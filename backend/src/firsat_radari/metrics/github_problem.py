import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    IngestionCollection,
    MetricDefinition,
    MetricObservation,
    MetricRun,
    NormalizedDocument,
    ProblemEvidence,
    ProblemExtractionRecord,
    RawSnapshotObservation,
    SignalDefinition,
    SignalValue,
)
from firsat_radari.problem_mining.github import (
    EXTRACTOR_KEY,
    EXTRACTOR_VERSION,
)

DEFINITION_SET_VERSION = "github_problem_v2"
NORMALIZER_KEY = "github_work_item"
NORMALIZER_VERSION = "1.0.0"
MINIMUM_NORMALIZATION_COVERAGE = Decimal("0.95")
MINIMUM_PROBLEM_EXTRACTION_COVERAGE = Decimal("0.95")
BUG_LABELS = frozenset({"bug", "crash", "defect", "error", "regression"})
PERMITTED_DERIVED_DATA_STATUSES = frozenset({"allowed", "approved"})
STORAGE_PRECISION = Decimal("0.000001")


class MetricEngineError(ValueError):
    pass


@dataclass(frozen=True)
class MetricSpec:
    key: str
    name: str
    description: str
    unit: str
    numerator_description: str
    denominator_description: str | None
    minimum_sample_size: int
    window_days: int | None
    calculation_kind: str


@dataclass(frozen=True)
class ComputedMetric:
    numerator: Decimal | None
    denominator: Decimal | None
    value: Decimal | None
    sample_size: int
    confidence_lower: Decimal | None = None
    confidence_upper: Decimal | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class MetricRunOutcome:
    run_id: uuid.UUID
    status: str
    input_document_count: int
    metric_count: int
    error_count: int


METRIC_SPECS = (
    MetricSpec(
        key="github.eligible_issue_count",
        name="Eligible issue count",
        description="Non-bot issue count in the complete repository sampling frame.",
        unit="count",
        numerator_description="Non-bot issues",
        denominator_description=None,
        minimum_sample_size=1,
        window_days=None,
        calculation_kind="eligible_issue_count",
    ),
    MetricSpec(
        key="github.pull_request_share",
        name="Pull request share",
        description="Pull requests divided by eligible issues plus pull requests.",
        unit="ratio",
        numerator_description="Pull requests",
        denominator_description="Non-bot issues plus pull requests",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="pull_request_share",
    ),
    MetricSpec(
        key="github.bug_label_ratio",
        name="Bug-label issue ratio",
        description="Eligible issues carrying an explicit bug-like label.",
        unit="ratio",
        numerator_description="Eligible issues with a bug-like label",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="bug_label_ratio",
    ),
    MetricSpec(
        key="github.open_issue_ratio",
        name="Open issue ratio",
        description="Open eligible issues divided by all eligible issues.",
        unit="ratio",
        numerator_description="Open eligible issues",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="open_issue_ratio",
    ),
    MetricSpec(
        key="github.mean_issue_comments",
        name="Mean comments per issue",
        description="Total comments divided by eligible non-bot issues.",
        unit="comments_per_issue",
        numerator_description="Comments on eligible issues",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="mean_issue_comments",
    ),
    MetricSpec(
        key="github.issue_creation_rate_30d",
        name="30-day issue creation rate",
        description="Eligible issues created in the trailing 30 days per day.",
        unit="issues_per_day",
        numerator_description="Eligible issues created in trailing 30 days",
        denominator_description="30 days",
        minimum_sample_size=10,
        window_days=30,
        calculation_kind="issue_creation_rate_30d",
    ),
    MetricSpec(
        key="github.median_resolution_days",
        name="Median issue resolution time",
        description="Median days from creation to closure for eligible closed issues.",
        unit="days",
        numerator_description="Median resolution duration in days",
        denominator_description="Eligible closed issues",
        minimum_sample_size=10,
        window_days=None,
        calculation_kind="median_resolution_days",
    ),
    MetricSpec(
        key="github.severe_impact_issue_ratio",
        name="Severe-impact issue ratio",
        description="Eligible issues with an explicit severe-impact phrase.",
        unit="ratio",
        numerator_description="Eligible issues with severe-impact evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="severe_impact_issue_ratio",
    ),
    MetricSpec(
        key="github.workaround_issue_ratio",
        name="Workaround issue ratio",
        description="Eligible issues with an explicit workaround phrase.",
        unit="ratio",
        numerator_description="Eligible issues with workaround evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="workaround_issue_ratio",
    ),
    MetricSpec(
        key="github.missing_capability_issue_ratio",
        name="Missing-capability issue ratio",
        description="Eligible issues with an explicit missing-capability phrase.",
        unit="ratio",
        numerator_description="Eligible issues with missing-capability evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="missing_capability_issue_ratio",
    ),
    MetricSpec(
        key="github.payment_intent_issue_ratio",
        name="Payment-intent issue ratio",
        description="Eligible issues with an explicit payment-intent phrase.",
        unit="ratio",
        numerator_description="Eligible issues with payment-intent evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="payment_intent_issue_ratio",
    ),
    MetricSpec(
        key="github.abandonment_intent_issue_ratio",
        name="Abandonment-intent issue ratio",
        description="Eligible issues with an explicit abandonment-intent phrase.",
        unit="ratio",
        numerator_description="Eligible issues with abandonment-intent evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="abandonment_intent_issue_ratio",
    ),
    MetricSpec(
        key="github.time_impact_issue_ratio",
        name="Time-impact issue ratio",
        description="Eligible issues with an explicit time-impact phrase.",
        unit="ratio",
        numerator_description="Eligible issues with time-impact evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="time_impact_issue_ratio",
    ),
    MetricSpec(
        key="github.money_impact_issue_ratio",
        name="Money-impact issue ratio",
        description="Eligible issues with an explicit money-impact phrase.",
        unit="ratio",
        numerator_description="Eligible issues with money-impact evidence",
        denominator_description="Eligible non-bot issues",
        minimum_sample_size=20,
        window_days=None,
        calculation_kind="money_impact_issue_ratio",
    ),
)


