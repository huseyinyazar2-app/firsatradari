import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.db.models import (
    CommercialOutcome,
    CostEntry,
    OperationalAlert,
    Opportunity,
    OpportunityScoreRun,
    OpportunityScoreSnapshot,
    OpportunityVersion,
    ProblemCluster,
)

router = APIRouter(prefix="/reports", tags=["reports"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


class ReportOpportunity(BaseModel):
    opportunity_version_id: uuid.UUID
    title: str
    total_score: Decimal | None
    potential_score: Decimal
    actionability_score: Decimal
    confidence_score: Decimal
    uncertainty: Decimal
    status: str


class ResearchReportResponse(BaseModel):
    period: str
    period_start: datetime
    period_end: datetime
    new_opportunity_count: int
    new_problem_cluster_count: int
    latest_score_run_id: uuid.UUID | None
    rankable_count: int
    verified_commercial_outcome_count: int
    open_alert_count: int
    critical_alert_count: int
    cost_by_currency: dict[str, Decimal]
    top_opportunities: list[ReportOpportunity]


@router.get("/weekly", response_model=ResearchReportResponse)
def weekly_report(
    session: DatabaseSession,
    as_of: datetime | None = None,
) -> ResearchReportResponse:
    return _build_report(session, "weekly", as_of, days=7)


@router.get("/monthly", response_model=ResearchReportResponse)
def monthly_report(
    session: DatabaseSession,
    as_of: datetime | None = None,
) -> ResearchReportResponse:
    return _build_report(session, "monthly", as_of, days=30)


def _build_report(
    session: Session,
    period: str,
    as_of: datetime | None,
    *,
    days: int,
) -> ResearchReportResponse:
    period_end = _as_utc(as_of or datetime.now(UTC))
    period_start = period_end - timedelta(days=days)
    latest_run = session.scalar(
        select(OpportunityScoreRun)
        .where(
            OpportunityScoreRun.status == "succeeded",
            OpportunityScoreRun.as_of <= period_end,
        )
        .order_by(OpportunityScoreRun.as_of.desc())
        .limit(1)
    )
    top_opportunities: list[ReportOpportunity] = []
    if latest_run is not None:
        rows = session.execute(
            select(OpportunityScoreSnapshot, OpportunityVersion.title)
            .join(
                OpportunityVersion,
                OpportunityVersion.id
                == OpportunityScoreSnapshot.opportunity_version_id,
            )
            .where(
                OpportunityScoreSnapshot.run_id == latest_run.id,
                OpportunityScoreSnapshot.status == "rankable",
                OpportunityScoreSnapshot.total_score.is_not(None),
            )
            .order_by(
                OpportunityScoreSnapshot.total_score.desc().nullslast(),
                OpportunityScoreSnapshot.confidence_score.desc(),
            )
            .limit(10)
        )
        top_opportunities = [
            ReportOpportunity(
                opportunity_version_id=snapshot.opportunity_version_id,
                title=title,
                total_score=snapshot.total_score,
                potential_score=snapshot.potential_score,
                actionability_score=snapshot.actionability_score,
                confidence_score=snapshot.confidence_score,
                uncertainty=snapshot.uncertainty,
                status=snapshot.status,
            )
            for snapshot, title in rows
        ]

    alerts = list(
        session.scalars(
            select(OperationalAlert).where(OperationalAlert.status == "open")
        )
    )
    cost_rows = session.execute(
        select(CostEntry.currency, func.sum(CostEntry.amount))
        .where(
            CostEntry.occurred_at >= period_start,
            CostEntry.occurred_at <= period_end,
        )
        .group_by(CostEntry.currency)
    )
    costs = {
        currency: Decimal(amount).quantize(Decimal("0.000001"))
        for currency, amount in cost_rows
    }
    new_opportunities = session.scalar(
        select(func.count())
        .select_from(Opportunity)
        .where(
            Opportunity.created_at >= period_start,
            Opportunity.created_at <= period_end,
        )
    )
    new_clusters = session.scalar(
        select(func.count())
        .select_from(ProblemCluster)
        .where(
            ProblemCluster.created_at >= period_start,
            ProblemCluster.created_at <= period_end,
        )
    )
    verified_outcomes = session.scalar(
        select(func.count())
        .select_from(CommercialOutcome)
        .where(
            CommercialOutcome.verification_status == "verified",
            CommercialOutcome.occurred_at >= period_start,
            CommercialOutcome.occurred_at <= period_end,
        )
    )
    return ResearchReportResponse(
        period=period,
        period_start=period_start,
        period_end=period_end,
        new_opportunity_count=int(new_opportunities or 0),
        new_problem_cluster_count=int(new_clusters or 0),
        latest_score_run_id=latest_run.id if latest_run else None,
        rankable_count=latest_run.rankable_count if latest_run else 0,
        verified_commercial_outcome_count=int(verified_outcomes or 0),
        open_alert_count=len(alerts),
        critical_alert_count=sum(a.severity == "critical" for a in alerts),
        cost_by_currency=costs,
        top_opportunities=top_opportunities,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
