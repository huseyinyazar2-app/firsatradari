import hashlib
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.commercial_validation.service import (
    DIRECT_PAYMENT_OUTCOMES,
)
from firsat_radari.db.models import (
    CommercialOutcome,
    CommercialValidationExperiment,
    DataSource,
    MetricDefinition,
    NormalizedDocument,
    ProblemCluster,
    ProblemClusteringRun,
    ProblemClusterMembership,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
    ProblemEvidence,
    SourceRelationship,
)
from firsat_radari.source_registry.independence import (
    EvidenceOrigin,
    assess_source_independence,
)

DEFINITION_SET_VERSION = "problem_cluster_v3"
STORAGE_PRECISION = Decimal("0.000001")
DEFINITION_VERSIONS = {
    "cluster.problem_entity_spread": "2",
    "cluster.unresolved_problem_median_age_days": "2",
}


class ProblemClusterMetricError(ValueError):
    pass


@dataclass(frozen=True)
class ClusterMetricSpec:
    key: str
    name: str
    description: str
    unit: str
    numerator_description: str
    denominator_description: str
    minimum_sample_size: int
    calculation_kind: str


@dataclass(frozen=True)
class ComputedClusterMetric:
    numerator: Decimal | None
    denominator: Decimal | None
    value: Decimal | None
    sample_size: int
    confidence_lower: Decimal | None = None
    confidence_upper: Decimal | None = None


@dataclass(frozen=True)
class ProblemClusterMetricOutcome:
    run_id: uuid.UUID
    status: str
    cluster_count: int
    metric_count: int
    error_count: int


CLUSTER_METRIC_SPECS = (
    ClusterMetricSpec(
        key="cluster.problem_mention_rate",
        name="Problem mention rate",
        description="Cluster documents divided by all clustering-eligible documents.",
        unit="ratio",
        numerator_description="Unique documents in the problem cluster",
        denominator_description="All clustering-eligible problem documents",
        minimum_sample_size=20,
        calculation_kind="problem_mention_rate",
    ),
    ClusterMetricSpec(
        key="cluster.problem_entity_spread",
        name="Problem entity spread",
        description=(
            "Distinct source entities in the cluster divided by all "
            "clustering-eligible entities."
        ),
        unit="ratio",
        numerator_description="Unique source entities in the problem cluster",
        denominator_description="All clustering-eligible source entities",
        minimum_sample_size=5,
        calculation_kind="problem_entity_spread",
    ),
    ClusterMetricSpec(
        key="cluster.workaround_rate",
        name="Workaround rate",
        description="Cluster documents with explicit workaround evidence.",
        unit="ratio",
        numerator_description="Cluster documents with workaround evidence",
        denominator_description="Unique cluster documents",
        minimum_sample_size=5,
        calculation_kind="workaround_rate",
    ),
    ClusterMetricSpec(
        key="cluster.switching_intent_rate",
        name="Switching intent rate",
        description="Cluster documents with explicit abandonment evidence.",
        unit="ratio",
        numerator_description="Cluster documents with abandonment-intent evidence",
        denominator_description="Unique cluster documents",
        minimum_sample_size=5,
        calculation_kind="switching_intent_rate",
    ),
    ClusterMetricSpec(
        key="cluster.economic_impact_rate",
        name="Economic impact rate",
        description="Cluster documents with explicit money, time, or severe impact.",
        unit="ratio",
        numerator_description="Cluster documents with explicit impact evidence",
        denominator_description="Unique cluster documents",
        minimum_sample_size=5,
        calculation_kind="economic_impact_rate",
    ),
    ClusterMetricSpec(
        key="cluster.payment_intent_rate",
        name="Payment intent rate",
        description="Cluster documents with explicit payment-intent evidence.",
        unit="ratio",
        numerator_description="Cluster documents with payment-intent evidence",
        denominator_description="Unique cluster documents",
        minimum_sample_size=5,
        calculation_kind="payment_intent_rate",
    ),
    ClusterMetricSpec(
        key="cluster.independent_demand_signal_rate",
        name="Independent demand signal rate",
        description=(
            "Cluster documents originating from an independent demand "
            "evidence family."
        ),
        unit="ratio",
        numerator_description=(
            "Cluster documents from approved demand evidence sources"
        ),
        denominator_description="Unique cluster documents",
        minimum_sample_size=5,
        calculation_kind="independent_demand_signal_rate",
    ),
    ClusterMetricSpec(
        key="cluster.direct_payment_evidence_rate",
        name="Direct payment evidence rate",
        description=(
            "Verified participants with prepayment, contract, sale, or "
            "renewal evidence."
        ),
        unit="ratio",
        numerator_description=(
            "Unique participants with verified direct payment outcomes"
        ),
        denominator_description=(
            "Unique participants with any verified commercial outcome"
        ),
        minimum_sample_size=1,
        calculation_kind="direct_payment_evidence_rate",
    ),
    ClusterMetricSpec(
        key="cluster.unresolved_problem_median_age_days",
        name="Unresolved problem median age",
        description=(
            "Median age in days of unresolved source items in the cluster."
        ),
        unit="days",
        numerator_description="Median age of unresolved cluster documents",
        denominator_description=(
            "Unresolved cluster documents with valid creation time"
        ),
        minimum_sample_size=5,
        calculation_kind="unresolved_problem_median_age_days",
    ),
)


