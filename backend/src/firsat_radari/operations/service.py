import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    CommercialValidationExperiment,
    CostEntry,
    DataQualityEvent,
    DataSource,
    IngestionCollection,
    IngestionRun,
    OperationalAlert,
    Opportunity,
    RawSnapshot,
    RequestRecord,
)

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_EXTERNAL_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")


class OperationsError(ValueError):
    pass


@dataclass(frozen=True)
class CostEntryInput:
    external_key: str
    operation_type: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    source_id: uuid.UUID | None = None
    opportunity_id: uuid.UUID | None = None
    experiment_id: uuid.UUID | None = None
    units: Decimal | None = None
    details: dict | None = None


@dataclass(frozen=True)
class OperationsEvaluation:
    evaluated_source_count: int
    opened_alert_count: int
    resolved_alert_count: int
    open_alert_count: int
    evaluated_at: datetime


@dataclass(frozen=True)
class _AlertValue:
    key: str
    source_id: uuid.UUID | None
    category: str
    severity: str
    message: str
    details: dict


class OperationsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_cost(self, value: CostEntryInput) -> CostEntry:
        external_key = value.external_key.strip()
        if not _EXTERNAL_KEY.fullmatch(external_key):
            raise OperationsError("Invalid cost external key")
        operation_type = value.operation_type.strip()
        if not operation_type or len(operation_type) > 60:
            raise OperationsError("Invalid cost operation type")
        if value.amount < 0:
            raise OperationsError("Cost amount cannot be negative")
        currency = value.currency.strip().upper()
        if not _CURRENCY.fullmatch(currency):
            raise OperationsError("Currency must be a three-letter ISO code")
        if value.units is not None and value.units < 0:
            raise OperationsError("Cost units cannot be negative")
        occurred_at = _as_utc(value.occurred_at)
        if occurred_at > datetime.now(UTC) + timedelta(minutes=5):
            raise OperationsError("Cost cannot occur in the future")
        self._validate_references(value)

        existing = self._session.scalar(
            select(CostEntry).where(CostEntry.external_key == external_key)
        )
        if existing is not None:
            expected = (
                operation_type,
                value.amount.quantize(Decimal("0.000001")),
                currency,
                value.source_id,
                value.opportunity_id,
                value.experiment_id,
                value.units,
                value.details or {},
                occurred_at,
            )
            actual = (
                existing.operation_type,
                existing.amount,
                existing.currency,
                existing.source_id,
                existing.opportunity_id,
                existing.experiment_id,
                existing.units,
                existing.details,
                _as_utc(existing.occurred_at),
            )
            if actual != expected:
                raise OperationsError(
                    "Cost external key was already used with different data"
                )
            return existing

        entry = CostEntry(
            external_key=external_key,
            operation_type=operation_type,
            source_id=value.source_id,
            opportunity_id=value.opportunity_id,
            experiment_id=value.experiment_id,
            amount=value.amount.quantize(Decimal("0.000001")),
            currency=currency,
            units=value.units,
            details=value.details or {},
            occurred_at=occurred_at,
            created_at=datetime.now(UTC),
        )
        self._session.add(entry)
        self._session.commit()
        return entry

    def evaluate(
        self,
        *,
        as_of: datetime,
        freshness_hours: int,
        daily_budget_usd: Decimal,
        monthly_budget_usd: Decimal,
    ) -> OperationsEvaluation:
        evaluated_at = _as_utc(as_of)
        desired: dict[str, _AlertValue] = {}
        sources = list(
            self._session.scalars(
                select(DataSource).where(DataSource.enabled.is_(True))
            )
        )
        for source in sources:
            for alert in self._source_alerts(
                source,
                evaluated_at,
                freshness_hours,
            ):
                desired[alert.key] = alert

        day_start = evaluated_at.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start.replace(day=1)
        daily_cost = self.cost_total(day_start, evaluated_at, "USD")
        monthly_cost = self.cost_total(month_start, evaluated_at, "USD")
        if daily_budget_usd > 0 and daily_cost >= daily_budget_usd:
            alert = _AlertValue(
                key="global:daily_cost_budget",
                source_id=None,
                category="cost_budget",
                severity="critical",
                message="Daily USD cost budget reached",
                details={
                    "actual": str(daily_cost),
                    "budget": str(daily_budget_usd),
                },
            )
            desired[alert.key] = alert
        if monthly_budget_usd > 0 and monthly_cost >= monthly_budget_usd:
            alert = _AlertValue(
                key="global:monthly_cost_budget",
                source_id=None,
                category="cost_budget",
                severity="critical",
                message="Monthly USD cost budget reached",
                details={
                    "actual": str(monthly_cost),
                    "budget": str(monthly_budget_usd),
                },
            )
            desired[alert.key] = alert

        existing = {
            alert.alert_key: alert
            for alert in self._session.scalars(select(OperationalAlert))
        }
        opened_count = 0
        resolved_count = 0
        for key, value in desired.items():
            alert = existing.get(key)
            if alert is None:
                alert = OperationalAlert(
                    alert_key=value.key,
                    source_id=value.source_id,
                    category=value.category,
                    severity=value.severity,
                    status="open",
                    message=value.message,
                    details=value.details,
                    first_detected_at=evaluated_at,
                    last_detected_at=evaluated_at,
                    resolved_at=None,
                )
                self._session.add(alert)
                opened_count += 1
                continue
            if alert.status != "open":
                alert.status = "open"
                alert.first_detected_at = evaluated_at
                alert.resolved_at = None
                opened_count += 1
            alert.source_id = value.source_id
            alert.category = value.category
            alert.severity = value.severity
            alert.message = value.message
            alert.details = value.details
            alert.last_detected_at = evaluated_at

        for key, alert in existing.items():
            if alert.status == "open" and key not in desired:
                alert.status = "resolved"
                alert.resolved_at = evaluated_at
                resolved_count += 1

        self._session.commit()
        open_count = self._session.scalar(
            select(func.count())
            .select_from(OperationalAlert)
            .where(OperationalAlert.status == "open")
        )
        return OperationsEvaluation(
            evaluated_source_count=len(sources),
            opened_alert_count=opened_count,
            resolved_alert_count=resolved_count,
            open_alert_count=int(open_count or 0),
            evaluated_at=evaluated_at,
        )

    def cost_total(
        self,
        start_at: datetime,
        end_at: datetime,
        currency: str,
    ) -> Decimal:
        value = self._session.scalar(
            select(func.coalesce(func.sum(CostEntry.amount), 0)).where(
                CostEntry.currency == currency,
                CostEntry.occurred_at >= start_at,
                CostEntry.occurred_at <= end_at,
            )
        )
        return Decimal(value or 0).quantize(Decimal("0.000001"))

    def _source_alerts(
        self,
        source: DataSource,
        as_of: datetime,
        freshness_hours: int,
    ) -> list[_AlertValue]:
        prefix = f"source:{source.id}"
        alerts: list[_AlertValue] = []
        latest_run = self._session.scalar(
            select(IngestionRun)
            .where(IngestionRun.source_id == source.id)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        latest_usable = self._session.scalar(
            select(IngestionRun)
            .where(
                IngestionRun.source_id == source.id,
                or_(
                    IngestionRun.status == "succeeded",
                    and_(
                        IngestionRun.status == "partial",
                        IngestionRun.raw_item_count > 0,
                    ),
                ),
            )
            .order_by(IngestionRun.finished_at.desc())
            .limit(1)
        )
        if latest_run is not None and latest_run.status in {"failed", "partial"}:
            alerts.append(
                _AlertValue(
                    key=f"{prefix}:run_failure",
                    source_id=source.id,
                    category="source_failure",
                    severity="critical" if latest_run.status == "failed" else "warning",
                    message=f"{source.key} latest ingestion is {latest_run.status}",
                    details={"run_id": str(latest_run.id)},
                )
            )
        if latest_usable is None or latest_usable.finished_at is None:
            alerts.append(
                _AlertValue(
                    key=f"{prefix}:never_succeeded",
                    source_id=source.id,
                    category="freshness",
                    severity="critical",
                    message=f"{source.key} has no usable ingestion",
                    details={"freshness_hours": freshness_hours},
                )
            )
        else:
            finished_at = _as_utc(latest_usable.finished_at)
            age_hours = max(
                Decimal("0"),
                Decimal(str((as_of - finished_at).total_seconds() / 3600)),
            )
            if age_hours > freshness_hours:
                alerts.append(
                    _AlertValue(
                        key=f"{prefix}:stale",
                        source_id=source.id,
                        category="freshness",
                        severity="warning",
                        message=f"{source.key} data is stale",
                        details={
                            "age_hours": str(age_hours.quantize(Decimal("0.01"))),
                            "freshness_hours": freshness_hours,
                            "last_success_at": finished_at.isoformat(),
                        },
                    )
                )
        open_quality = self._session.scalar(
            select(func.count())
            .select_from(DataQualityEvent)
            .where(
                DataQualityEvent.source_id == source.id,
                DataQualityEvent.resolved_at.is_(None),
                DataQualityEvent.severity.in_(
                    ("warning", "error", "critical")
                ),
            )
        )
        if open_quality:
            alerts.append(
                _AlertValue(
                    key=f"{prefix}:quality",
                    source_id=source.id,
                    category="data_quality",
                    severity="warning",
                    message=f"{source.key} has open data-quality events",
                    details={"count": int(open_quality)},
                )
            )
        incomplete = self._session.scalar(
            select(func.count())
            .select_from(IngestionCollection)
            .where(
                IngestionCollection.source_id == source.id,
                IngestionCollection.is_complete.is_(False),
            )
        )
        latest_request = self._session.scalar(
            select(RequestRecord)
            .join(IngestionRun, IngestionRun.id == RequestRecord.run_id)
            .where(IngestionRun.source_id == source.id)
            .order_by(RequestRecord.requested_at.desc())
            .limit(1)
        )
        if (
            latest_request is not None
            and latest_request.rate_limit_remaining is not None
        ):
            remaining = latest_request.rate_limit_remaining
            limit = latest_request.rate_limit_limit
            exhausted = remaining == 0
            nearly_exhausted = (
                limit is not None
                and limit > 0
                and Decimal(remaining) / Decimal(limit) <= Decimal("0.10")
            )
            if exhausted or nearly_exhausted:
                alerts.append(
                    _AlertValue(
                        key=f"{prefix}:quota",
                        source_id=source.id,
                        category="source_quota",
                        severity="critical" if exhausted else "warning",
                        message=(
                            f"{source.key} quota is exhausted"
                            if exhausted
                            else f"{source.key} quota is nearly exhausted"
                        ),
                        details={
                            "remaining": remaining,
                            "limit": limit,
                            "reset_at": (
                                latest_request.rate_limit_reset_at.isoformat()
                                if latest_request.rate_limit_reset_at
                                else None
                            ),
                        },
                    )
                )
        if incomplete:
            alerts.append(
                _AlertValue(
                    key=f"{prefix}:incomplete_collections",
                    source_id=source.id,
                    category="collection_completeness",
                    severity="warning",
                    message=f"{source.key} has incomplete collections",
                    details={"count": int(incomplete)},
                )
            )
        expired_snapshots = self._session.scalar(
            select(func.count())
            .select_from(RawSnapshot)
            .where(
                RawSnapshot.source_id == source.id,
                RawSnapshot.retention_until.is_not(None),
                RawSnapshot.retention_until < as_of,
                RawSnapshot.purged_at.is_(None),
            )
        )
        if expired_snapshots:
            alerts.append(
                _AlertValue(
                    key=f"{prefix}:retention_expired",
                    source_id=source.id,
                    category="retention_expiry",
                    severity="critical",
                    message=f"{source.key} has expired retained snapshots",
                    details={"count": int(expired_snapshots)},
                )
            )
        return alerts

    def _validate_references(self, value: CostEntryInput) -> None:
        references = (
            (DataSource, value.source_id, "Source"),
            (Opportunity, value.opportunity_id, "Opportunity"),
            (
                CommercialValidationExperiment,
                value.experiment_id,
                "Commercial validation experiment",
            ),
        )
        for model, identifier, label in references:
            if identifier is not None and self._session.get(model, identifier) is None:
                raise OperationsError(f"{label} not found")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