class GitHubProblemMetricEngine:
    def __init__(self, session: Session) -> None:
        self._session = session

    def calculate(
        self,
        collection_id: uuid.UUID,
        *,
        as_of: datetime | None = None,
    ) -> MetricRunOutcome:
        collection = self._session.get(IngestionCollection, collection_id)
        if collection is None:
            raise MetricEngineError("Collection not found")
        if collection.job_type != "github_work_items":
            raise MetricEngineError("Collection is not a GitHub work-item collection")
        source = self._session.get(DataSource, collection.source_id)
        if (
            source is None
            or not source.enabled
            or source.policy_status != "approved"
            or source.derived_data_permission not in PERMITTED_DERIVED_DATA_STATUSES
        ):
            raise MetricEngineError("Source policy does not permit derived metrics")
        effective_as_of = as_of or collection.completed_at
        if effective_as_of is None:
            raise MetricEngineError("as_of is required for an unfinished collection")
        effective_as_of = _as_utc(effective_as_of)
        if collection.completed_at is not None and effective_as_of != _as_utc(
            collection.completed_at
        ):
            raise MetricEngineError("as_of must match collection completion")

        existing_run = self._session.scalar(
            select(MetricRun).where(
                MetricRun.collection_id == collection.id,
                MetricRun.definition_set_version == DEFINITION_SET_VERSION,
                MetricRun.as_of == effective_as_of,
            )
        )
        if existing_run is not None:
            return _run_outcome(existing_run)

        definitions = self._ensure_definitions()
        signal_definition = self._ensure_signal_definition()
        run = MetricRun(
            collection_id=collection.id,
            definition_set_version=DEFINITION_SET_VERSION,
            as_of=effective_as_of,
            status="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            input_document_count=0,
            metric_count=0,
            error_count=0,
        )
        self._session.add(run)
        self._session.commit()

        documents = list(
            self._session.scalars(
                select(NormalizedDocument)
                .join(
                    RawSnapshotObservation,
                    RawSnapshotObservation.snapshot_id
                    == NormalizedDocument.snapshot_id,
                )
                .where(
                    RawSnapshotObservation.collection_id == collection.id,
                    NormalizedDocument.normalizer_key == NORMALIZER_KEY,
                    NormalizedDocument.normalizer_version == NORMALIZER_VERSION,
                    NormalizedDocument.status == "succeeded",
                    NormalizedDocument.source_created_at <= effective_as_of,
                )
                .order_by(NormalizedDocument.source_created_at)
            )
        )
        observed_snapshot_count = (
            self._session.scalar(
                select(func.count())
                .select_from(RawSnapshotObservation)
                .where(RawSnapshotObservation.collection_id == collection.id)
            )
            or 0
        )
        document_ids = [document.id for document in documents]
        issue_document_ids = {
            document.id
            for document in documents
            if document.document_type == "issue"
        }
        successful_extraction_ids: set[uuid.UUID] = set()
        evidence_types_by_document: dict[uuid.UUID, set[str]] = defaultdict(set)
        if document_ids:
            successful_extraction_ids = set(
                self._session.scalars(
                    select(ProblemExtractionRecord.document_id).where(
                        ProblemExtractionRecord.document_id.in_(document_ids),
                        ProblemExtractionRecord.extractor_key
                        == EXTRACTOR_KEY,
                        ProblemExtractionRecord.extractor_version
                        == EXTRACTOR_VERSION,
                        ProblemExtractionRecord.status == "succeeded",
                    )
                )
            )
            for document_id, evidence_type in self._session.execute(
                select(
                    ProblemEvidence.document_id,
                    ProblemEvidence.evidence_type,
                )
                .join(
                    ProblemExtractionRecord,
                    ProblemExtractionRecord.id
                    == ProblemEvidence.extraction_record_id,
                )
                .where(
                    ProblemEvidence.document_id.in_(document_ids),
                    ProblemExtractionRecord.extractor_key
                    == EXTRACTOR_KEY,
                    ProblemExtractionRecord.extractor_version
                    == EXTRACTOR_VERSION,
                    ProblemExtractionRecord.status == "succeeded",
                )
            ):
                evidence_types_by_document[document_id].add(evidence_type)
        extraction_coverage = (
            Decimal(1)
            if not issue_document_ids
            else Decimal(
                len(successful_extraction_ids & issue_document_ids)
            )
            / Decimal(len(issue_document_ids))
        )
        run.input_document_count = len(documents)
        grouped_documents: dict[uuid.UUID, list[NormalizedDocument]] = defaultdict(list)
        for document in documents:
            if document.entity_id is not None:
                grouped_documents[document.entity_id].append(document)

        base_status, coverage = _data_status(
            collection,
            len(documents),
            observed_snapshot_count,
        )
        sampling_frame_supported = _sampling_frame_supported(
            collection.query_definition
        )
        if base_status == "measured" and not sampling_frame_supported:
            base_status = "unsupported_sampling_frame"
        if (
            base_status == "measured"
            and extraction_coverage < MINIMUM_PROBLEM_EXTRACTION_COVERAGE
        ):
            base_status = "incomplete_problem_extraction"

        observations: list[MetricObservation] = []
        for entity_id, entity_documents in grouped_documents.items():
            computed = _compute_metrics(
                entity_documents,
                evidence_types_by_document,
                effective_as_of,
            )
            for spec in METRIC_SPECS:
                result = computed[spec.calculation_kind]
                status = base_status
                if status == "measured" and result.sample_size < spec.minimum_sample_size:
                    status = "insufficient_sample"
                value = (
                    _quantize(result.value) if status == "measured" else None
                )
                confidence_lower = (
                    _quantize(result.confidence_lower)
                    if status == "measured"
                    else None
                )
                confidence_upper = (
                    _quantize(result.confidence_upper)
                    if status == "measured"
                    else None
                )
                observation = MetricObservation(
                    run_id=run.id,
                    metric_definition_id=definitions[spec.key].id,
                    collection_id=collection.id,
                    entity_id=entity_id,
                    as_of=effective_as_of,
                    numerator=_quantize(result.numerator),
                    denominator=_quantize(result.denominator),
                    value=value,
                    unit=spec.unit,
                    sample_size=result.sample_size,
                    status=status,
                    confidence_lower=confidence_lower,
                    confidence_upper=confidence_upper,
                    calculation={
                        "definition_set_version": DEFINITION_SET_VERSION,
                        "formula": spec.calculation_kind,
                        "minimum_sample_size": spec.minimum_sample_size,
                        "normalization_coverage": float(coverage),
                        "normalized_document_count": len(documents),
                        "observed_snapshot_count": observed_snapshot_count,
                        "problem_extraction_coverage": float(
                            extraction_coverage
                        ),
                        "query_fingerprint": collection.query_fingerprint,
                        "sampling_frame_supported": sampling_frame_supported,
                        **(result.details or {}),
                    },
                    created_at=datetime.now(UTC),
                )
                self._session.add(observation)
                observations.append(observation)
                run.metric_count += 1

        self._session.flush()
        for observation in observations:
            self._create_trend_signal(signal_definition, observation)
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return _run_outcome(run)

    def _ensure_definitions(self) -> dict[str, MetricDefinition]:
        definitions: dict[str, MetricDefinition] = {}
        for spec in METRIC_SPECS:
            definition = self._session.scalar(
                select(MetricDefinition).where(
                    MetricDefinition.key == spec.key,
                    MetricDefinition.version == "2",
                )
            )
            if definition is None:
                definition = MetricDefinition(
                    key=spec.key,
                    version="2",
                    name=spec.name,
                    description=spec.description,
                    unit=spec.unit,
                    numerator_description=spec.numerator_description,
                    denominator_description=spec.denominator_description,
                    minimum_sample_size=spec.minimum_sample_size,
                    window_days=spec.window_days,
                    comparison_group_description=(
                        "Same repository and metric definition across collection periods"
                    ),
                    freshness_policy=(
                        "Observation time equals collection completion; current ranking "
                        "must apply its own freshness threshold"
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

    def _ensure_signal_definition(self) -> SignalDefinition:
        definition = self._session.scalar(
            select(SignalDefinition).where(
                SignalDefinition.key == "metric.period_change",
                SignalDefinition.version == "1",
            )
        )
        if definition is None:
            definition = SignalDefinition(
                key="metric.period_change",
                version="1",
                name="Metric period change",
                description="Change from the latest earlier measured observation.",
                active=True,
            )
            self._session.add(definition)
            self._session.flush()
        return definition

    def _create_trend_signal(
        self,
        definition: SignalDefinition,
        observation: MetricObservation,
    ) -> None:
        if observation.status != "measured" or observation.value is None:
            self._session.add(
                SignalValue(
                    signal_definition_id=definition.id,
                    metric_observation_id=observation.id,
                    baseline_observation_id=None,
                    entity_id=observation.entity_id,
                    as_of=observation.as_of,
                    absolute_change=None,
                    relative_change=None,
                    direction=None,
                    status=observation.status,
                    explanation={"reason": observation.status},
                    created_at=datetime.now(UTC),
                )
            )
            return

        baseline = self._session.scalar(
            select(MetricObservation)
            .where(
                MetricObservation.entity_id == observation.entity_id,
                MetricObservation.metric_definition_id
                == observation.metric_definition_id,
                MetricObservation.status == "measured",
                MetricObservation.as_of < observation.as_of,
            )
            .order_by(MetricObservation.as_of.desc())
            .limit(1)
        )
        if baseline is None or baseline.value is None:
            self._session.add(
                SignalValue(
                    signal_definition_id=definition.id,
                    metric_observation_id=observation.id,
                    baseline_observation_id=None,
                    entity_id=observation.entity_id,
                    as_of=observation.as_of,
                    absolute_change=None,
                    relative_change=None,
                    direction=None,
                    status="insufficient_history",
                    explanation={"reason": "no_earlier_measured_observation"},
                    created_at=datetime.now(UTC),
                )
            )
            return

        absolute_change = observation.value - baseline.value
        relative_change = (
            absolute_change / abs(baseline.value)
            if baseline.value != 0
            else None
        )
        direction = (
            "up"
            if absolute_change > 0
            else "down"
            if absolute_change < 0
            else "flat"
        )
        self._session.add(
            SignalValue(
                signal_definition_id=definition.id,
                metric_observation_id=observation.id,
                baseline_observation_id=baseline.id,
                entity_id=observation.entity_id,
                as_of=observation.as_of,
                absolute_change=absolute_change,
                relative_change=relative_change,
                direction=direction,
                status="measured",
                explanation={
                    "baseline_as_of": baseline.as_of.isoformat(),
                    "formula": "(current-baseline)/abs(baseline)",
                },
                created_at=datetime.now(UTC),
            )
        )


def _compute_metrics(
    documents: list[NormalizedDocument],
    evidence_types_by_document: dict[uuid.UUID, set[str]],
    as_of: datetime,
) -> dict[str, ComputedMetric]:
    eligible_documents = [
        document
        for document in documents
        if not bool(document.attributes.get("is_bot_likely", False))
    ]
    issues = [
        document
        for document in eligible_documents
        if document.attributes.get("item_type") == "issue"
    ]
    pull_requests = [
        document
        for document in eligible_documents
        if document.attributes.get("item_type") == "pull_request"
    ]
    bug_issues = [
        document
        for document in issues
        if BUG_LABELS
        & {
            str(label).casefold()
            for label in document.attributes.get("labels", [])
            if isinstance(label, str)
        }
    ]
    open_issues = [
        document
        for document in issues
        if document.attributes.get("state") == "open"
    ]
    comment_count = sum(
        _safe_nonnegative_int(document.attributes.get("comments_count"))
        for document in issues
    )
    recent_threshold = as_of - timedelta(days=30)
    recent_issues = [
        document
        for document in issues
        if document.source_created_at is not None
        and recent_threshold <= _as_utc(document.source_created_at) <= as_of
    ]
    resolution_days = [
        duration
        for document in issues
        if (duration := _resolution_days(document)) is not None
    ]

    issue_count = len(issues)
    work_item_count = len(issues) + len(pull_requests)
    return {
        "eligible_issue_count": ComputedMetric(
            numerator=Decimal(issue_count),
            denominator=None,
            value=Decimal(issue_count),
            sample_size=issue_count,
        ),
        "pull_request_share": _ratio_metric(
            len(pull_requests),
            work_item_count,
        ),
        "bug_label_ratio": _ratio_metric(len(bug_issues), issue_count),
        "open_issue_ratio": _ratio_metric(len(open_issues), issue_count),
        "mean_issue_comments": _mean_metric(comment_count, issue_count),
        "issue_creation_rate_30d": ComputedMetric(
            numerator=Decimal(len(recent_issues)),
            denominator=Decimal(30),
            value=_safe_divide(len(recent_issues), 30),
            sample_size=issue_count,
            details={
                "window_start": recent_threshold.isoformat(),
                "window_end": as_of.isoformat(),
            },
        ),
        "median_resolution_days": ComputedMetric(
            numerator=(
                Decimal(str(median(resolution_days)))
                if resolution_days
                else None
            ),
            denominator=Decimal(len(resolution_days)),
            value=(
                Decimal(str(median(resolution_days)))
                if resolution_days
                else None
            ),
            sample_size=len(resolution_days),
        ),
        "severe_impact_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "severe_impact",
        ),
        "workaround_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "workaround",
        ),
        "missing_capability_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "missing_capability",
        ),
        "payment_intent_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "payment_intent",
        ),
        "abandonment_intent_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "abandonment_intent",
        ),
        "time_impact_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "time_impact",
        ),
        "money_impact_issue_ratio": _evidence_ratio(
            issues,
            evidence_types_by_document,
            "money_impact",
        ),
    }


