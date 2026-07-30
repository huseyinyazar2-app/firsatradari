import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from firsat_radari.config import Settings
from firsat_radari.connectors.registry import (
    ConnectorRegistryError,
    create_connector,
    validate_discovery_query,
)
from firsat_radari.db.models import (
    DataSource,
    IngestionRun,
    ScheduledJob,
    ScheduledJobRun,
)
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.metrics.problem_clusters import (
    ProblemClusterMetricEngine,
)
from firsat_radari.normalization.registry import (
    NormalizerRegistryError,
    create_normalizer,
)
from firsat_radari.normalization.service import NormalizationService
from firsat_radari.operations.service import CostEntryInput, OperationsService
from firsat_radari.opportunities.scoring import OpportunityScoringService
from firsat_radari.problem_mining.clustering import ProblemClusteringEngine
from firsat_radari.problem_mining.github import GitHubProblemEvidenceExtractor
from firsat_radari.problem_mining.stack_exchange import (
    StackExchangeProblemEvidenceExtractor,
)
from firsat_radari.storage.filesystem import FileObjectStore

JOB_TYPES = frozenset(
    {
        "ingestion",
        "radar_scan",
        "problem_analysis",
        "opportunity_scoring",
        "operations_evaluation",
    }
)


class SchedulerError(ValueError):
    pass


@dataclass(frozen=True)
class ScheduleInput:
    key: str
    job_type: str
    interval_minutes: int
    payload: dict
    next_run_at: datetime
    created_by: str


@dataclass(frozen=True)
class SchedulerOutcome:
    considered_count: int
    succeeded_count: int
    failed_count: int
    run_ids: tuple[uuid.UUID, ...]


