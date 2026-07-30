import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import AuditEvent, CostEntry, OperationalAlert
from firsat_radari.operations.service import (
    CostEntryInput,
    OperationsError,
    OperationsEvaluation,
    OperationsService,
)

router = APIRouter(tags=["operations"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class CreateCostEntryRequest(BaseModel):
    external_key: str = Field(min_length=3, max_length=120)
    operation_type: str = Field(min_length=1, max_length=60)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    occurred_at: datetime
    source_id: uuid.UUID | None = None
    opportunity_id: uuid.UUID | None = None
    experiment_id: uuid.UUID | None = None
    units: Decimal | None = Field(default=None, ge=0)
    details: dict = Field(default_factory=dict)


class CostEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_key: str
    operation_type: str
    source_id: uuid.UUID | None
    opportunity_id: uuid.UUID | None
    experiment_id: uuid.UUID | None
    amount: Decimal
    currency: str
    units: Decimal | None
    details: dict
    occurred_at: datetime
    created_at: datetime


class OperationalAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_key: str
    source_id: uuid.UUID | None
    category: str
    severity: str
    status: str
    message: str
    details: dict
    first_detected_at: datetime
    last_detected_at: datetime
    resolved_at: datetime | None


class EvaluateOperationsRequest(BaseModel):
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OperationsEvaluationResponse(BaseModel):
    evaluated_source_count: int
    opened_alert_count: int
    resolved_alert_count: int
    open_alert_count: int
    evaluated_at: datetime


class OperationsSummaryResponse(BaseModel):
    open_alert_count: int
    critical_alert_count: int
    warning_alert_count: int
    daily_cost_usd: Decimal
    monthly_cost_usd: Decimal
    daily_budget_usd: Decimal
    monthly_budget_usd: Decimal
    budget_status: str
    generated_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: str
    actor: str
    method: str
    path: str
    status_code: int
    outcome: str
    duration_ms: int
    details: dict
    occurred_at: datetime


@router.post(
    "/cost-entries",
    response_model=CostEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cost_entry(
    request: CreateCostEntryRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CostEntry:
    _ensure_enabled(settings)
    try:
        return OperationsService(session).record_cost(
            CostEntryInput(**request.model_dump())
        )
    except OperationsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/cost-entries", response_model=list[CostEntryResponse])
def list_cost_entries(
    session: DatabaseSession,
    currency: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CostEntry]:
    statement = select(CostEntry).order_by(CostEntry.occurred_at.desc()).limit(limit)
    if currency:
        statement = statement.where(CostEntry.currency == currency.upper())
    return list(session.scalars(statement))


@router.post(
    "/operations/evaluate",
    response_model=OperationsEvaluationResponse,
)
def evaluate_operations(
    request: EvaluateOperationsRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OperationsEvaluation:
    _ensure_enabled(settings)
    return OperationsService(session).evaluate(
        as_of=request.as_of,
        freshness_hours=settings.source_freshness_hours,
        daily_budget_usd=settings.daily_cost_budget_usd,
        monthly_budget_usd=settings.monthly_cost_budget_usd,
    )


@router.get("/operational-alerts", response_model=list[OperationalAlertResponse])
def list_operational_alerts(
    session: DatabaseSession,
    alert_status: str | None = Query(default="open", alias="status"),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[OperationalAlert]:
    statement = (
        select(OperationalAlert)
        .order_by(
            OperationalAlert.status,
            OperationalAlert.severity,
            OperationalAlert.last_detected_at.desc(),
        )
        .limit(limit)
    )
    if alert_status is not None:
        statement = statement.where(OperationalAlert.status == alert_status)
    return list(session.scalars(statement))


@router.get("/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    session: DatabaseSession,
    actor: str | None = None,
    outcome: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEvent]:
    statement = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    if actor:
        statement = statement.where(AuditEvent.actor == actor)
    if outcome:
        statement = statement.where(AuditEvent.outcome == outcome)
    return list(session.scalars(statement))


@router.get("/operations/summary", response_model=OperationsSummaryResponse)
def get_operations_summary(
    session: DatabaseSession,
    settings: AppSettings,
) -> OperationsSummaryResponse:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    alerts = list(
        session.scalars(
            select(OperationalAlert).where(OperationalAlert.status == "open")
        )
    )
    service = OperationsService(session)
    daily = service.cost_total(day_start, now, "USD")
    monthly = service.cost_total(month_start, now, "USD")
    status_value = "ok"
    if (
        settings.daily_cost_budget_usd > 0
        and daily >= settings.daily_cost_budget_usd
    ) or (
        settings.monthly_cost_budget_usd > 0
        and monthly >= settings.monthly_cost_budget_usd
    ):
        status_value = "blocked"
    elif any(alert.severity == "critical" for alert in alerts):
        status_value = "attention"
    return OperationsSummaryResponse(
        open_alert_count=len(alerts),
        critical_alert_count=sum(a.severity == "critical" for a in alerts),
        warning_alert_count=sum(a.severity == "warning" for a in alerts),
        daily_cost_usd=daily,
        monthly_cost_usd=monthly,
        daily_budget_usd=settings.daily_cost_budget_usd,
        monthly_budget_usd=settings.monthly_cost_budget_usd,
        budget_status=status_value,
        generated_at=now,
    )


def _ensure_enabled(settings: Settings) -> None:
    if not settings.operations_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operations mutation API is disabled",
        )
