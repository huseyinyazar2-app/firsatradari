import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    BacktestPrediction,
    BacktestRun,
    CommercialOutcome,
    CommercialValidationExperiment,
    MetricDefinition,
    Opportunity,
    OpportunityEligibilityDecision,
    OpportunityProfileEvaluation,
    OpportunityRankingEntry,
    OpportunityRankingRun,
    OpportunityScoreRun,
    OpportunityScoreSnapshot,
    OpportunityVersion,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
    ResearchProfile,
    ScoringProfile,
)

PROFILE_KEY = "evidence_first"
PROFILE_VERSION = "1.0.0"
STORAGE_PRECISION = Decimal("0.000001")
DEFAULT_WEIGHTS = {
    "cluster.independent_demand_signal_rate": Decimal("0.25"),
    "cluster.direct_payment_evidence_rate": Decimal("0.25"),
    "cluster.economic_impact_rate": Decimal("0.20"),
    "cluster.problem_mention_rate": Decimal("0.15"),
    "cluster.problem_entity_spread": Decimal("0.15"),
}
MINIMUM_CONFIDENCE = Decimal("0.60")
OUTCOME_TYPES = frozenset(
    {"prepayment", "contract", "sale", "renewal"}
)


class OpportunityScoringError(ValueError):
    pass


@dataclass(frozen=True)
class ScoreRunOutcome:
    run_id: uuid.UUID
    opportunity_count: int
    rankable_count: int
    excluded_count: int


@dataclass(frozen=True)
class RankingOutcome:
    ranking_run_id: uuid.UUID
    ranked_count: int
    excluded_count: int


@dataclass(frozen=True)
class BacktestOutcome:
    run_id: uuid.UUID
    status: str
    evaluated_count: int
    positive_count: int


