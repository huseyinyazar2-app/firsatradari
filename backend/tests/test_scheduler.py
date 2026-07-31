import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.config import Settings
from firsat_radari.connectors.base import CollectionResult, CollectionStatus
from firsat_radari.db.base import Base
from firsat_radari.db.models import DataSource, ScheduledJob, ScheduledJobRun
from firsat_radari.profiles.service import (
    ProfileInput,
    ResearchProfileService,
    VerticalInput,
)
from firsat_radari.scheduler.service import (
    ScheduleInput,
    SchedulerError,
    SchedulerService,
)
from scripts.bootstrap_pilot_schedules import _enforce_issue_schedule_limit


def _context() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.asyncio
async def test_due_schedule_runs_once_and_advances_next_run() -> None:
    context = _context()
    session = next(context)
    try:
        now = datetime.now(UTC)
        service = SchedulerService(
            session,
            Settings(environment="test", database_url="sqlite://"),
        )
        job = service.create(
            ScheduleInput(
                key="operations-health",
                job_type="operations_evaluation",
                interval_minutes=60,
                payload={},
                next_run_at=now - timedelta(minutes=1),
                created_by="test",
            )
        )

        first = await service.run_due(as_of=now)
        repeated = await service.run_due(as_of=now)

        assert first.considered_count == 1
        assert first.succeeded_count == 1
        assert first.failed_count == 0
        assert repeated.considered_count == 0
        assert job.next_run_at > now
        run = session.get(ScheduledJobRun, first.run_ids[0])
        assert run is not None
        assert run.status == "succeeded"
        assert run.result["evaluated_source_count"] == 0
    finally:
        context.close()


def test_ingestion_schedule_respects_configured_page_limit() -> None:
    context = _context()
    session = next(context)
    try:
        service = SchedulerService(
            session,
            Settings(
                environment="test",
                database_url="sqlite://",
                ingestion_api_max_pages=2,
            ),
        )
        with pytest.raises(
            SchedulerError,
            match="Scheduled max_pages must be between 1 and 2",
        ):
            service.create(
                ScheduleInput(
                    key="github-too-wide",
                    job_type="ingestion",
                    interval_minutes=60,
                    payload={
                        "source_key": "github",
                        "connector_key": "github",
                        "query": {"q": "is:issue is:open"},
                        "max_pages": 3,
                    },
                    next_run_at=datetime.now(UTC),
                    created_by="test",
                )
            )
    finally:
        context.close()


def test_pilot_issue_schedule_reconciliation_pauses_outside_cohort() -> None:
    context = _context()
    session = next(context)
    try:
        service = SchedulerService(
            session,
            Settings(environment="test", database_url="sqlite://"),
        )
        jobs = [
            service.create(
                ScheduleInput(
                    key=f"pilot-github-issues-example/repository-{index}",
                    job_type="operations_evaluation",
                    interval_minutes=60,
                    payload={},
                    next_run_at=datetime.now(UTC),
                    created_by="test",
                )
            )
            for index in range(3)
        ]

        _enforce_issue_schedule_limit(
            session,
            service,
            desired_keys={jobs[0].key, jobs[2].key},
        )

        session.expire_all()
        statuses = {
            job.key: job.status
            for job in session.query(ScheduledJob).all()
        }
        assert statuses[jobs[0].key] == "active"
        assert statuses[jobs[1].key] == "paused"
        assert statuses[jobs[2].key] == "active"
    finally:
        context.close()


