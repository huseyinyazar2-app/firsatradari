import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import ScheduledJob, ScheduledJobRun
from firsat_radari.scheduler.service import (
    ScheduleInput,
    SchedulerError,
    SchedulerOutcome,
    SchedulerService,
)

router = APIRouter(tags=["scheduler"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class CreateScheduleRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    job_type: str
    interval_minutes: int = Field(ge=15, le=43_200)
    payload: dict = Field(default_factory=dict)
    next_run_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(min_length=1, max_length=200)


class UpdateScheduleStatusRequest(BaseModel):
    status: str


class RunDueRequest(BaseModel):
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    limit: int = Field(default=10, ge=1, le=100)


class ScheduledJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    job_type: str
    status: str
    interval_minutes: int
    payload: dict
    next_run_at: datetime
    last_run_at: datetime | None
    lease_until: datetime | None
    consecutive_failure_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class ScheduledJobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheduled_job_id: uuid.UUID
    status: str
    result: dict
    error_class: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class SchedulerOutcomeResponse(BaseModel):
    considered_count: int
    succeeded_count: int
    failed_count: int
    run_ids: tuple[uuid.UUID, ...]


@router.post(
    "/scheduled-jobs",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scheduled_job(
    request: CreateScheduleRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ScheduledJob:
    _ensure_enabled(settings)
    try:
        return SchedulerService(session, settings).create(
            ScheduleInput(**request.model_dump())
        )
    except SchedulerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/scheduled-jobs", response_model=list[ScheduledJobResponse])
def list_scheduled_jobs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ScheduledJob]:
    return list(
        session.scalars(
            select(ScheduledJob)
            .order_by(ScheduledJob.next_run_at, ScheduledJob.key)
            .limit(limit)
        )
    )


@router.patch(
    "/scheduled-jobs/{job_id}/status",
    response_model=ScheduledJobResponse,
)
def update_scheduled_job_status(
    job_id: uuid.UUID,
    request: UpdateScheduleStatusRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ScheduledJob:
    _ensure_enabled(settings)
    try:
        return SchedulerService(session, settings).set_status(
            job_id,
            request.status,
        )
    except SchedulerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/scheduler/run-due", response_model=SchedulerOutcomeResponse)
async def run_due_scheduled_jobs(
    request: RunDueRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> SchedulerOutcome:
    _ensure_enabled(settings)
    return await SchedulerService(session, settings).run_due(
        as_of=request.as_of,
        limit=request.limit,
    )


@router.get(
    "/scheduled-job-runs",
    response_model=list[ScheduledJobRunResponse],
)
def list_scheduled_job_runs(
    session: DatabaseSession,
    scheduled_job_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ScheduledJobRun]:
    statement = (
        select(ScheduledJobRun)
        .order_by(ScheduledJobRun.started_at.desc())
        .limit(limit)
    )
    if scheduled_job_id is not None:
        statement = statement.where(
            ScheduledJobRun.scheduled_job_id == scheduled_job_id
        )
    return list(session.scalars(statement))


def _ensure_enabled(settings: Settings) -> None:
    if not settings.scheduler_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler API is disabled",
        )
