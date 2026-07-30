from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.config import Settings
from firsat_radari.db.base import Base
from firsat_radari.db.models import ScheduledJobRun
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