class ProblemClusterMetricEngine:
    def __init__(self, session: Session) -> None:
        self._session = session

    def calculate(
        self,
        clustering_run_id: uuid.UUID,
    ) -> ProblemClusterMetricOutcome:
        clustering_run = self._session.get(
            ProblemClusteringRun,
            clustering_run_id,
        )
        if clustering_run is None:
            raise ProblemClusterMetricError("Problem clustering run not found")
        if clustering_run.status != "succeeded":
            raise ProblemClusterMetricError(
                "Problem clustering run is not complete"
            )
        clusters = list(
            self._session.scalars(
                select(ProblemCluster)
                .where(ProblemCluster.run_id == clustering_run.id)
                .order_by(ProblemCluster.id)
            )
        )
        cluster_ids = {cluster.id for cluster in clusters}
        memberships = list(
            self._session.scalars(
                select(ProblemClusterMembership).where(
                    ProblemClusterMembership.run_id == clustering_run.id
                )
            )
        )
        source_ids = {membership.source_id for membership in memberships}
        governance_sources = list(
            self._session.scalars(
                select(DataSource)
                .where(DataSource.id.in_(source_ids))
                .order_by(DataSource.id)
            )
        )
        governance_relationships = list(
            self._session.scalars(
                select(SourceRelationship)
                .where(
                    SourceRelationship.source_id.in_(source_ids),
                    SourceRelationship.related_source_id.in_(source_ids),
                )
                .order_by(SourceRelationship.id)
            )
        )
        verified_outcome_rows = list(
            self._session.execute(
                select(
                    CommercialOutcome,
                    CommercialValidationExperiment.cluster_id,
                )
                .join(
                    CommercialValidationExperiment,
                    CommercialValidationExperiment.id
                    == CommercialOutcome.experiment_id,
                )
                .where(
                    CommercialValidationExperiment.cluster_id.in_(
                        cluster_ids
                    ),
                    CommercialOutcome.verification_status == "verified",
                    CommercialOutcome.verified_at.is_not(None),
                )
                .order_by(
                    CommercialValidationExperiment.cluster_id,
                    CommercialOutcome.id,
                )
            )
        )
        input_fingerprint = _input_fingerprint(
            clustering_run,
            verified_outcome_rows,
            governance_sources,
            governance_relationships,
        )
        existing = self._session.scalar(
            select(ProblemClusterMetricRun).where(
                ProblemClusterMetricRun.clustering_run_id
                == clustering_run.id,
                ProblemClusterMetricRun.definition_set_version
                == DEFINITION_SET_VERSION,
                ProblemClusterMetricRun.input_fingerprint
                == input_fingerprint,
            )
        )
        if existing is not None:
            return _outcome(existing)

        definitions = self._ensure_definitions()
        outcomes_by_cluster: dict[
            uuid.UUID,
            list[CommercialOutcome],
        ] = defaultdict(list)
        for outcome, cluster_id in verified_outcome_rows:
            outcomes_by_cluster[cluster_id].append(outcome)
        members_by_cluster: dict[
            uuid.UUID,
            list[ProblemClusterMembership],
        ] = defaultdict(list)
        for membership in memberships:
            members_by_cluster[membership.cluster_id].append(membership)
        document_ids = {membership.document_id for membership in memberships}
        documents = {
            document.id: document
            for document in self._session.scalars(
                select(NormalizedDocument).where(
                    NormalizedDocument.id.in_(document_ids)
                )
            )
        }
        evidence_types_by_document: dict[uuid.UUID, set[str]] = defaultdict(set)
        if document_ids:
            for document_id, evidence_type in self._session.execute(
                select(
                    ProblemEvidence.document_id,
                    ProblemEvidence.evidence_type,
                ).where(ProblemEvidence.document_id.in_(document_ids))
            ):
                evidence_types_by_document[document_id].add(evidence_type)
        eligible_entity_count = len(
            {membership.entity_id for membership in memberships}
        )
        demand_source_ids = set(
            self._session.scalars(
                select(DataSource.id).where(
                    DataSource.id.in_(source_ids),
                    DataSource.evidence_family_key
                    == "technical_q_and_a",
                )
            )
        )

        run = ProblemClusterMetricRun(
            clustering_run_id=clustering_run.id,
            definition_set_version=DEFINITION_SET_VERSION,
            input_fingerprint=input_fingerprint,
            as_of=max(
                (
                    _as_utc(outcome.verified_at)
                    for outcome, _ in verified_outcome_rows
                    if outcome.verified_at is not None
                ),
                default=clustering_run.as_of,
            ),
            status="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            cluster_count=len(clusters),
            metric_count=0,
            error_count=0,
        )
        self._session.add(run)
        self._session.flush()

        for cluster in clusters:
            cluster_members = members_by_cluster[cluster.id]
            cluster_documents = [
                documents[membership.document_id]
                for membership in cluster_members
                if membership.document_id in documents
            ]
            demand_document_ids = {
                membership.document_id
                for membership in cluster_members
                if membership.source_id in demand_source_ids
            }
            computed = _compute_cluster_metrics(
                cluster,
                cluster_documents,
                evidence_types_by_document,
                demand_document_ids,
                outcomes_by_cluster.get(cluster.id, []),
                clustering_run.eligible_count,
                eligible_entity_count,
                run.as_of,
            )
            independence = assess_source_independence(
                self._session,
                [
                    EvidenceOrigin(
                        source_id=membership.source_id,
                        entity_id=membership.entity_id,
                        content_id=membership.document_id,
                    )
                    for membership in cluster_members
                ],
            )
            structural_status = _structural_status(cluster)
            for spec in CLUSTER_METRIC_SPECS:
                result = computed[spec.calculation_kind]
                metric_status = structural_status
                if (
                    metric_status == "measured"
                    and result.sample_size < spec.minimum_sample_size
                ):
                    metric_status = "insufficient_sample"
                if (
                    metric_status == "measured"
                    and spec.calculation_kind
                    == "independent_demand_signal_rate"
                    and not independence.verified_independent
                ):
                    metric_status = "unverified_source_independence"
                self._session.add(
                    ProblemClusterMetricObservation(
                        run_id=run.id,
                        metric_definition_id=definitions[spec.key].id,
                        cluster_id=cluster.id,
                        as_of=run.as_of,
                        numerator=_quantize(result.numerator),
                        denominator=_quantize(result.denominator),
                        value=(
                            _quantize(result.value)
                            if metric_status == "measured"
                            else None
                        ),
                        unit=spec.unit,
                        sample_size=result.sample_size,
                        status=metric_status,
                        confidence_lower=(
                            _quantize(result.confidence_lower)
                            if metric_status == "measured"
                            else None
                        ),
                        confidence_upper=(
                            _quantize(result.confidence_upper)
                            if metric_status == "measured"
                            else None
                        ),
                        calculation={
                            "definition_set_version": DEFINITION_SET_VERSION,
                            "formula": spec.calculation_kind,
                            "minimum_sample_size": spec.minimum_sample_size,
                            "cluster_status": cluster.status,
                            "source_count": cluster.source_count,
                            "evidence_level": independence.evidence_level,
                            "independence_group_count": (
                                independence.independence_group_count
                            ),
                            "independence_verified": (
                                independence.verified_independent
                            ),
                            "independence_blockers": list(
                                independence.blockers
                            ),
                            "ranking_eligible": False,
                            "ranking_blocker": (
                                "independent_source_validation_required"
                            ),
                            "commercial_evidence_level": (
                                "E5"
                                if spec.calculation_kind
                                == "direct_payment_evidence_rate"
                                and result.numerator is not None
                                and result.numerator > 0
                                else "none"
                            ),
                        },
                        created_at=datetime.now(UTC),
                    )
                )
                run.metric_count += 1

        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _outcome(run)

    def _ensure_definitions(self) -> dict[str, MetricDefinition]:
        definitions: dict[str, MetricDefinition] = {}
        for spec in CLUSTER_METRIC_SPECS:
            definition_version = DEFINITION_VERSIONS.get(spec.key, "1")
            definition = self._session.scalar(
                select(MetricDefinition).where(
                    MetricDefinition.key == spec.key,
                    MetricDefinition.version == definition_version,
                )
            )
            if definition is None:
                definition = MetricDefinition(
                    key=spec.key,
                    version=definition_version,
                    name=spec.name,
                    description=spec.description,
                    unit=spec.unit,
                    numerator_description=spec.numerator_description,
                    denominator_description=spec.denominator_description,
                    minimum_sample_size=spec.minimum_sample_size,
                    window_days=None,
                    comparison_group_description=(
                        "Problem clusters from the same versioned clustering run"
                    ),
                    freshness_policy=(
                        "Observation time equals the clustering run as_of"
                    ),
                    confidence_method=(
                        "wilson_95" if spec.unit == "ratio" else "none_v1"
                    ),
                    missing_data_policy="unknown_not_zero",
                    outlier_policy="no_winsorization_v1",
                    active=True,
                )
                self._session.add(definition)
                self._session.flush()
            definitions[spec.key] = definition
        return definitions