class SchedulerService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def create(self, value: ScheduleInput) -> ScheduledJob:
        key = value.key.strip()
        if not key or len(key) > 100:
            raise SchedulerError("Invalid schedule key")
        if value.job_type not in JOB_TYPES:
            raise SchedulerError("Unsupported scheduled job type")
        if not 15 <= value.interval_minutes <= 43_200:
            raise SchedulerError(
                "Schedule interval must be between 15 and 43200 minutes"
            )
        created_by = value.created_by.strip()
        if not created_by or len(created_by) > 200:
            raise SchedulerError("Invalid schedule owner")
        payload = _validated_payload(
            value.job_type,
            value.payload,
            ingestion_max_pages=self._settings.ingestion_api_max_pages,
            normalization_max_items=(
                self._settings.normalization_api_max_items
            ),
            extraction_max_items=(
                self._settings.problem_extraction_api_max_items
            ),
        )
        next_run_at = _as_utc(value.next_run_at)
        existing = self._session.scalar(
            select(ScheduledJob).where(ScheduledJob.key == key)
        )
        if existing is not None:
            expected = (
                value.job_type,
                value.interval_minutes,
                payload,
                next_run_at,
            )
            actual = (
                existing.job_type,
                existing.interval_minutes,
                existing.payload,
                _as_utc(existing.next_run_at),
            )
            if actual != expected:
                raise SchedulerError(
                    "Schedule key already exists with different data"
                )
            return existing
        now = datetime.now(UTC)
        result = ScheduledJob(
            key=key,
            job_type=value.job_type,
            status="active",
            interval_minutes=value.interval_minutes,
            payload=payload,
            next_run_at=next_run_at,
            last_run_at=None,
            lease_until=None,
            consecutive_failure_count=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._session.add(result)
        self._session.commit()
        return result

    def set_status(self, job_id: uuid.UUID, status: str) -> ScheduledJob:
        job = self._session.get(ScheduledJob, job_id)
        if job is None:
            raise SchedulerError("Scheduled job not found")
        if status not in {"active", "paused", "retired"}:
            raise SchedulerError("Unsupported scheduled job status")
        job.status = status
        job.lease_until = None
        job.updated_at = datetime.now(UTC)
        self._session.commit()
        return job

    async def run_due(
        self,
        *,
        as_of: datetime,
        limit: int = 10,
    ) -> SchedulerOutcome:
        now = _as_utc(as_of)
        jobs = list(
            self._session.scalars(
                select(ScheduledJob)
                .where(
                    ScheduledJob.status == "active",
                    ScheduledJob.next_run_at <= now,
                    or_(
                        ScheduledJob.lease_until.is_(None),
                        ScheduledJob.lease_until < now,
                    ),
                )
                .order_by(ScheduledJob.next_run_at, ScheduledJob.id)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
        )
        claimed: list[tuple[ScheduledJob, ScheduledJobRun]] = []
        for job in jobs:
            job.lease_until = now + timedelta(
                minutes=self._settings.scheduler_lease_minutes
            )
            run = ScheduledJobRun(
                scheduled_job_id=job.id,
                status="running",
                result={},
                error_class=None,
                error_message=None,
                started_at=now,
                finished_at=None,
            )
            self._session.add(run)
            claimed.append((job, run))
        self._session.commit()

        run_ids: list[uuid.UUID] = []
        succeeded = 0
        failed = 0
        for job, run in claimed:
            run_ids.append(run.id)
            try:
                result = await self._execute(job, now)
                run.status = "succeeded"
                run.result = result
                job.consecutive_failure_count = 0
                succeeded += 1
            except Exception as exc:
                self._session.rollback()
                job = self._session.get(ScheduledJob, job.id)
                run = self._session.get(ScheduledJobRun, run.id)
                if job is None or run is None:
                    raise
                run.status = "failed"
                run.result = {}
                run.error_class = type(exc).__name__[:100]
                run.error_message = str(exc)[:2_000]
                job.consecutive_failure_count += 1
                failed += 1
            finished_at = datetime.now(UTC)
            run.finished_at = finished_at
            job.last_run_at = finished_at
            job.next_run_at = _next_run(
                _as_utc(job.next_run_at),
                job.interval_minutes,
                now,
            )
            job.lease_until = None
            job.updated_at = finished_at
            self._session.commit()
        return SchedulerOutcome(
            considered_count=len(jobs),
            succeeded_count=succeeded,
            failed_count=failed,
            run_ids=tuple(run_ids),
        )

    async def _execute(self, job: ScheduledJob, now: datetime) -> dict:
        if job.job_type == "operations_evaluation":
            outcome = OperationsService(self._session).evaluate(
                as_of=now,
                freshness_hours=self._settings.source_freshness_hours,
                daily_budget_usd=self._settings.daily_cost_budget_usd,
                monthly_budget_usd=self._settings.monthly_cost_budget_usd,
            )
            return json.loads(json.dumps(asdict(outcome), default=str))
        if job.job_type == "opportunity_scoring":
            score = OpportunityScoringService(self._session).score(
                as_of=now,
                research_profile_id=uuid.UUID(
                    job.payload["research_profile_id"]
                ),
            )
            ranking = OpportunityScoringService(self._session).rank(
                score.run_id
            )
            return {
                "score_run_id": str(score.run_id),
                "opportunity_count": score.opportunity_count,
                "rankable_count": score.rankable_count,
                "excluded_count": score.excluded_count,
                "ranking_run_id": str(ranking.ranking_run_id),
                "ranked_count": ranking.ranked_count,
            }
        if job.job_type == "problem_analysis":
            return self._problem_analysis(job.payload, now)
        if job.job_type == "ingestion":
            return await self._ingest(job.payload)
        if job.job_type == "radar_scan":
            return await self._radar_scan(job.payload, now)
        raise SchedulerError("Unsupported scheduled job type")

    def _problem_analysis(self, payload: dict, now: datetime) -> dict:
        extractions = {}
        for source_key in payload["source_keys"]:
            if source_key == "github":
                extractor = GitHubProblemEvidenceExtractor(self._session)
            elif source_key == "stack_exchange":
                extractor = StackExchangeProblemEvidenceExtractor(
                    self._session
                )
            else:
                raise SchedulerError("Unsupported problem analysis source")
            outcome = extractor.extract_pending(
                limit=payload["extract_limit"]
            )
            extractions[source_key] = {
                "run_id": str(outcome.run_id),
                "status": outcome.status,
                "input_count": outcome.input_count,
                "evidence_count": outcome.evidence_count,
                "error_count": outcome.error_count,
            }
        clustering = ProblemClusteringEngine(self._session).cluster(
            as_of=now,
            source_created_from=None,
        )
        metrics = ProblemClusterMetricEngine(self._session).calculate(
            clustering.run_id
        )
        return {
            "extractions": extractions,
            "clustering": {
                "run_id": str(clustering.run_id),
                "cluster_count": clustering.cluster_count,
                "eligible_count": clustering.eligible_count,
            },
            "cluster_metrics": {
                "run_id": str(metrics.run_id),
                "cluster_count": metrics.cluster_count,
                "metric_count": metrics.metric_count,
                "error_count": metrics.error_count,
            },
            "next_gate": "cluster_review_and_claim_approval",
        }

    async def _ingest(self, payload: dict) -> dict:
        request_cost = Decimal(payload["request_cost_usd"])
        self._enforce_ingestion_budget(
            request_cost * Decimal(payload["max_pages"])
        )
        connector = create_connector(
            payload["connector_key"],
            self._settings,
        )
        if connector.source_key != payload["source_key"]:
            raise ConnectorRegistryError(
                "Connector does not belong to scheduled source"
            )
        try:
            outcome = await IngestionService(
                self._session,
                FileObjectStore(self._settings.raw_storage_path),
            ).discover(
                connector,
                payload["query"],
                resume=payload["resume"],
                max_pages=payload["max_pages"],
            )
            amount = request_cost * Decimal(outcome.request_count)
            source = self._session.scalar(
                select(DataSource).where(
                    DataSource.key == payload["source_key"]
                )
            )
            if source is None:
                raise SchedulerError("Scheduled source not found")
            OperationsService(self._session).record_cost(
                CostEntryInput(
                    external_key=f"ingestion:{outcome.run_id}",
                    operation_type="source_api_request",
                    amount=amount,
                    currency="USD",
                    occurred_at=datetime.now(UTC),
                    source_id=source.id,
                    units=Decimal(outcome.request_count),
                    details={
                        "connector_key": payload["connector_key"],
                        "request_cost_usd": str(request_cost),
                    },
                )
            )
            ingestion_run = self._session.get(IngestionRun, outcome.run_id)
            if ingestion_run is not None:
                ingestion_run.estimated_cost = amount
                self._session.commit()
            if outcome.status not in {"succeeded", "partial"}:
                raise SchedulerError(
                    f"Ingestion ended with status: {outcome.status}"
                )
            return {
                "ingestion_run_id": str(outcome.run_id),
                "status": outcome.status,
                "request_count": outcome.request_count,
                "raw_item_count": outcome.raw_item_count,
                "error_count": outcome.error_count,
                "cost_usd": str(amount),
            }
        finally:
            close = getattr(connector, "aclose", None)
            if close is not None:
                await close()

    def _enforce_ingestion_budget(self, estimated_cost: Decimal) -> None:
        if estimated_cost <= 0:
            return
        now = datetime.now(UTC)
        day_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_start = day_start.replace(day=1)
        operations = OperationsService(self._session)
        daily = operations.cost_total(day_start, now, "USD")
        monthly = operations.cost_total(month_start, now, "USD")
        if (
            self._settings.daily_cost_budget_usd > 0
            and daily + estimated_cost
            > self._settings.daily_cost_budget_usd
        ):
            raise SchedulerError("Daily ingestion budget would be exceeded")
        if (
            self._settings.monthly_cost_budget_usd > 0
            and monthly + estimated_cost
            > self._settings.monthly_cost_budget_usd
        ):
            raise SchedulerError(
                "Monthly ingestion budget would be exceeded"
            )

    async def _radar_scan(self, payload: dict, now: datetime) -> dict:
        result = {"ingestion": await self._ingest(payload)}
        normalizer = create_normalizer(payload["normalizer_key"])
        if normalizer.source_key != payload["source_key"]:
            raise SchedulerError(
                "Normalizer does not belong to scheduled source"
            )
        normalization = NormalizationService(
            self._session,
            FileObjectStore(self._settings.raw_storage_path),
        ).normalize_pending(
            normalizer,
            limit=payload["normalize_limit"],
        )
        result["normalization"] = {
            "run_id": str(normalization.run_id),
            "input_count": normalization.input_count,
            "success_count": normalization.success_count,
            "error_count": normalization.error_count,
        }
        extraction_source = payload.get("extraction_source_key")
        if extraction_source is None:
            result["extraction"] = {"status": "not_supported"}
            return result
        if extraction_source == "github":
            extractor = GitHubProblemEvidenceExtractor(self._session)
        elif extraction_source == "stack_exchange":
            extractor = StackExchangeProblemEvidenceExtractor(self._session)
        else:
            raise SchedulerError("Unsupported scheduled extraction source")
        extraction = extractor.extract_pending(
            limit=payload["extract_limit"]
        )
        result["extraction"] = {
            "run_id": str(extraction.run_id),
            "input_count": extraction.input_count,
            "evidence_count": extraction.evidence_count,
            "error_count": extraction.error_count,
        }
        if not payload["cluster_after_extraction"]:
            return result
        clustering = ProblemClusteringEngine(self._session).cluster(
            as_of=now,
            source_created_from=None,
        )
        result["clustering"] = {
            "run_id": str(clustering.run_id),
            "cluster_count": clustering.cluster_count,
            "eligible_count": clustering.eligible_count,
        }
        metrics = ProblemClusterMetricEngine(self._session).calculate(
            clustering.run_id
        )
        result["cluster_metrics"] = {
            "run_id": str(metrics.run_id),
            "cluster_count": metrics.cluster_count,
            "metric_count": metrics.metric_count,
            "error_count": metrics.error_count,
        }
        result["next_gate"] = "cluster_review_and_claim_approval"
        return result


def _validated_payload(
    job_type: str,
    payload: dict,
    *,
    ingestion_max_pages: int,
    normalization_max_items: int,
    extraction_max_items: int,
) -> dict:
    if not isinstance(payload, dict):
        raise SchedulerError("Schedule payload must be an object")
    if job_type == "operations_evaluation":
        if payload:
            raise SchedulerError(
                "Operations evaluation schedule takes no payload"
            )
        return {}
    if job_type == "opportunity_scoring":
        if set(payload) != {"research_profile_id"}:
            raise SchedulerError(
                "Opportunity scoring requires only research_profile_id"
            )
        try:
            research_profile_id = str(
                uuid.UUID(str(payload["research_profile_id"]))
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise SchedulerError("Invalid research_profile_id") from exc
        return {"research_profile_id": research_profile_id}
    if job_type == "problem_analysis":
        if set(payload) - {"source_keys", "extract_limit"}:
            raise SchedulerError(
                "Problem analysis payload contains unsupported fields"
            )
        source_keys = payload.get("source_keys")
        if (
            not isinstance(source_keys, list)
            or not source_keys
            or any(
                not isinstance(source_key, str)
                or source_key not in {"github", "stack_exchange"}
                for source_key in source_keys
            )
        ):
            raise SchedulerError(
                "Problem analysis requires supported source_keys"
            )
        if len(source_keys) != len(set(source_keys)):
            raise SchedulerError(
                "Problem analysis source_keys must be unique"
            )
        extract_limit = payload.get("extract_limit", 500)
        if (
            not isinstance(extract_limit, int)
            or not 1 <= extract_limit <= extraction_max_items
        ):
            raise SchedulerError(
                "extract_limit must be between 1 and "
                f"{extraction_max_items}"
            )
        return {
            "source_keys": source_keys,
            "extract_limit": extract_limit,
        }
    source_key = payload.get("source_key")
    connector_key = payload.get("connector_key") or source_key
    query = payload.get("query")
    if not isinstance(source_key, str) or not source_key.strip():
        raise SchedulerError("Scheduled ingestion requires source_key")
    if not isinstance(connector_key, str) or not connector_key.strip():
        raise SchedulerError("Scheduled ingestion requires connector_key")
    if not isinstance(query, dict):
        raise SchedulerError("Scheduled ingestion requires query")
    try:
        validated_query = validate_discovery_query(connector_key, query)
    except ConnectorRegistryError as exc:
        raise SchedulerError(str(exc)) from exc
    max_pages = payload.get("max_pages", 10)
    if (
        not isinstance(max_pages, int)
        or not 1 <= max_pages <= ingestion_max_pages
    ):
        raise SchedulerError(
            "Scheduled max_pages must be between 1 and "
            f"{ingestion_max_pages}"
        )
    result = {
        "source_key": source_key.strip(),
        "connector_key": connector_key.strip(),
        "query": validated_query,
        "resume": bool(payload.get("resume", True)),
        "max_pages": max_pages,
        "request_cost_usd": _request_cost(
            payload.get("request_cost_usd", "0")
        ),
    }
    if job_type == "ingestion":
        return result
    normalizer_key = payload.get("normalizer_key") or connector_key
    try:
        create_normalizer(normalizer_key)
    except NormalizerRegistryError as exc:
        raise SchedulerError(str(exc)) from exc
    normalize_limit = payload.get("normalize_limit", 500)
    if (
        not isinstance(normalize_limit, int)
        or not 1 <= normalize_limit <= normalization_max_items
    ):
        raise SchedulerError(
            "normalize_limit must be between 1 and "
            f"{normalization_max_items}"
        )
    extract_limit = payload.get("extract_limit", 500)
    if (
        not isinstance(extract_limit, int)
        or not 1 <= extract_limit <= extraction_max_items
    ):
        raise SchedulerError(
            "extract_limit must be between 1 and "
            f"{extraction_max_items}"
        )
    extraction_source = payload.get("extraction_source_key")
    if extraction_source not in {None, "github", "stack_exchange"}:
        raise SchedulerError("Unsupported scheduled extraction source")
    result.update(
        {
            "normalizer_key": normalizer_key,
            "normalize_limit": normalize_limit,
            "extraction_source_key": extraction_source,
            "extract_limit": extract_limit,
            "cluster_after_extraction": bool(
                payload.get("cluster_after_extraction", True)
            ),
        }
    )
    return result


def _request_cost(value) -> str:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SchedulerError("Invalid request_cost_usd") from exc
    if result < 0 or result > Decimal("10000"):
        raise SchedulerError(
            "request_cost_usd must be between 0 and 10000"
        )
    return str(result.quantize(Decimal("0.000001")))


def _next_run(current: datetime, interval_minutes: int, now: datetime) -> datetime:
    result = current
    step = timedelta(minutes=interval_minutes)
    while result <= now:
        result += step
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
