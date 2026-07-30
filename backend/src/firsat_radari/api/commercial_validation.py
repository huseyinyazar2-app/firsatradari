import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.commercial_validation.service import (
    CommercialValidationError,
    CommercialValidationService,
    ContactPreferenceInput,
    ExperimentInput,
    OutcomeInput,
    OutcomeReviewInput,
)
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    CommercialContactPreference,
    CommercialOutcome,
    CommercialOutcomeReview,
    CommercialValidationExperiment,
)

router = APIRouter(tags=["commercial-validation"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class CreateExperimentRequest(BaseModel):
    cluster_id: uuid.UUID
    opportunity_version_id: uuid.UUID | None = None
    external_key: str = Field(min_length=3, max_length=80)
    protocol_key: str = Field(default="default-v1", min_length=3, max_length=80)
    cohort: str = "radar"
    experiment_type: str = Field(min_length=3, max_length=40)
    target_segment: str = Field(min_length=1, max_length=2_000)
    hypothesis: str = Field(min_length=1, max_length=4_000)
    status: str = "running"
    started_at: datetime
    created_by: str = Field(min_length=1, max_length=200)


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cluster_id: uuid.UUID
    opportunity_version_id: uuid.UUID | None
    external_key: str
    protocol_key: str
    cohort: str
    experiment_type: str
    target_segment: str
    hypothesis: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_by: str
    created_at: datetime


class CreateOutcomeRequest(BaseModel):
    idempotency_key: str = Field(min_length=3, max_length=80)
    participant_key: str = Field(min_length=3, max_length=200)
    outcome_type: str = Field(min_length=3, max_length=40)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    evidence_reference: str | None = Field(default=None, max_length=800)
    notes: str | None = Field(default=None, max_length=2_000)
    occurred_at: datetime
    created_by: str = Field(min_length=1, max_length=200)


class ReviewOutcomeRequest(BaseModel):
    new_status: str
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=2_000)


class CloseExperimentRequest(BaseModel):
    status: str
    ended_at: datetime


class RecordContactPreferenceRequest(BaseModel):
    participant_key: str = Field(min_length=3, max_length=200)
    channel: str
    scope: str = Field(min_length=3, max_length=80)
    status: str
    evidence_reference: str | None = Field(default=None, max_length=800)
    recorded_by: str = Field(min_length=1, max_length=200)


class ContactPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    scope: str
    status: str
    evidence_reference: str | None
    recorded_by: str
    recorded_at: datetime


class OutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    experiment_id: uuid.UUID
    idempotency_key: str
    outcome_type: str
    direction: str
    amount: Decimal | None
    currency: str | None
    evidence_reference: str | None
    notes: str | None
    verification_status: str
    occurred_at: datetime
    created_by: str
    created_at: datetime
    verified_at: datetime | None
    verifier: str | None
    verification_notes: str | None


class OutcomeReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    outcome_id: uuid.UUID
    previous_status: str
    new_status: str
    reviewer: str
    notes: str
    reviewed_at: datetime


@router.post(
    "/commercial-validation-experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    request: CreateExperimentRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CommercialValidationExperiment:
    service = _service(session, settings)
    try:
        return service.create_experiment(
            ExperimentInput(
                cluster_id=request.cluster_id,
                opportunity_version_id=request.opportunity_version_id,
                external_key=request.external_key,
                protocol_key=request.protocol_key,
                cohort=request.cohort,
                experiment_type=request.experiment_type,
                target_segment=request.target_segment,
                hypothesis=request.hypothesis,
                status=request.status,
                started_at=request.started_at,
                created_by=request.created_by,
            )
        )
    except CommercialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/commercial-validation-experiments/{experiment_id}",
    response_model=ExperimentResponse,
)
def close_experiment(
    experiment_id: uuid.UUID,
    request: CloseExperimentRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CommercialValidationExperiment:
    service = _service(session, settings)
    try:
        return service.close_experiment(
            experiment_id,
            new_status=request.status,
            ended_at=request.ended_at,
        )
    except CommercialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/commercial-contact-preferences",
    response_model=ContactPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_contact_preference(
    request: RecordContactPreferenceRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CommercialContactPreference:
    service = _service(session, settings)
    try:
        return service.record_contact_preference(
            ContactPreferenceInput(**request.model_dump())
        )
    except CommercialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/commercial-validation-experiments",
    response_model=list[ExperimentResponse],
)
def list_experiments(
    session: DatabaseSession,
    settings: AppSettings,
    cluster_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[CommercialValidationExperiment]:
    _ensure_enabled(settings)
    statement = (
        select(CommercialValidationExperiment)
        .order_by(
            CommercialValidationExperiment.created_at.desc(),
            CommercialValidationExperiment.id,
        )
        .limit(limit)
    )
    if cluster_id is not None:
        statement = statement.where(
            CommercialValidationExperiment.cluster_id == cluster_id
        )
    return list(session.scalars(statement))


@router.post(
    "/commercial-validation-experiments/{experiment_id}/outcomes",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_outcome(
    experiment_id: uuid.UUID,
    request: CreateOutcomeRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CommercialOutcome:
    service = _service(session, settings)
    try:
        return service.add_outcome(
            OutcomeInput(
                experiment_id=experiment_id,
                idempotency_key=request.idempotency_key,
                participant_key=request.participant_key,
                outcome_type=request.outcome_type,
                amount=request.amount,
                currency=request.currency,
                evidence_reference=request.evidence_reference,
                notes=request.notes,
                occurred_at=request.occurred_at,
                created_by=request.created_by,
            )
        )
    except CommercialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/commercial-validation-experiments/{experiment_id}/outcomes",
    response_model=list[OutcomeResponse],
)
def list_outcomes(
    experiment_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
    verification_status: str | None = None,
) -> list[CommercialOutcome]:
    _ensure_enabled(settings)
    statement = (
        select(CommercialOutcome)
        .where(CommercialOutcome.experiment_id == experiment_id)
        .order_by(CommercialOutcome.occurred_at, CommercialOutcome.id)
    )
    if verification_status is not None:
        statement = statement.where(
            CommercialOutcome.verification_status == verification_status
        )
    return list(session.scalars(statement))


@router.patch(
    "/commercial-outcomes/{outcome_id}/review",
    response_model=OutcomeResponse,
)
def review_outcome(
    outcome_id: uuid.UUID,
    request: ReviewOutcomeRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> CommercialOutcome:
    service = _service(session, settings)
    try:
        return service.review_outcome(
            OutcomeReviewInput(
                outcome_id=outcome_id,
                new_status=request.new_status,
                reviewer=request.reviewer,
                notes=request.notes,
            )
        )
    except CommercialValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/commercial-outcomes/{outcome_id}/reviews",
    response_model=list[OutcomeReviewResponse],
)
def list_outcome_reviews(
    outcome_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
) -> list[CommercialOutcomeReview]:
    _ensure_enabled(settings)
    return list(
        session.scalars(
            select(CommercialOutcomeReview)
            .where(CommercialOutcomeReview.outcome_id == outcome_id)
            .order_by(
                CommercialOutcomeReview.reviewed_at,
                CommercialOutcomeReview.id,
            )
        )
    )


def _service(
    session: Session,
    settings: Settings,
) -> CommercialValidationService:
    _ensure_enabled(settings)
    if settings.validation_hash_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Validation hash secret is not configured",
        )
    return CommercialValidationService(
        session,
        settings.validation_hash_secret.get_secret_value(),
    )


def _ensure_enabled(settings: Settings) -> None:
    if not settings.commercial_validation_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Commercial validation API is disabled",
        )
