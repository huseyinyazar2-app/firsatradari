from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from firsat_radari.config import get_settings
from firsat_radari.db.models import (
    Repository,
    RepositoryObservation,
    ScheduledJob,
)
from firsat_radari.db.session import SessionLocal
from firsat_radari.scheduler.service import ScheduleInput, SchedulerService

_PILOT_SCHEDULES = (
    ScheduleInput(
        key="pilot-npm-workflow-automation",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "npm",
            "connector_key": "npm",
            "normalizer_key": "npm",
            "query": {"text": "workflow automation", "size": 50},
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
    ScheduleInput(
        key="pilot-github-workflow-automation",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "github",
            "connector_key": "github",
            "normalizer_key": "github",
            "query": {
                "q": (
                    '"workflow automation" in:name,description,readme '
                    "language:TypeScript stars:20..2000 archived:false"
                ),
                "sort": "updated",
                "order": "desc",
                "per_page": 50,
            },
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
    ScheduleInput(
        key="pilot-npm-mcp-agent-tooling",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "npm",
            "connector_key": "npm",
            "normalizer_key": "npm",
            "query": {"text": "mcp agent tooling", "size": 50},
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
    ScheduleInput(
        key="pilot-github-mcp-agent-tooling",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "github",
            "connector_key": "github",
            "normalizer_key": "github",
            "query": {
                "q": (
                    '"mcp" "ai agent" in:name,description,readme '
                    "language:TypeScript stars:20..2000 archived:false"
                ),
                "sort": "updated",
                "order": "desc",
                "per_page": 50,
            },
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
    ScheduleInput(
        key="pilot-npm-self-hosted-automation",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "npm",
            "connector_key": "npm",
            "normalizer_key": "npm",
            "query": {"text": "self hosted automation", "size": 50},
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
    ScheduleInput(
        key="pilot-github-self-hosted-automation",
        job_type="radar_scan",
        interval_minutes=10_080,
        payload={
            "source_key": "github",
            "connector_key": "github",
            "normalizer_key": "github",
            "query": {
                "q": (
                    '"self hosted" automation in:name,description,readme '
                    "language:TypeScript stars:20..2000 archived:false"
                ),
                "sort": "updated",
                "order": "desc",
                "per_page": 50,
            },
            "max_pages": 1,
            "normalize_limit": 50,
            "extraction_source_key": None,
            "cluster_after_extraction": False,
            "request_cost_usd": "0",
        },
        next_run_at=datetime.now(UTC),
        created_by="owner:huseyinyazar2-app",
    ),
)
_PILOT_ANALYSIS_SCHEDULE = ScheduleInput(
    key="pilot-problem-analysis",
    job_type="problem_analysis",
    interval_minutes=10_080,
    payload={
        "source_keys": ["github"],
        "extract_limit": 500,
    },
    next_run_at=datetime.now(UTC) + timedelta(minutes=30),
    created_by="owner:huseyinyazar2-app",
)
_PILOT_OPERATIONS_SCHEDULE = ScheduleInput(
    key="pilot-operations-evaluation",
    job_type="operations_evaluation",
    interval_minutes=60,
    payload={},
    next_run_at=datetime.now(UTC),
    created_by="owner:huseyinyazar2-app",
)
_MAX_ACTIVE_ISSUE_SCHEDULES = 10


def main() -> None:
    with SessionLocal() as session:
        service = SchedulerService(session, get_settings())
        issue_schedules = _issue_schedules(session)
        issue_schedule_keys = {
            schedule.key for schedule in issue_schedules
        }
        existing_jobs = {
            job.key: job for job in session.scalars(select(ScheduledJob))
        }
        schedules = (
            *_PILOT_SCHEDULES,
            *issue_schedules,
            _PILOT_ANALYSIS_SCHEDULE,
            _PILOT_OPERATIONS_SCHEDULE,
        )
        for schedule in schedules:
            existing = existing_jobs.get(schedule.key)
            if existing is not None:
                if (
                    schedule.key in issue_schedule_keys
                    and existing.status != "active"
                ):
                    service.set_status(existing.id, "active")
                    print(f"activated: {schedule.key}")
                    continue
                print(f"unchanged: {schedule.key}")
                continue
            service.create(schedule)
            print(f"created: {schedule.key}")
        _enforce_issue_schedule_limit(
            session,
            service,
            desired_keys=issue_schedule_keys,
        )


def _issue_schedules(session) -> tuple[ScheduleInput, ...]:
    repository_rows = session.scalars(
        select(Repository)
        .join(RepositoryObservation)
        .where(
            Repository.archived.is_(False),
            Repository.disabled.is_(False),
            RepositoryObservation.open_items_count.between(10, 100),
        )
        .order_by(
            RepositoryObservation.open_items_count.desc(),
            RepositoryObservation.stars_count.desc(),
        )
        .limit(50)
    )
    repositories = []
    seen_repository_ids = set()
    for repository in repository_rows:
        if repository.id in seen_repository_ids:
            continue
        seen_repository_ids.add(repository.id)
        repositories.append(repository)
        if len(repositories) == _MAX_ACTIVE_ISSUE_SCHEDULES:
            break
    now = datetime.now(UTC)
    return tuple(
        ScheduleInput(
            key=f"pilot-github-issues-{repository.full_name.casefold()}",
            job_type="radar_scan",
            interval_minutes=10_080,
            payload={
                "source_key": "github",
                "connector_key": "github_work_items",
                "normalizer_key": "github_work_items",
                "query": {
                    "q": (
                        f"repo:{repository.full_name} is:issue "
                        "is:open archived:false"
                    ),
                    "sort": "updated",
                    "order": "desc",
                    "per_page": 100,
                },
                "max_pages": 2,
                "normalize_limit": 500,
                "extraction_source_key": "github",
                "extract_limit": 500,
                "cluster_after_extraction": False,
                "request_cost_usd": "0",
            },
            next_run_at=now,
            created_by="owner:huseyinyazar2-app",
        )
        for repository in repositories
    )


def _enforce_issue_schedule_limit(
    session,
    service: SchedulerService,
    *,
    desired_keys: set[str],
) -> None:
    active_jobs = list(
        session.scalars(
            select(ScheduledJob)
            .where(
                ScheduledJob.key.like("pilot-github-issues-%"),
                ScheduledJob.status == "active",
            )
        )
    )
    for job in active_jobs:
        if job.key in desired_keys:
            continue
        service.set_status(job.id, "paused")
        print(f"paused (outside current pilot cohort): {job.key}")


if __name__ == "__main__":
    main()