def _compute_cluster_metrics(
    cluster: ProblemCluster,
    documents: list[NormalizedDocument],
    evidence_types_by_document: dict[uuid.UUID, set[str]],
    demand_document_ids: set[uuid.UUID],
    commercial_outcomes: list[CommercialOutcome],
    eligible_document_count: int,
    eligible_entity_count: int,
    as_of: datetime,
) -> dict[str, ComputedClusterMetric]:
    document_count = len(documents)
    workaround_count = _evidence_document_count(
        documents,
        evidence_types_by_document,
        {"workaround"},
    )
    switching_count = _evidence_document_count(
        documents,
        evidence_types_by_document,
        {"abandonment_intent"},
    )
    economic_count = _evidence_document_count(
        documents,
        evidence_types_by_document,
        {"money_impact", "time_impact", "severe_impact"},
    )
    payment_count = _evidence_document_count(
        documents,
        evidence_types_by_document,
        {"payment_intent"},
    )
    independent_demand_count = sum(
        document.id in demand_document_ids for document in documents
    )
    verified_participants = {
        outcome.participant_key_hash for outcome in commercial_outcomes
    }
    direct_payment_participants = {
        outcome.participant_key_hash
        for outcome in commercial_outcomes
        if outcome.direction == "supports"
        and outcome.outcome_type in DIRECT_PAYMENT_OUTCOMES
    }
    open_ages = [
        max(
            0.0,
            (
                _as_utc(as_of) - _as_utc(document.source_created_at)
            ).total_seconds()
            / 86_400,
        )
        for document in documents
        if document.attributes.get("state") in {"open", "unresolved"}
        and document.source_created_at is not None
    ]
    median_age = (
        Decimal(str(median(open_ages))) if open_ages else None
    )
    return {
        "problem_mention_rate": _ratio_metric(
            document_count,
            eligible_document_count,
        ),
        "problem_entity_spread": _ratio_metric(
            cluster.entity_count,
            eligible_entity_count,
        ),
        "workaround_rate": _ratio_metric(workaround_count, document_count),
        "switching_intent_rate": _ratio_metric(
            switching_count,
            document_count,
        ),
        "economic_impact_rate": _ratio_metric(
            economic_count,
            document_count,
        ),
        "payment_intent_rate": _ratio_metric(payment_count, document_count),
        "independent_demand_signal_rate": _ratio_metric(
            independent_demand_count,
            document_count,
        ),
        "direct_payment_evidence_rate": _ratio_metric(
            len(direct_payment_participants),
            len(verified_participants),
        ),
        "unresolved_problem_median_age_days": ComputedClusterMetric(
            numerator=median_age,
            denominator=Decimal(len(open_ages)),
            value=median_age,
            sample_size=len(open_ages),
        ),
    }