@pytest.mark.asyncio
async def test_scoring_schedule_uses_an_explicit_research_profile() -> None:
    context = _context()
    session = next(context)
    try:
        profiles = ResearchProfileService(session)
        vertical = profiles.create_vertical(
            VerticalInput(
                key="software",
                version="1.0.0",
                name="Software",
                status="active",
                config={},
                selection_rationale="Scheduled score test",
                created_by="test",
            )
        )
        profile = profiles.create_profile(
            ProfileInput(
                vertical_definition_id=vertical.id,
                key="solo-founder",
                version="1.0.0",
                name="Solo founder",
                status="active",
                constraints={},
                exclusions={},
                preferences={},
                created_by="test",
            )
        )
        now = datetime.now(UTC)
        service = SchedulerService(
            session,
            Settings(environment="test", database_url="sqlite://"),
        )
        service.create(
            ScheduleInput(
                key="score-opportunities",
                job_type="opportunity_scoring",
                interval_minutes=60,
                payload={"research_profile_id": str(profile.id)},
                next_run_at=now,
                created_by="test",
            )
        )

        result = await service.run_due(as_of=now)

        assert result.succeeded_count == 1
        run = session.get(ScheduledJobRun, result.run_ids[0])
        assert run is not None
        assert run.result["opportunity_count"] == 0
        assert run.result["ranked_count"] == 0
    finally:
        context.close()


@pytest.mark.asyncio
async def test_problem_analysis_refreshes_extraction_clusters_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extraction_run_id = uuid.uuid4()
    clustering_run_id = uuid.uuid4()
    metric_run_id = uuid.uuid4()
    extractor = Mock()
    extractor.return_value.extract_pending.return_value = SimpleNamespace(
        run_id=extraction_run_id,
        status="succeeded",
        input_count=3,
        evidence_count=2,
        error_count=0,
    )
    clustering = Mock()
    clustering.return_value.cluster.return_value = SimpleNamespace(
        run_id=clustering_run_id,
        cluster_count=1,
        eligible_count=2,
    )
    metrics = Mock()
    metrics.return_value.calculate.return_value = SimpleNamespace(
        run_id=metric_run_id,
        cluster_count=1,
        metric_count=9,
        error_count=0,
    )

    monkeypatch.setattr(
        "firsat_radari.scheduler.service.GitHubProblemEvidenceExtractor",
        extractor,
    )
    monkeypatch.setattr(
        "firsat_radari.scheduler.service.ProblemClusteringEngine",
        clustering,
    )
    monkeypatch.setattr(
        "firsat_radari.scheduler.service.ProblemClusterMetricEngine",
        metrics,
    )
    context = _context()
    session = next(context)
    try:
        now = datetime.now(UTC)
        service = SchedulerService(
            session,
            Settings(environment="test", database_url="sqlite://"),
        )
        service.create(
            ScheduleInput(
                key="problem-analysis",
                job_type="problem_analysis",
                interval_minutes=60,
                payload={
                    "source_keys": ["github"],
                    "extract_limit": 25,
                },
                next_run_at=now,
                created_by="test",
            )
        )

        result = await service.run_due(as_of=now)

        run = session.get(ScheduledJobRun, result.run_ids[0])
        assert run is not None
        assert result.succeeded_count == 1, run.error_message
        assert run.result["extractions"]["github"]["input_count"] == 3
        assert run.result["clustering"]["cluster_count"] == 1
        assert run.result["cluster_metrics"]["metric_count"] == 9
        extractor.return_value.extract_pending.assert_called_once_with(
            limit=25
        )
        metrics.return_value.calculate.assert_called_once_with(
            clustering_run_id
        )
    finally:
        context.close()


@pytest.mark.asyncio
async def test_one_off_radar_scan_is_validated_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context()
    session = next(context)
    try:
        service = SchedulerService(
            session,
            Settings(
                environment="test",
                database_url="sqlite://",
                ingestion_api_max_pages=1,
                normalization_api_max_items=50,
                problem_extraction_api_max_items=50,
            ),
        )
        scan = Mock(return_value={"status": "succeeded"})

        async def run_scan(payload, now):
            return scan(payload, now)

        monkeypatch.setattr(service, "_radar_scan", run_scan)
        now = datetime.now(UTC)

        result = await service.run_radar_scan(
            {
                "source_key": "github",
                "connector_key": "github_work_items",
                "normalizer_key": "github_work_items",
                "query": {
                    "q": "workflow automation is:issue is:open",
                    "per_page": 50,
                },
                "max_pages": 1,
                "normalize_limit": 50,
                "extraction_source_key": "github",
                "extract_limit": 50,
                "cluster_after_extraction": True,
                "request_cost_usd": "0",
            },
            as_of=now,
        )

        assert result == {"status": "succeeded"}
        payload, called_at = scan.call_args.args
        assert payload["connector_key"] == "github_work_items"
        assert payload["max_pages"] == 1
        assert payload["normalize_limit"] == 50
        assert payload["extract_limit"] == 50
        assert payload["cluster_after_extraction"] is True
        assert called_at == now
    finally:
        context.close()