class OpportunityScoringService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def score(
        self,
        *,
        as_of: datetime,
        research_profile_id: uuid.UUID,
    ) -> ScoreRunOutcome:
        effective_as_of = _as_utc(as_of)
        if effective_as_of > datetime.now(UTC):
            raise OpportunityScoringError(
                "Score cutoff cannot be in the future"
            )
        profile = self._ensure_profile()
        research_profile = self._session.get(
            ResearchProfile,
            research_profile_id,
        )
        if research_profile is None:
            raise OpportunityScoringError("Research profile not found")
        versions = self._versions_as_of(effective_as_of)
        inputs: list[
            tuple[
                OpportunityVersion,
                OpportunityEligibilityDecision | None,
                ProblemClusterMetricRun | None,
                dict[str, ProblemClusterMetricObservation],
                OpportunityProfileEvaluation | None,
            ]
        ] = []
        fingerprint_parts = [
            PROFILE_KEY,
            PROFILE_VERSION,
            effective_as_of.isoformat(),
            json.dumps(profile.weights, sort_keys=True),
            str(_quantize(Decimal(profile.minimum_confidence))),
            str(research_profile.id),
            f"{research_profile.key}:{research_profile.version}",
        ]
        for version in versions:
            decision = self._session.get(
                OpportunityEligibilityDecision,
                version.eligibility_decision_id,
            )
            metric_run = self._metric_run(decision)
            observations = self._observations(
                metric_run,
                decision.cluster_id if decision else None,
            )
            profile_evaluation = self._profile_evaluation(
                version.id,
                research_profile.id,
                effective_as_of,
            )
            inputs.append(
                (
                    version,
                    decision,
                    metric_run,
                    observations,
                    profile_evaluation,
                )
            )
            fingerprint_parts.extend(
                (
                    str(version.id),
                    version.input_fingerprint,
                    str(decision.id) if decision else "missing-decision",
                    str(metric_run.id) if metric_run else "missing-metrics",
                    (
                        str(profile_evaluation.id)
                        if profile_evaluation
                        else "missing-profile-evaluation"
                    ),
                    (
                        str(profile_evaluation.fit_score)
                        if profile_evaluation
                        else "unknown-fit"
                    ),
                    *(
                        "|".join(
                            (
                                key,
                                str(observation.id),
                                observation.status,
                                str(observation.value),
                                str(observation.confidence_lower),
                                str(observation.confidence_upper),
                                str(observation.sample_size),
                            )
                        )
                        for key, observation in sorted(
                            observations.items()
                        )
                    ),
                )
            )
        input_fingerprint = hashlib.sha256(
            "|".join(fingerprint_parts).encode()
        ).hexdigest()
        existing = self._session.scalar(
            select(OpportunityScoreRun).where(
                OpportunityScoreRun.profile_id == profile.id,
                OpportunityScoreRun.as_of == effective_as_of,
                OpportunityScoreRun.input_fingerprint == input_fingerprint,
            )
        )
        if existing is not None:
            return _score_outcome(existing)

        run = OpportunityScoreRun(
            profile_id=profile.id,
            research_profile_id=research_profile.id,
            as_of=effective_as_of,
            input_fingerprint=input_fingerprint,
            status="running",
            opportunity_count=len(inputs),
            rankable_count=0,
            excluded_count=0,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        self._session.add(run)
        self._session.flush()
        weights = {
            key: Decimal(str(value))
            for key, value in profile.weights.items()
        }
        for (
            version,
            decision,
            metric_run,
            observations,
            profile_evaluation,
        ) in inputs:
            snapshot = _calculate_snapshot(
                run.id,
                version,
                decision,
                metric_run,
                observations,
                profile_evaluation,
                weights,
                Decimal(profile.minimum_confidence),
                effective_as_of,
            )
            self._session.add(snapshot)
            if snapshot.status == "rankable":
                run.rankable_count += 1
            else:
                run.excluded_count += 1
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _score_outcome(run)

    def rank(self, score_run_id: uuid.UUID) -> RankingOutcome:
        score_run = self._session.get(OpportunityScoreRun, score_run_id)
        if score_run is None or score_run.status != "succeeded":
            raise OpportunityScoringError(
                "Successful opportunity score run not found"
            )
        existing = self._session.scalar(
            select(OpportunityRankingRun).where(
                OpportunityRankingRun.score_run_id == score_run.id
            )
        )
        if existing is not None:
            return RankingOutcome(
                ranking_run_id=existing.id,
                ranked_count=existing.ranked_count,
                excluded_count=existing.excluded_count,
            )
        snapshots = list(
            self._session.scalars(
                select(OpportunityScoreSnapshot).where(
                    OpportunityScoreSnapshot.run_id == score_run.id
                )
            )
        )
        rankable = sorted(
            (
                snapshot
                for snapshot in snapshots
                if snapshot.status == "rankable"
                and snapshot.total_score is not None
            ),
            key=lambda item: (
                Decimal(item.total_score),
                item.opportunity_version_id,
            ),
            reverse=True,
        )
        ranking = OpportunityRankingRun(
            score_run_id=score_run.id,
            status="succeeded",
            candidate_count=len(snapshots),
            ranked_count=len(rankable),
            excluded_count=len(snapshots) - len(rankable),
            created_at=datetime.now(UTC),
        )
        self._session.add(ranking)
        self._session.flush()
        rank_by_snapshot = {
            snapshot.id: index
            for index, snapshot in enumerate(rankable, start=1)
        }
        for snapshot in snapshots:
            eligible = snapshot.id in rank_by_snapshot
            self._session.add(
                OpportunityRankingEntry(
                    ranking_run_id=ranking.id,
                    score_snapshot_id=snapshot.id,
                    rank=rank_by_snapshot.get(snapshot.id),
                    eligible=eligible,
                    exclusion_reasons=(
                        [] if eligible else [snapshot.status]
                    ),
                    created_at=datetime.now(UTC),
                )
            )
        self._session.commit()
        return RankingOutcome(
            ranking_run_id=ranking.id,
            ranked_count=ranking.ranked_count,
            excluded_count=ranking.excluded_count,
        )

    def backtest(
        self,
        score_run_id: uuid.UUID,
        *,
        outcome_window_days: int,
    ) -> BacktestOutcome:
        if not 1 <= outcome_window_days <= 730:
            raise OpportunityScoringError(
                "Outcome window must be between 1 and 730 days"
            )
        score_run = self._session.get(OpportunityScoreRun, score_run_id)
        if score_run is None or score_run.status != "succeeded":
            raise OpportunityScoringError(
                "Successful opportunity score run not found"
            )
        existing = self._session.scalar(
            select(BacktestRun).where(
                BacktestRun.score_run_id == score_run.id,
                BacktestRun.outcome_window_days == outcome_window_days,
            )
        )
        if existing is not None:
            return _backtest_outcome(existing)
        cutoff = _as_utc(score_run.as_of)
        horizon = cutoff + timedelta(days=outcome_window_days)
        if horizon > datetime.now(UTC):
            raise OpportunityScoringError(
                "Outcome window is not complete yet"
            )
        snapshots = list(
            self._session.scalars(
                select(OpportunityScoreSnapshot).where(
                    OpportunityScoreSnapshot.run_id == score_run.id,
                    OpportunityScoreSnapshot.status == "rankable",
                    OpportunityScoreSnapshot.total_score.is_not(None),
                )
            )
        )
        run = BacktestRun(
            score_run_id=score_run.id,
            cutoff_at=cutoff,
            outcome_window_days=outcome_window_days,
            status="running",
            prediction_count=len(snapshots),
            evaluated_count=0,
            positive_count=0,
            brier_score=None,
            baseline_brier_score=None,
            improvement=None,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        self._session.add(run)
        self._session.flush()
        results: list[tuple[Decimal, bool]] = []
        baseline_probability = self._historical_base_rate(cutoff)
        for snapshot in snapshots:
            version = self._session.get(
                OpportunityVersion,
                snapshot.opportunity_version_id,
            )
            opportunity = (
                self._session.get(Opportunity, version.opportunity_id)
                if version
                else None
            )
            if opportunity is None:
                continue
            outcome_count = self._future_outcome_count(
                version.id,
                cutoff,
                horizon,
            )
            observed = outcome_count > 0
            probability = Decimal(snapshot.total_score)
            results.append((probability, observed))
            self._session.add(
                BacktestPrediction(
                    backtest_run_id=run.id,
                    score_snapshot_id=snapshot.id,
                    predicted_probability=probability,
                    outcome_observed=observed,
                    outcome_count=outcome_count,
                    evaluation_status="evaluated",
                    created_at=datetime.now(UTC),
                )
            )
        run.evaluated_count = len(results)
        run.positive_count = sum(observed for _, observed in results)
        if results:
            brier = sum(
                (
                    probability
                    - (Decimal(1) if observed else Decimal(0))
                )
                ** 2
                for probability, observed in results
            ) / Decimal(len(results))
            baseline = sum(
                (
                    baseline_probability
                    - (Decimal(1) if observed else Decimal(0))
                )
                ** 2
                for _, observed in results
            ) / Decimal(len(results))
            run.brier_score = _quantize(brier)
            run.baseline_brier_score = _quantize(baseline)
            run.improvement = _quantize(baseline - brier)
        run.status = (
            "succeeded"
            if run.evaluated_count >= 20
            else "insufficient_sample"
        )
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _backtest_outcome(run)

    def _ensure_profile(self) -> ScoringProfile:
        profile = self._session.scalar(
            select(ScoringProfile).where(
                ScoringProfile.key == PROFILE_KEY,
                ScoringProfile.version == PROFILE_VERSION,
            )
        )
        if profile is not None:
            return profile
        profile = ScoringProfile(
            key=PROFILE_KEY,
            version=PROFILE_VERSION,
            name="Evidence-first opportunity score",
            weights={
                key: str(value) for key, value in DEFAULT_WEIGHTS.items()
            },
            minimum_confidence=MINIMUM_CONFIDENCE,
            active=True,
            created_at=datetime.now(UTC),
        )
        self._session.add(profile)
        self._session.flush()
        return profile

    def _versions_as_of(
        self,
        as_of: datetime,
    ) -> list[OpportunityVersion]:
        latest: dict[uuid.UUID, OpportunityVersion] = {}
        for version in self._session.scalars(
            select(OpportunityVersion)
            .where(
                OpportunityVersion.created_at <= as_of,
                OpportunityVersion.status == "candidate",
            )
            .order_by(
                OpportunityVersion.opportunity_id,
                OpportunityVersion.version_number,
            )
        ):
            latest[version.opportunity_id] = version
        return sorted(latest.values(), key=lambda item: str(item.id))

    def _metric_run(
        self,
        decision: OpportunityEligibilityDecision | None,
    ) -> ProblemClusterMetricRun | None:
        if decision is None:
            return None
        raw_id = decision.details.get("cluster_metric_run_id")
        try:
            run_id = uuid.UUID(str(raw_id))
        except (ValueError, TypeError, AttributeError):
            return None
        return self._session.get(ProblemClusterMetricRun, run_id)

    def _observations(
        self,
        metric_run: ProblemClusterMetricRun | None,
        cluster_id: uuid.UUID | None,
    ) -> dict[str, ProblemClusterMetricObservation]:
        if metric_run is None or cluster_id is None:
            return {}
        return {
            key: observation
            for observation, key in self._session.execute(
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
                    ProblemClusterMetricObservation.run_id == metric_run.id,
                    ProblemClusterMetricObservation.cluster_id == cluster_id,
                    MetricDefinition.key.in_(DEFAULT_WEIGHTS),
                )
            )
        }

    def _profile_evaluation(
        self,
        version_id: uuid.UUID,
        research_profile_id: uuid.UUID,
        as_of: datetime,
    ) -> OpportunityProfileEvaluation | None:
        return self._session.scalar(
            select(OpportunityProfileEvaluation)
            .where(
                OpportunityProfileEvaluation.opportunity_version_id
                == version_id,
                OpportunityProfileEvaluation.research_profile_id
                == research_profile_id,
                OpportunityProfileEvaluation.evaluated_at <= as_of,
            )
            .order_by(
                OpportunityProfileEvaluation.evaluated_at.desc(),
                OpportunityProfileEvaluation.id.desc(),
            )
            .limit(1)
        )

    def _future_outcome_count(
        self,
        opportunity_version_id: uuid.UUID,
        cutoff: datetime,
        horizon: datetime,
    ) -> int:
        return len(
            list(
                self._session.scalars(
                    select(CommercialOutcome)
                    .join(
                        CommercialValidationExperiment,
                        CommercialValidationExperiment.id
                        == CommercialOutcome.experiment_id,
                    )
                    .where(
                        CommercialValidationExperiment.opportunity_version_id
                        == opportunity_version_id,
                        CommercialOutcome.verification_status == "verified",
                        CommercialOutcome.verified_at.is_not(None),
                        CommercialOutcome.direction == "supports",
                        CommercialOutcome.outcome_type.in_(OUTCOME_TYPES),
                        CommercialOutcome.occurred_at > cutoff,
                        CommercialOutcome.occurred_at <= horizon,
                    )
                )
            )
        )

    def _historical_base_rate(self, cutoff: datetime) -> Decimal:
        experiment_versions = set(
            self._session.scalars(
                select(
                    CommercialValidationExperiment.opportunity_version_id
                ).where(
                    CommercialValidationExperiment.opportunity_version_id
                    .is_not(None),
                    CommercialValidationExperiment.started_at < cutoff,
                )
            )
        )
        positive_versions = set(
            self._session.scalars(
                select(
                    CommercialValidationExperiment.opportunity_version_id
                )
                .join(
                    CommercialOutcome,
                    CommercialOutcome.experiment_id
                    == CommercialValidationExperiment.id,
                )
                .where(
                    CommercialValidationExperiment.opportunity_version_id
                    .is_not(None),
                    CommercialValidationExperiment.started_at < cutoff,
                    CommercialOutcome.verification_status == "verified",
                    CommercialOutcome.verified_at.is_not(None),
                    CommercialOutcome.verified_at <= cutoff,
                    CommercialOutcome.occurred_at <= cutoff,
                    CommercialOutcome.direction == "supports",
                    CommercialOutcome.outcome_type.in_(OUTCOME_TYPES),
                )
            )
        )
        return (
            (Decimal(len(positive_versions)) + Decimal(1))
            / (Decimal(len(experiment_versions)) + Decimal(2))
        ).quantize(STORAGE_PRECISION)


def _calculate_snapshot(
    run_id: uuid.UUID,
    version: OpportunityVersion,
    decision: OpportunityEligibilityDecision | None,
    metric_run: ProblemClusterMetricRun | None,
    observations: dict[str, ProblemClusterMetricObservation],
    profile_evaluation: OpportunityProfileEvaluation | None,
    weights: dict[str, Decimal],
    minimum_confidence: Decimal,
    as_of: datetime,
) -> OpportunityScoreSnapshot:
    measured = {
        key: observation
        for key, observation in observations.items()
        if observation.status == "measured"
        and observation.value is not None
    }
    potential = sum(
        weights[key] * _clamp(Decimal(observation.value))
        for key, observation in measured.items()
        if key in weights
    )
    actionability = (
        Decimal(profile_evaluation.fit_score)
        if profile_evaluation is not None
        and profile_evaluation.fit_score is not None
        else Decimal(0)
    )
    coverage = Decimal(len(measured)) / Decimal(len(weights))
    sample_factor = (
        sum(
            min(Decimal(1), Decimal(item.sample_size) / Decimal(20))
            for item in measured.values()
        )
        / Decimal(len(weights))
    )
    precision = (
        sum(_precision(item) for item in measured.values())
        / Decimal(len(weights))
    )
    evidence_factor = (
        Decimal(1)
        if decision is not None and decision.evidence_level == "E2"
        else Decimal(0)
    )
    confidence = (
        Decimal("0.35") * coverage
        + Decimal("0.25") * sample_factor
        + Decimal("0.20") * precision
        + Decimal("0.20") * evidence_factor
    )
    blockers: list[str] = []
    if decision is None or not decision.eligible:
        blockers.append("ineligible_opportunity")
    elif _as_utc(decision.decided_at) > as_of:
        blockers.append("future_eligibility_decision")
    if metric_run is None:
        blockers.append("missing_metric_run")
    elif (
        metric_run.finished_at is None
        or _as_utc(metric_run.finished_at) > as_of
    ):
        blockers.append("future_or_incomplete_metric_run")
    if len(measured) != len(weights):
        blockers.append("required_metrics_not_measured")
    if profile_evaluation is None:
        blockers.append("missing_profile_evaluation")
    elif not profile_evaluation.eligible:
        blockers.append("profile_ineligible")
    elif profile_evaluation.fit_score is None:
        blockers.append("insufficient_profile_data")
    if confidence < minimum_confidence:
        blockers.append("insufficient_confidence")
    status = "rankable" if not blockers else blockers[0]
    total = (
        _quantize(
            potential
            * (Decimal("0.80") + Decimal("0.20") * actionability)
            * confidence
        )
        if not blockers
        else None
    )
    return OpportunityScoreSnapshot(
        run_id=run_id,
        opportunity_version_id=version.id,
        potential_score=_quantize(potential),
        actionability_score=_quantize(actionability),
        confidence_score=_quantize(confidence),
        uncertainty=_quantize(Decimal(1) - confidence),
        total_score=total,
        status=status,
        components={
            "profile_version": PROFILE_VERSION,
            "metric_values": {
                key: str(observation.value)
                for key, observation in sorted(measured.items())
            },
            "weights": {
                key: str(value) for key, value in sorted(weights.items())
            },
            "coverage": str(_quantize(coverage)),
            "sample_factor": str(_quantize(sample_factor)),
            "precision": str(_quantize(precision)),
            "evidence_factor": str(evidence_factor),
            "profile_evaluation_id": (
                str(profile_evaluation.id)
                if profile_evaluation is not None
                else None
            ),
            "profile_data_coverage": (
                str(profile_evaluation.data_coverage)
                if profile_evaluation is not None
                else None
            ),
            "minimum_confidence": str(minimum_confidence),
            "blockers": blockers,
            "ranking_eligible": not blockers,
        },
        created_at=datetime.now(UTC),
    )


def _precision(observation: ProblemClusterMetricObservation) -> Decimal:
    if (
        observation.confidence_lower is None
        or observation.confidence_upper is None
    ):
        return Decimal("0.50")
    width = Decimal(observation.confidence_upper) - Decimal(
        observation.confidence_lower
    )
    return _clamp(Decimal(1) - width)


def _clamp(value: Decimal) -> Decimal:
    return min(Decimal(1), max(Decimal(0), value))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(STORAGE_PRECISION, rounding=ROUND_HALF_UP)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _score_outcome(run: OpportunityScoreRun) -> ScoreRunOutcome:
    return ScoreRunOutcome(
        run_id=run.id,
        opportunity_count=run.opportunity_count,
        rankable_count=run.rankable_count,
        excluded_count=run.excluded_count,
    )


def _backtest_outcome(run: BacktestRun) -> BacktestOutcome:
    return BacktestOutcome(
        run_id=run.id,
        status=run.status,
        evaluated_count=run.evaluated_count,
        positive_count=run.positive_count,
    )
