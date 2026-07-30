import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    MetricDefinition,
    OpportunityEligibilityDecision,
    OpportunityEligibilityRun,
    ProblemCluster,
    ProblemClusterAudit,
    ProblemClusteringQualitySnapshot,
    ProblemClusteringRun,
    ProblemClusterLineageRun,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
)

GATE_VERSION = "1.0.0"
REQUIRED_BASE_METRICS = frozenset(
    {
        "cluster.problem_mention_rate",
        "cluster.problem_entity_spread",
        "cluster.economic_impact_rate",
    }
)
INDEPENDENT_DEMAND_METRIC = "cluster.independent_demand_signal_rate"
DIRECT_PAYMENT_METRIC = "cluster.direct_payment_evidence_rate"


class OpportunityEligibilityError(ValueError):
    pass


@dataclass(frozen=True)
class OpportunityEligibilityOutcome:
    run_id: uuid.UUID
    status: str
    evaluated_cluster_count: int
    eligible_cluster_count: int
    excluded_cluster_count: int


class OpportunityEligibilityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(
        self,
        clustering_run_id: uuid.UUID,
    ) -> OpportunityEligibilityOutcome:
        clustering_run = self._session.get(
            ProblemClusteringRun,
            clustering_run_id,
        )
        if clustering_run is None:
            raise OpportunityEligibilityError(
                "Problem clustering run not found"
            )
        if clustering_run.status != "succeeded":
            raise OpportunityEligibilityError(
                "Problem clustering run is not complete"
            )
        clusters = list(
            self._session.scalars(
                select(ProblemCluster).where(
                    ProblemCluster.run_id == clustering_run.id,
                    ProblemCluster.status == "cross_entity_candidate",
                )
            )
        )
        quality = self._session.scalar(
            select(ProblemClusteringQualitySnapshot)
            .where(
                ProblemClusteringQualitySnapshot.clustering_run_id
                == clustering_run.id
            )
            .order_by(
                ProblemClusteringQualitySnapshot.calculated_at.desc(),
                ProblemClusteringQualitySnapshot.id.desc(),
            )
            .limit(1)
        )
        lineage = self._session.scalar(
            select(ProblemClusterLineageRun)
            .where(
                ProblemClusterLineageRun.current_clustering_run_id
                == clustering_run.id
            )
            .order_by(
                ProblemClusterLineageRun.finished_at.desc(),
                ProblemClusterLineageRun.id.desc(),
            )
            .limit(1)
        )
        metric_run = self._session.scalar(
            select(ProblemClusterMetricRun)
            .where(
                ProblemClusterMetricRun.clustering_run_id
                == clustering_run.id
            )
            .order_by(
                ProblemClusterMetricRun.finished_at.desc(),
                ProblemClusterMetricRun.id.desc(),
            )
            .limit(1)
        )
        latest_audits = self._latest_audits(
            {cluster.id for cluster in clusters}
        )
        input_fingerprint = hashlib.sha256(
            "|".join(
                (
                    str(clustering_run.id),
                    str(quality.id) if quality else "no-quality",
                    str(lineage.id) if lineage else "no-lineage",
                    str(metric_run.id) if metric_run else "no-metrics",
                    *sorted(str(audit.id) for audit in latest_audits.values()),
                )
            ).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(OpportunityEligibilityRun).where(
                OpportunityEligibilityRun.clustering_run_id
                == clustering_run.id,
                OpportunityEligibilityRun.gate_version == GATE_VERSION,
                OpportunityEligibilityRun.input_fingerprint
                == input_fingerprint,
            )
        )
        if existing is not None:
            return _outcome(existing)

        observations_by_cluster = self._metric_observations(metric_run)
        run = OpportunityEligibilityRun(
            clustering_run_id=clustering_run.id,
            gate_version=GATE_VERSION,
            input_fingerprint=input_fingerprint,
            status="running",
            evaluated_cluster_count=len(clusters),
            eligible_cluster_count=0,
            excluded_cluster_count=0,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        self._session.add(run)
        self._session.flush()
        for cluster in clusters:
            metrics = observations_by_cluster.get(cluster.id, {})
            audit = latest_audits.get(cluster.id)
            blockers: list[str] = []
            if quality is None:
                blockers.append("missing_cluster_quality_snapshot")
            elif not quality.passes_quality_gate:
                blockers.append(f"cluster_quality:{quality.status}")
            if lineage is None:
                blockers.append("missing_cluster_lineage")
            elif not lineage.passes_stability_gate:
                blockers.append(f"cluster_stability:{lineage.status}")
            if audit is None:
                blockers.append("missing_cluster_audit")
            elif audit.verdict != "coherent":
                blockers.append(f"cluster_audit:{audit.verdict}")
            missing_or_unmeasured = sorted(
                metric_key
                for metric_key in REQUIRED_BASE_METRICS
                if metric_key not in metrics
                or metrics[metric_key].status != "measured"
            )
            if missing_or_unmeasured:
                blockers.append("base_metrics_not_measured")
            evidence_level = _evidence_level(metrics)
            if evidence_level != "E2":
                blockers.append("independent_source_evidence_required")
            if (
                INDEPENDENT_DEMAND_METRIC not in metrics
                or metrics[INDEPENDENT_DEMAND_METRIC].status != "measured"
            ):
                blockers.append("independent_demand_evidence_required")
            elif not _has_positive_signal(metrics[INDEPENDENT_DEMAND_METRIC]):
                blockers.append("independent_demand_signal_absent")
            if (
                DIRECT_PAYMENT_METRIC not in metrics
                or metrics[DIRECT_PAYMENT_METRIC].status != "measured"
            ):
                blockers.append("direct_payment_evidence_required")
            elif not _has_positive_signal(metrics[DIRECT_PAYMENT_METRIC]):
                blockers.append("direct_payment_signal_absent")
            eligible = not blockers
            self._session.add(
                OpportunityEligibilityDecision(
                    run_id=run.id,
                    cluster_id=cluster.id,
                    eligible=eligible,
                    evidence_level=evidence_level,
                    blocker_codes=blockers,
                    details={
                        "quality_snapshot_id": str(quality.id)
                        if quality
                        else None,
                        "lineage_run_id": str(lineage.id)
                        if lineage
                        else None,
                        "cluster_metric_run_id": str(metric_run.id)
                        if metric_run
                        else None,
                        "cluster_audit_id": str(audit.id)
                        if audit
                        else None,
                        "required_base_metrics": sorted(
                            REQUIRED_BASE_METRICS
                        ),
                        "required_demand_metric": INDEPENDENT_DEMAND_METRIC,
                        "required_payment_metric": DIRECT_PAYMENT_METRIC,
                    },
                    decided_at=datetime.now(UTC),
                )
            )
            if eligible:
                run.eligible_cluster_count += 1
            else:
                run.excluded_cluster_count += 1
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(run)

    def _latest_audits(
        self,
        cluster_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, ProblemClusterAudit]:
        latest: dict[uuid.UUID, ProblemClusterAudit] = {}
        if not cluster_ids:
            return latest
        for audit in self._session.scalars(
            select(ProblemClusterAudit)
            .where(ProblemClusterAudit.cluster_id.in_(cluster_ids))
            .order_by(
                ProblemClusterAudit.created_at,
                ProblemClusterAudit.id,
            )
        ):
            latest[audit.cluster_id] = audit
        return latest

    def _metric_observations(
        self,
        metric_run: ProblemClusterMetricRun | None,
    ) -> dict[
        uuid.UUID,
        dict[str, ProblemClusterMetricObservation],
    ]:
        by_cluster: dict[
            uuid.UUID,
            dict[str, ProblemClusterMetricObservation],
        ] = defaultdict(dict)
        if metric_run is None:
            return by_cluster
        for observation, metric_key in self._session.execute(
            select(
                ProblemClusterMetricObservation,
                MetricDefinition.key,
            )
            .join(
                MetricDefinition,
                MetricDefinition.id
                == ProblemClusterMetricObservation.metric_definition_id,
            )
            .where(
                ProblemClusterMetricObservation.run_id == metric_run.id
            )
        ):
            by_cluster[observation.cluster_id][metric_key] = observation
        return by_cluster


def _evidence_level(
    metrics: dict[str, ProblemClusterMetricObservation],
) -> str:
    levels = {
        str(observation.calculation.get("evidence_level", "unknown"))
        for observation in metrics.values()
    }
    if "E2" in levels:
        return "E2"
    if "unverified_cross_source" in levels:
        return "unverified_cross_source"
    if "E1" in levels:
        return "E1"
    return "unknown"


def _has_positive_signal(
    observation: ProblemClusterMetricObservation,
) -> bool:
    return (
        observation.numerator is not None
        and observation.numerator > Decimal(0)
        and observation.value is not None
        and observation.value > Decimal(0)
    )


def _outcome(
    run: OpportunityEligibilityRun,
) -> OpportunityEligibilityOutcome:
    return OpportunityEligibilityOutcome(
        run_id=run.id,
        status=run.status,
        evaluated_cluster_count=run.evaluated_cluster_count,
        eligible_cluster_count=run.eligible_cluster_count,
        excluded_cluster_count=run.excluded_cluster_count,
    )
