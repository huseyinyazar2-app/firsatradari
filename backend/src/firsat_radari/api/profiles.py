import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    OpportunityProfileEvaluation,
    ResearchProfile,
    VerticalDefinition,
)
from firsat_radari.profiles.service import (
    ProfileError,
    ProfileEvaluationInput,
    ProfileInput,
    ResearchProfileService,
    VerticalInput,
)

router = APIRouter(tags=["profiles"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class CreateVerticalRequest(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    status: str = "draft"
    config: dict = Field(default_factory=dict)
    selection_rationale: str = Field(min_length=1, max_length=4_000)
    created_by: str = Field(min_length=1, max_length=200)


class VerticalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    version: str
    name: str
    status: str
    config: dict
    selection_rationale: str
    is_current: bool
    created_by: str
    created_at: datetime


class CreateResearchProfileRequest(BaseModel):
    vertical_definition_id: uuid.UUID
    key: str = Field(min_length=2, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    status: str = "draft"
    constraints: dict = Field(default_factory=dict)
    exclusions: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)
    created_by: str = Field(min_length=1, max_length=200)


class ResearchProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vertical_definition_id: uuid.UUID
    key: str
    version: str
    name: str
    status: str
    constraints: dict
    exclusions: dict
    preferences: dict
    is_current: bool
    created_by: str
    created_at: datetime


class EvaluateProfileRequest(BaseModel):
    research_profile_id: uuid.UUID
    observed_attributes: dict = Field(default_factory=dict)
    evaluated_by: str = Field(min_length=1, max_length=200)


class ProfileEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_version_id: uuid.UUID
    research_profile_id: uuid.UUID
    input_fingerprint: str
    observed_attributes: dict
    eligible: bool
    blocker_codes: list[str]
    unknown_fields: list[str]
    fit_score: Decimal | None
    data_coverage: Decimal
    components: dict
    evaluated_by: str
    evaluated_at: datetime


@router.post(
    "/verticals",
    response_model=VerticalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vertical(
    request: CreateVerticalRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> VerticalDefinition:
    _ensure_enabled(settings)
    try:
        return ResearchProfileService(session).create_vertical(
            VerticalInput(**request.model_dump())
        )
    except ProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/verticals", response_model=list[VerticalResponse])
def list_verticals(
    session: DatabaseSession,
    current_only: bool = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[VerticalDefinition]:
    statement = (
        select(VerticalDefinition)
        .order_by(
            VerticalDefinition.key,
            VerticalDefinition.created_at.desc(),
        )
        .limit(limit)
    )
    if current_only:
        statement = statement.where(VerticalDefinition.is_current.is_(True))
    return list(session.scalars(statement))


@router.post(
    "/research-profiles",
    response_model=ResearchProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_profile(
    request: CreateResearchProfileRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ResearchProfile:
    _ensure_enabled(settings)
    try:
        return ResearchProfileService(session).create_profile(
            ProfileInput(**request.model_dump())
        )
    except ProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/research-profiles",
    response_model=list[ResearchProfileResponse],
)
def list_research_profiles(
    session: DatabaseSession,
    current_only: bool = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ResearchProfile]:
    statement = (
        select(ResearchProfile)
        .order_by(ResearchProfile.key, ResearchProfile.created_at.desc())
        .limit(limit)
    )
    if current_only:
        statement = statement.where(ResearchProfile.is_current.is_(True))
    return list(session.scalars(statement))


@router.post(
    "/opportunity-versions/{version_id}/profile-evaluations",
    response_model=ProfileEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_opportunity_profile(
    version_id: uuid.UUID,
    request: EvaluateProfileRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityProfileEvaluation:
    _ensure_enabled(settings)
    try:
        return ResearchProfileService(session).evaluate(
            ProfileEvaluationInput(
                opportunity_version_id=version_id,
                research_profile_id=request.research_profile_id,
                observed_attributes=request.observed_attributes,
                evaluated_by=request.evaluated_by,
            )
        )
    except ProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/opportunity-versions/{version_id}/profile-evaluations",
    response_model=list[ProfileEvaluationResponse],
)
def list_profile_evaluations(
    version_id: uuid.UUID,
    session: DatabaseSession,
) -> list[OpportunityProfileEvaluation]:
    return list(
        session.scalars(
            select(OpportunityProfileEvaluation)
            .where(
                OpportunityProfileEvaluation.opportunity_version_id
                == version_id
            )
            .order_by(OpportunityProfileEvaluation.evaluated_at.desc())
        )
    )


def _ensure_enabled(settings: Settings) -> None:
    if not settings.research_settings_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research settings API is disabled",
        )