def _evidence_document_count(
    documents: list[NormalizedDocument],
    evidence_types_by_document: dict[uuid.UUID, set[str]],
    target_types: set[str],
) -> int:
    return sum(
        bool(
            evidence_types_by_document.get(document.id, set())
            & target_types
        )
        for document in documents
    )


def _input_fingerprint(
    clustering_run: ProblemClusteringRun,
    outcome_rows: list[tuple[CommercialOutcome, uuid.UUID]],
    governance_sources: list[DataSource],
    governance_relationships: list[SourceRelationship],
) -> str:
    parts = [
        DEFINITION_SET_VERSION,
        str(clustering_run.id),
        clustering_run.input_fingerprint,
    ]
    for source in governance_sources:
        parts.append(
            "|".join(
                (
                    "source",
                    str(source.id),
                    source.evidence_family_key,
                    source.independence_group_key,
                    source.independence_status,
                )
            )
        )
    for relationship in governance_relationships:
        parts.append(
            "|".join(
                (
                    "relationship",
                    str(relationship.id),
                    str(relationship.source_id),
                    str(relationship.related_source_id),
                    relationship.relationship_type,
                    relationship.scope,
                    relationship.independence_effect,
                    relationship.status,
                )
            )
        )
    for outcome, cluster_id in outcome_rows:
        parts.append(
            "|".join(
                (
                    str(cluster_id),
                    str(outcome.id),
                    outcome.participant_key_hash,
                    outcome.outcome_type,
                    outcome.direction,
                    str(outcome.amount),
                    outcome.currency or "",
                    _as_utc(outcome.occurred_at).isoformat(),
                    (
                        _as_utc(outcome.verified_at).isoformat()
                        if outcome.verified_at is not None
                        else ""
                    ),
                )
            )
        )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _structural_status(cluster: ProblemCluster) -> str:
    if cluster.status == "insufficient_repetition":
        return "insufficient_repetition"
    if cluster.status == "within_entity_repeated":
        return "insufficient_entity_spread"
    if cluster.status != "cross_entity_candidate":
        return "unsupported_cluster_status"
    return "measured"