def _evidence_ratio(
    documents: list[NormalizedDocument],
    evidence_types_by_document: dict[uuid.UUID, set[str]],
    evidence_type: str,
) -> ComputedMetric:
    matched = sum(
        evidence_type in evidence_types_by_document.get(document.id, set())
        for document in documents
    )
    return _ratio_metric(matched, len(documents))


def _ratio_metric(numerator: int, denominator: int) -> ComputedMetric:
    value = _safe_divide(numerator, denominator)
    lower, upper = _wilson_interval(numerator, denominator)
    return ComputedMetric(
        numerator=Decimal(numerator),
        denominator=Decimal(denominator),
        value=value,
        sample_size=denominator,
        confidence_lower=lower,
        confidence_upper=upper,
        details={"confidence_method": "wilson_95"},
    )


def _mean_metric(numerator: int, denominator: int) -> ComputedMetric:
    return ComputedMetric(
        numerator=Decimal(numerator),
        denominator=Decimal(denominator),
        value=_safe_divide(numerator, denominator),
        sample_size=denominator,
    )


def _safe_divide(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return Decimal(numerator) / Decimal(denominator)


def _quantize(value: Decimal | None) -> Decimal | None:
    return value.quantize(STORAGE_PRECISION) if value is not None else None


def _wilson_interval(
    successes: int,
    sample_size: int,
) -> tuple[Decimal | None, Decimal | None]:
    if sample_size == 0:
        return None, None
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


def _resolution_days(document: NormalizedDocument) -> float | None:
    if document.source_created_at is None:
        return None
    closed_at_raw = document.attributes.get("closed_at")
    if not isinstance(closed_at_raw, str):
        return None
    try:
        closed_at = datetime.fromisoformat(closed_at_raw)
    except ValueError:
        return None
    duration = _as_utc(closed_at) - _as_utc(document.source_created_at)
    if duration.total_seconds() < 0:
        return None
    return duration.total_seconds() / 86_400


def _safe_nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _data_status(
    collection: IngestionCollection,
    normalized_document_count: int,
    observed_snapshot_count: int,
) -> tuple[str, Decimal]:
    if observed_snapshot_count == 0:
        coverage = Decimal(1 if collection.expected_total == 0 else 0)
    else:
        coverage = Decimal(normalized_document_count) / Decimal(
            observed_snapshot_count
        )
    if not collection.is_complete:
        return "incomplete_collection", coverage
    if coverage < MINIMUM_NORMALIZATION_COVERAGE:
        return "incomplete_normalization", coverage
    return "measured", coverage


def _sampling_frame_supported(query_definition: dict) -> bool:
    query = query_definition.get("q")
    if not isinstance(query, str):
        return False
    tokens = query.split()
    return len(tokens) == 1 and tokens[0].lower().startswith("repo:")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _run_outcome(run: MetricRun) -> MetricRunOutcome:
    return MetricRunOutcome(
        run_id=run.id,
        status=run.status,
        input_document_count=run.input_document_count,
        metric_count=run.metric_count,
        error_count=run.error_count,
    )
