import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    MetricDefinition,
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterLineage,
    ProblemClusterLineageRun,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
    ProblemClusterSignalObservation,
    ProblemClusterSignalRun,
)

ALGORITHM_VERSION = "1.0.0"
MINIMUM_TREND_POINTS = 4
MINIMUM_ANOMALY_POINTS = 6
MINIMUM_SEASONALITY_POINTS = 12
PRECISION = Decimal("0.000001")


class ClusterSignalError(ValueError):
    pass


@dataclass(frozen=True)
class TimePoint:
    at: datetime
    value: Decimal
    observation_id: uuid.UUID


@dataclass(frozen=True)
class SignalAnalysis:
    status: str
    slope_per_day: Decimal | None
    relative_change_30d: Decimal | None
    trend_direction: str | None
    anomaly_score: Decimal | None
    anomaly_status: str
    seasonality_period_days: int | None
    seasonality_strength: Decimal | None
    calculation: dict


@dataclass(frozen=True)
class ClusterSignalOutcome:
    run_id: uuid.UUID
    cluster_count: int
    observation_count: int


class ProblemClusterSignalService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def calculate(
        self,
        clustering_run_id: uuid.UUID,
    ) -> ClusterSignalOutcome:
        clustering_run = self._session.get(
            ProblemClusteringRun,
            clustering_run_id,
        )
        if clustering_run is None or clustering_run.status != "succeeded":
            raise ClusterSignalError(
                "Successful problem clustering run not found"
            )
        clusters = list(
            self._session.scalars(
                select(ProblemCluster)
                .where(
                    ProblemCluster.run_id == clustering_run.id,
                    ProblemCluster.status == "cross_entity_candidate",
                )
                .order_by(ProblemCluster.id)
            )
        )
        inputs: list[
            tuple[
                ProblemCluster,
                MetricDefinition,
                list[TimePoint],
            ]
        ] = []
        fingerprint_parts = [
            ALGORITHM_VERSION,
            str(clustering_run.id),
            clustering_run.input_fingerprint,
        ]
        for cluster in clusters:
            cluster_ids = self._stable_history(cluster.id)
            for definition, points in self._metric_points(cluster_ids):
                inputs.append((cluster, definition, points))
                fingerprint_parts.extend(
                    (
                        str(cluster.id),
                        str(definition.id),
                        *(
                            f"{point.observation_id}|"
                            f"{_as_utc(point.at).isoformat()}|{point.value}"
                            for point in points
                        ),
                    )
                )
        input_fingerprint = hashlib.sha256(
            "|".join(fingerprint_parts).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(ProblemClusterSignalRun).where(
                ProblemClusterSignalRun.clustering_run_id
                == clustering_run.id,
                ProblemClusterSignalRun.algorithm_version
                == ALGORITHM_VERSION,
                ProblemClusterSignalRun.input_fingerprint
                == input_fingerprint,
            )
        )
        if existing is not None:
            return _outcome(existing)
        run = ProblemClusterSignalRun(
            clustering_run_id=clustering_run.id,
            algorithm_version=ALGORITHM_VERSION,
            input_fingerprint=input_fingerprint,
            status="running",
            cluster_count=len(clusters),
            observation_count=0,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        self._session.add(run)
        self._session.flush()
        for cluster, definition, points in inputs:
            analysis = analyze_points(points)
            self._session.add(
                ProblemClusterSignalObservation(
                    run_id=run.id,
                    cluster_id=cluster.id,
                    metric_definition_id=definition.id,
                    point_count=len(points),
                    first_at=points[0].at if points else None,
                    last_at=points[-1].at if points else None,
                    slope_per_day=analysis.slope_per_day,
                    relative_change_30d=analysis.relative_change_30d,
                    trend_direction=analysis.trend_direction,
                    anomaly_score=analysis.anomaly_score,
                    anomaly_status=analysis.anomaly_status,
                    seasonality_period_days=(
                        analysis.seasonality_period_days
                    ),
                    seasonality_strength=analysis.seasonality_strength,
                    status=analysis.status,
                    calculation=analysis.calculation,
                    created_at=datetime.now(UTC),
                )
            )
            run.observation_count += 1
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(run)

    def _stable_history(
        self,
        current_cluster_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        history = [current_cluster_id]
        seen = {current_cluster_id}
        cursor = current_cluster_id
        for _ in range(51):
            relation = self._session.scalar(
                select(ProblemClusterLineage)
                .join(
                    ProblemClusterLineageRun,
                    ProblemClusterLineageRun.id
                    == ProblemClusterLineage.lineage_run_id,
                )
                .where(
                    ProblemClusterLineage.current_cluster_id == cursor,
                    ProblemClusterLineage.previous_cluster_id.is_not(None),
                    ProblemClusterLineage.relation_type.in_(
                        {"stable", "evolved"}
                    ),
                )
                .order_by(
                    ProblemClusterLineageRun.finished_at.desc(),
                    ProblemClusterLineage.id.desc(),
                )
                .limit(1)
            )
            if (
                relation is None
                or relation.previous_cluster_id is None
                or relation.previous_cluster_id in seen
            ):
                break
            cursor = relation.previous_cluster_id
            seen.add(cursor)
            history.append(cursor)
        history.reverse()
        return history

    def _metric_points(
        self,
        cluster_ids: list[uuid.UUID],
    ) -> list[tuple[MetricDefinition, list[TimePoint]]]:
        rows = list(
            self._session.execute(
                select(
                    ProblemClusterMetricObservation,
                    ProblemClusterMetricRun,
                    MetricDefinition,
                )
                .join(
                    ProblemClusterMetricRun,
                    ProblemClusterMetricRun.id
                    == ProblemClusterMetricObservation.run_id,
                )
                .join(
                    MetricDefinition,
                    MetricDefinition.id
                    == ProblemClusterMetricObservation.metric_definition_id,
                )
                .where(
                    ProblemClusterMetricObservation.cluster_id.in_(
                        cluster_ids
                    ),
                    ProblemClusterMetricObservation.status == "measured",
                    ProblemClusterMetricObservation.value.is_not(None),
                    ProblemClusterMetricRun.status == "succeeded",
                )
                .order_by(
                    ProblemClusterMetricRun.as_of,
                    ProblemClusterMetricRun.finished_at,
                )
            )
        )
        latest: dict[
            tuple[uuid.UUID, datetime],
            tuple[
                ProblemClusterMetricObservation,
                ProblemClusterMetricRun,
                MetricDefinition,
            ],
        ] = {}
        for observation, metric_run, definition in rows:
            latest[(definition.id, _as_utc(metric_run.as_of))] = (
                observation,
                metric_run,
                definition,
            )
        grouped: dict[
            uuid.UUID,
            tuple[MetricDefinition, list[TimePoint]],
        ] = {}
        for observation, metric_run, definition in latest.values():
            grouped.setdefault(definition.id, (definition, []))[1].append(
                TimePoint(
                    at=_as_utc(metric_run.as_of),
                    value=Decimal(observation.value),
                    observation_id=observation.id,
                )
            )
        return [
            (
                definition,
                sorted(points, key=lambda point: point.at),
            )
            for definition, points in grouped.values()
        ]


def analyze_points(points: list[TimePoint]) -> SignalAnalysis:
    ordered = sorted(points, key=lambda point: _as_utc(point.at))
    if len(ordered) < MINIMUM_TREND_POINTS:
        return SignalAnalysis(
            status="insufficient_history",
            slope_per_day=None,
            relative_change_30d=None,
            trend_direction=None,
            anomaly_score=None,
            anomaly_status="insufficient_history",
            seasonality_period_days=None,
            seasonality_strength=None,
            calculation={
                "point_count": len(ordered),
                "minimum_trend_points": MINIMUM_TREND_POINTS,
                "method": "theil_sen_median_pairwise_slope",
            },
        )
    slopes: list[Decimal] = []
    for left_index, left in enumerate(ordered[:-1]):
        for right in ordered[left_index + 1 :]:
            days = Decimal(
                str(
                    (
                        _as_utc(right.at) - _as_utc(left.at)
                    ).total_seconds()
                    / 86_400
                )
            )
            if days > 0:
                slopes.append((right.value - left.value) / days)
    slope = Decimal(str(median(slopes))) if slopes else Decimal(0)
    center = Decimal(str(median([point.value for point in ordered])))
    relative = (
        slope * Decimal(30) / abs(center)
        if center != 0
        else None
    )
    direction = "stable"
    if relative is not None and relative > Decimal("0.05"):
        direction = "rising"
    elif relative is not None and relative < Decimal("-0.05"):
        direction = "falling"
    anomaly_score, anomaly_status = _anomaly(ordered)
    period, strength, seasonality_status = _seasonality(ordered)
    return SignalAnalysis(
        status="measured",
        slope_per_day=_quantize(slope, Decimal("0.000000001")),
        relative_change_30d=(
            _quantize(relative, PRECISION)
            if relative is not None
            else None
        ),
        trend_direction=direction,
        anomaly_score=anomaly_score,
        anomaly_status=anomaly_status,
        seasonality_period_days=period,
        seasonality_strength=strength,
        calculation={
            "point_count": len(ordered),
            "trend_method": "theil_sen_median_pairwise_slope",
            "trend_threshold_30d": "0.05",
            "anomaly_method": "modified_z_score_mad",
            "anomaly_threshold": "3.5",
            "seasonality_method": "regular_interval_autocorrelation",
            "seasonality_status": seasonality_status,
            "future_data_used": False,
        },
    )


def _anomaly(
    points: list[TimePoint],
) -> tuple[Decimal | None, str]:
    if len(points) < MINIMUM_ANOMALY_POINTS:
        return None, "insufficient_history"
    history = [point.value for point in points[:-1]]
    center = Decimal(str(median(history)))
    deviations = [abs(value - center) for value in history]
    mad = Decimal(str(median(deviations)))
    delta = points[-1].value - center
    if mad == 0:
        if delta == 0:
            return Decimal("0.000000"), "normal"
        return Decimal("9.999999"), "anomaly"
    score = Decimal("0.6745") * delta / mad
    return (
        _quantize(score, PRECISION),
        "anomaly" if abs(score) >= Decimal("3.5") else "normal",
    )


def _seasonality(
    points: list[TimePoint],
) -> tuple[int | None, Decimal | None, str]:
    if len(points) < MINIMUM_SEASONALITY_POINTS:
        return None, None, "insufficient_history"
    intervals = [
        (
            _as_utc(right.at) - _as_utc(left.at)
        ).total_seconds()
        / 86_400
        for left, right in zip(points, points[1:], strict=False)
    ]
    median_interval = float(median(intervals))
    if median_interval <= 0 or any(
        abs(interval - median_interval) / median_interval > 0.20
        for interval in intervals
    ):
        return None, None, "irregular_sampling"
    candidates: list[tuple[int, float]] = []
    for period_days in (7, 30, 90):
        lag = round(period_days / median_interval)
        if lag >= 2 and len(points) >= lag * 3:
            correlation = _autocorrelation(
                [float(point.value) for point in points],
                lag,
            )
            if correlation is not None:
                candidates.append((lag, correlation))
    if not candidates:
        return None, None, "insufficient_cycles"
    lag, correlation = max(candidates, key=lambda item: item[1])
    strength = _quantize(
        Decimal(str(max(0.0, correlation))),
        PRECISION,
    )
    if strength < Decimal("0.60"):
        return None, strength, "not_detected"
    return round(lag * median_interval), strength, "detected"


def _autocorrelation(values: list[float], lag: int) -> float | None:
    left = values[:-lag]
    right = values[lag:]
    if len(left) < 3:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return numerator / denominator if denominator else None


def _quantize(value: Decimal, precision: Decimal) -> Decimal:
    return value.quantize(precision, rounding=ROUND_HALF_UP)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _outcome(run: ProblemClusterSignalRun) -> ClusterSignalOutcome:
    return ClusterSignalOutcome(
        run_id=run.id,
        cluster_count=run.cluster_count,
        observation_count=run.observation_count,
    )