@pytest.mark.asyncio
async def test_rate_limited_ingestion_fails_the_scheduled_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class RateLimitedConnector:
        source_key = "github"
        job_type = "discovery"
        version = "test"

        async def discover(self, query, checkpoint=None):
            return CollectionResult(
                status=CollectionStatus.RATE_LIMITED,
                is_complete=False,
                errors=["rate_limited"],
            )

        async def fetch(self, external_id):
            return CollectionResult(
                status=CollectionStatus.FAILED_PERMANENT,
                errors=["unsupported"],
            )

    monkeypatch.setattr(
        "firsat_radari.scheduler.service.create_connector",
        lambda connector_key, settings: RateLimitedConnector(),
    )
    context = _context()
    session = next(context)
    try:
        session.add(
            DataSource(
                key="github",
                source_type="code_host",
                evidence_family_key="developer_activity",
                independence_group_key="github",
                independence_status="independent",
                owner="GitHub",
                base_url="https://api.github.com",
                policy_status="approved",
                policy_version="test",
                commercial_use_status="allowed",
                storage_permission="allowed",
                derived_data_permission="allowed",
                llm_processing_permission="prohibited",
                retention_days=30,
                enabled=True,
            )
        )
        session.commit()
        now = datetime.now(UTC)
        service = SchedulerService(
            session,
            Settings(
                environment="test",
                database_url="sqlite://",
                raw_storage_path=tmp_path,
            ),
        )
        service.create(
            ScheduleInput(
                key="rate-limited-ingestion",
                job_type="ingestion",
                interval_minutes=60,
                payload={
                    "source_key": "github",
                    "connector_key": "github",
                    "query": {"q": "workflow automation"},
                    "max_pages": 1,
                },
                next_run_at=now,
                created_by="test",
            )
        )

        result = await service.run_due(as_of=now)

        assert result.failed_count == 1
        run = session.get(ScheduledJobRun, result.run_ids[0])
        assert run is not None
        assert run.status == "failed"
        assert run.error_message == "Ingestion ended with status: rate_limited"
    finally:
        context.close()


def test_radar_scan_schedule_has_bounded_stage_configuration() -> None:
    context = _context()
    session = next(context)
    try:
        service = SchedulerService(
            session,
            Settings(
                environment="test",
                database_url="sqlite://",
                ingestion_api_max_pages=2,
                normalization_api_max_items=50,
                problem_extraction_api_max_items=25,
            ),
        )
        job = service.create(
            ScheduleInput(
                key="stack-exchange-radar",
                job_type="radar_scan",
                interval_minutes=60,
                payload={
                    "source_key": "stack_exchange",
                    "connector_key": "stack_exchange_questions",
                    "normalizer_key": "stack_exchange_questions",
                    "extraction_source_key": "stack_exchange",
                    "query": {
                        "site": "stackoverflow",
                        "tags": ["saas"],
                        "from_date": "2026-07-01",
                        "to_date": "2026-07-30",
                    },
                    "max_pages": 2,
                    "normalize_limit": 50,
                    "extract_limit": 25,
                    "request_cost_usd": "0.01",
                },
                next_run_at=datetime.now(UTC),
                created_by="test",
            )
        )

        assert job.payload["request_cost_usd"] == "0.010000"
        assert job.payload["cluster_after_extraction"] is True
        assert job.payload["extract_limit"] == 25
    finally:
        context.close()