def _ratio_metric(
    numerator: int,
    denominator: int,
) -> ComputedClusterMetric:
    if denominator == 0:
        return ComputedClusterMetric(
            numerator=Decimal(numerator),
            denominator=Decimal(0),
            value=None,
            sample_size=0,
        )
    lower, upper = _wilson_interval(numerator, denominator)
    return ComputedClusterMetric(
        numerator=Decimal(numerator),
        denominator=Decimal(denominator),
        value=Decimal(numerator) / Decimal(denominator),
        sample_size=denominator,
        confidence_lower=lower,
        confidence_upper=upper,
    )


def _wilson_interval(
    successes: int,
    sample_size: int,
) -> tuple[Decimal, Decimal]:
    z = 1.959963984540054
    proportion = successes / sample_size
    denominator = 1 + z * z / sample_size
    centre = proportion + z * z / (2 * sample_size)
    spread = z * math.sqrt(
        proportion * (1 - proportion) / sample_size
        + z * z / (4 * sample_size * sample_size)
    )
    return (
        Decimal(str((centre - spread) / denominator)),
        Decimal(str((centre + spread) / denominator)),
    )


def _quantize(value: Decimal | None) -> Decimal | None:
    return value.quantize(STORAGE_PRECISION) if value is not None else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _outcome(run: ProblemClusterMetricRun) -> ProblemClusterMetricOutcome:
    return ProblemClusterMetricOutcome(
        run_id=run.id,
        status=run.status,
        cluster_count=run.cluster_count,
        metric_count=run.metric_count,
        error_count=run.error_count,
    )
