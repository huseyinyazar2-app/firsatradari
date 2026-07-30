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
from firsat_radari.db.models import (
    BacktestPrediction,
    BacktestRun,
    Opportunity,
    OpportunityEligibilityDecision,
    OpportunityEligibilityRun,
    OpportunityRankingEntry,
    OpportunityRankingRun,
    OpportunityReview,
    OpportunityScoreRun,
    OpportunityScoreSnapshot,
    OpportunityVersion,
)
from firsat_radari.opportunities.eligibility import (
    OpportunityEligibilityError,
    OpportunityEligibilityService,
)
from firsat_radari.opportunities.materialization import (
    GroundedOpportunityInput,
    OpportunityMaterializationError,
    OpportunityMaterializationService,
)
from firsat_radari.opportunities.scoring import (
    OpportunityScoringError,
    OpportunityScoringService,
)

router = APIRouter(tags=["opportunities"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartOpportunityEligibilityRequest(BaseModel):
    clustering_run_id: uuid.UUID


class OpportunityEligibilityRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clustering_run_id: uuid.UUID
    gate_version: str
    input_fingerprint: str
    status: str
    evaluated_cluster_count: int
    eligible_cluster_count: int
    excluded_cluster_count: int
    started_at: datetime
    finished_at: datetime | None


class OpportunityEligibilityDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    cluster_id: uuid.UUID
    eligible: bool
    evidence_level: str
    blocker_codes: list[str]
    details: dict
    decided_at: datetime


class MaterializeOpportunityRequest(BaseModel):
    eligibility_decision_id: uuid.UUID
    component_claim_ids: dict[str, uuid.UUID]
    created_by: str = Field(min_length=1, max_length=200)


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    origin_cluster_id: uuid.UUID
    status: str
    created_at: datetime


class OpportunityVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_id: uuid.UUID
    eligibility_decision_id: uuid.UUID
    supersedes_version_id: uuid.UUID | None
    version_number: int
    ontology_schema_version: str
    title: str
    ontology: dict
    status: str
    evidence_level: str
    is_current: bool
    created_by: str
    created_at: datetime


class StartOpportunityScoreRunRequest(BaseModel):
    as_of: datetime
    research_profile_id: uuid.UUID


class OpportunityScoreRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    research_profile_id: uuid.UUID | None
    as_of: datetime
    input_fingerprint: str
    status: str
    opportunity_count: int
    rankable_count: int
    excluded_count: int
    started_at: datetime
    finished_at: datetime | None


class OpportunityScoreSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    opportunity_version_id: uuid.UUID
    potential_score: Decimal
    actionability_score: Decimal
    confidence_score: Decimal
    uncertainty: Decimal
    total_score: Decimal | None
    status: str
    components: dict
    created_at: datetime


class OpportunityScoreHistoryResponse(BaseModel):
    run_id: uuid.UUID
    as_of: datetime
    profile_id: uuid.UUID
    potential_score: Decimal
    actionability_score: Decimal
    confidence_score: Decimal
    uncertainty: Decimal
    total_score: Decimal | None
    status: str
    components: dict


class OpportunityRankingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    score_run_id: uuid.UUID
    status: str
    candidate_count: int
    ranked_count: int
    excluded_count: int
    created_at: datetime


class OpportunityRankingEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ranking_run_id: uuid.UUID
    score_snapshot_id: uuid.UUID
    rank: int | None
    eligible: bool
    exclusion_reasons: list[str]
    created_at: datetime


class StartBacktestRequest(BaseModel):
    score_run_id: uuid.UUID
    outcome_window_days: int = Field(ge=1, le=730)


class BacktestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    score_run_id: uuid.UUID
    cutoff_at: datetime
    outcome_window_days: int
    status: str
    prediction_count: int
    evaluated_count: int
    positive_count: int
    brier_score: Decimal | None
    baseline_brier_score: Decimal | None
    improvement: Decimal | None
    started_at: datetime
    finished_at: datetime | None


class BacktestPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    backtest_run_id: uuid.UUID
    score_snapshot_id: uuid.UUID
    predicted_probability: Decimal | None
    outcome_observed: bool | None
    outcome_count: int
    evaluation_status: str
    created_at: datetime


class CreateOpportunityReviewRequest(BaseModel):
    decision: str
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=5_000)


class OpportunityReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_version_id: uuid.UUID
    decision: str
    reviewer: str
    notes: str
    created_at: datetime


@router.post(
    "/opportunity-eligibility-runs",
    response_model=OpportunityEligibilityRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity_eligibility_run(
    request: StartOpportunityEligibilityRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityEligibilityRun:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = OpportunityEligibilityService(session).evaluate(
            request.clustering_run_id
        )
    except OpportunityEligibilityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(OpportunityEligibilityRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Opportunity eligibility run could not be loaded",
        )
    return run


@router.get(
    "/opportunity-eligibility-runs",
    response_model=list[OpportunityEligibilityRunResponse],
)
def list_opportunity_eligibility_runs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OpportunityEligibilityRun]:
    return list(
        session.scalars(
            select(OpportunityEligibilityRun)
            .order_by(OpportunityEligibilityRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/opportunity-eligibility-runs/{run_id}/decisions",
    response_model=list[OpportunityEligibilityDecisionResponse],
)
def list_opportunity_eligibility_decisions(
    run_id: uuid.UUID,
    session: DatabaseSession,
    eligible: bool | None = None,
) -> list[OpportunityEligibilityDecision]:
    if session.get(OpportunityEligibilityRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity eligibility run not found",
        )
    statement = (
        select(OpportunityEligibilityDecision)
        .where(OpportunityEligibilityDecision.run_id == run_id)
        .order_by(
            OpportunityEligibilityDecision.eligible.desc(),
            OpportunityEligibilityDecision.cluster_id,
        )
    )
    if eligible is not None:
        statement = statement.where(
            OpportunityEligibilityDecision.eligible == eligible
        )
    return list(session.scalars(statement))


@router.post(
    "/opportunity-versions",
    response_model=OpportunityVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def materialize_opportunity_version(
    request: MaterializeOpportunityRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityVersion:
    if not settings.opportunity_materialization_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Opportunity materialization API is disabled",
        )
    try:
        outcome = OpportunityMaterializationService(session).materialize(
            GroundedOpportunityInput(
                eligibility_decision_id=request.eligibility_decision_id,
                component_claim_ids=request.component_claim_ids,
                created_by=request.created_by,
            )
        )
    except OpportunityMaterializationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    version = session.get(OpportunityVersion, outcome.version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Opportunity version could not be loaded",
        )
    return version


@router.get(
    "/opportunity-versions",
    response_model=list[OpportunityVersionResponse],
)
def list_all_opportunity_versions(
    session: DatabaseSession,
    current_only: bool = True,
    limit: Annotated[int, Query(ge=1, le=1_000)] = 500,
) -> list[OpportunityVersion]:
    statement = (
        select(OpportunityVersion)
        .order_by(
            OpportunityVersion.created_at.desc(),
            OpportunityVersion.id,
        )
        .limit(limit)
    )
    if current_only:
        statement = statement.where(
            OpportunityVersion.is_current.is_(True)
        )
    return list(session.scalars(statement))


@router.get(
    "/opportunities",
    response_model=list[OpportunityResponse],
)
def list_opportunities(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Opportunity]:
    return list(
        session.scalars(
            select(Opportunity)
            .order_by(Opportunity.created_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/opportunities/{opportunity_id}/versions",
    response_model=list[OpportunityVersionResponse],
)
def list_opportunity_versions(
    opportunity_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityVersion]:
    if session.get(Opportunity, opportunity_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return list(
        session.scalars(
            select(OpportunityVersion)
            .where(OpportunityVersion.opportunity_id == opportunity_id)
            .order_by(OpportunityVersion.version_number.desc())
        )
    )


@router.post(
    "/opportunity-versions/{version_id}/reviews",
    response_model=OpportunityReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity_review(
    version_id: uuid.UUID,
    request: CreateOpportunityReviewRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityReview:
    if not settings.research_review_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research review API is disabled",
        )
    if session.get(OpportunityVersion, version_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity version not found",
        )
    if request.decision not in {
        "investigate",
        "validate",
        "watch",
        "reject",
        "archive",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported opportunity review decision",
        )
    review = OpportunityReview(
        opportunity_version_id=version_id,
        decision=request.decision,
        reviewer=request.reviewer.strip(),
        notes=request.notes.strip(),
        created_at=datetime.now(UTC),
    )
    session.add(review)
    session.commit()
    return review


@router.get(
    "/opportunity-versions/{version_id}/reviews",
    response_model=list[OpportunityReviewResponse],
)
def list_opportunity_reviews(
    version_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityReview]:
    if session.get(OpportunityVersion, version_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity version not found",
        )
    return list(
        session.scalars(
            select(OpportunityReview)
            .where(OpportunityReview.opportunity_version_id == version_id)
            .order_by(OpportunityReview.created_at.desc())
        )
    )


@router.post(
    "/opportunity-score-runs",
    response_model=OpportunityScoreRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity_score_run(
    request: StartOpportunityScoreRunRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityScoreRun:
    _ensure_scoring_enabled(settings)
    try:
        outcome = OpportunityScoringService(session).score(
            as_of=request.as_of,
            research_profile_id=request.research_profile_id,
        )
    except OpportunityScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(OpportunityScoreRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Opportunity score run could not be loaded",
        )
    return run


@router.get(
    "/opportunity-versions/{version_id}/score-history",
    response_model=list[OpportunityScoreHistoryResponse],
)
def list_opportunity_score_history(
    version_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityScoreHistoryResponse]:
    if session.get(OpportunityVersion, version_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity version not found",
        )
    rows = session.execute(
        select(OpportunityScoreSnapshot, OpportunityScoreRun)
        .join(
            OpportunityScoreRun,
            OpportunityScoreRun.id == OpportunityScoreSnapshot.run_id,
        )
        .where(
            OpportunityScoreSnapshot.opportunity_version_id == version_id
        )
        .order_by(OpportunityScoreRun.as_of.desc())
    )
    return [
        OpportunityScoreHistoryResponse(
            run_id=run.id,
            as_of=run.as_of,
            profile_id=run.profile_id,
            potential_score=snapshot.potential_score,
            actionability_score=snapshot.actionability_score,
            confidence_score=snapshot.confidence_score,
            uncertainty=snapshot.uncertainty,
            total_score=snapshot.total_score,
            status=snapshot.status,
            components=snapshot.components,
        )
        for snapshot, run in rows
    ]


@router.get(
    "/opportunity-score-runs",
    response_model=list[OpportunityScoreRunResponse],
)
def list_opportunity_score_runs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OpportunityScoreRun]:
    return list(
        session.scalars(
            select(OpportunityScoreRun)
            .order_by(OpportunityScoreRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/opportunity-score-runs/{run_id}/snapshots",
    response_model=list[OpportunityScoreSnapshotResponse],
)
def list_opportunity_score_snapshots(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityScoreSnapshot]:
    if session.get(OpportunityScoreRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity score run not found",
        )
    return list(
        session.scalars(
            select(OpportunityScoreSnapshot)
            .where(OpportunityScoreSnapshot.run_id == run_id)
            .order_by(
                OpportunityScoreSnapshot.total_score.desc().nullslast(),
                OpportunityScoreSnapshot.opportunity_version_id,
            )
        )
    )


@router.post(
    "/opportunity-score-runs/{run_id}/ranking",
    response_model=OpportunityRankingRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity_ranking(
    run_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityRankingRun:
    _ensure_scoring_enabled(settings)
    try:
        outcome = OpportunityScoringService(session).rank(run_id)
    except OpportunityScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    ranking = session.get(OpportunityRankingRun, outcome.ranking_run_id)
    if ranking is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Opportunity ranking could not be loaded",
        )
    return ranking


@router.get(
    "/opportunity-ranking-runs/{run_id}/entries",
    response_model=list[OpportunityRankingEntryResponse],
)
def list_opportunity_ranking_entries(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityRankingEntry]:
    if session.get(OpportunityRankingRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity ranking run not found",
        )
    return list(
        session.scalars(
            select(OpportunityRankingEntry)
            .where(OpportunityRankingEntry.ranking_run_id == run_id)
            .order_by(
                OpportunityRankingEntry.rank.asc().nullslast(),
                OpportunityRankingEntry.id,
            )
        )
    )


@router.post(
    "/backtest-runs",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_backtest_run(
    request: StartBacktestRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> BacktestRun:
    _ensure_scoring_enabled(settings)
    try:
        outcome = OpportunityScoringService(session).backtest(
            request.score_run_id,
            outcome_window_days=request.outcome_window_days,
        )
    except OpportunityScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(BacktestRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backtest run could not be loaded",
        )
    return run


@router.get(
    "/backtest-runs",
    response_model=list[BacktestRunResponse],
)
def list_backtest_runs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[BacktestRun]:
    return list(
        session.scalars(
            select(BacktestRun)
            .order_by(BacktestRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/backtest-runs/{run_id}/predictions",
    response_model=list[BacktestPredictionResponse],
)
def list_backtest_predictions(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[BacktestPrediction]:
    if session.get(BacktestRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest run not found",
        )
    return list(
        session.scalars(
            select(BacktestPrediction)
            .where(BacktestPrediction.backtest_run_id == run_id)
            .order_by(BacktestPrediction.id)
        )
    )


def _ensure_scoring_enabled(settings: Settings) -> None:
    if not settings.scoring_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Opportunity scoring API is disabled",
        )
