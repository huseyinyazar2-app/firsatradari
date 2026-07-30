import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    DataQualityEvent,
    DataSource,
    IngestionCollection,
    IngestionRun,
    SourceIndependenceReview,
    SourcePolicy,
    SourceRelationship,
)
from firsat_radari.source_registry.service import (
    PolicyApproval,
    SourceIndependenceDecision,
    SourceRegistryError,
    SourceRegistryService,
)

router = APIRouter(prefix="/sources", tags=["sources"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    source_type: str
    evidence_family_key: str
    independence_group_key: str
    independence_status: str
    owner: str
    base_url: str
    policy_status: str
    policy_version: str | None
    storage_permission: str
    retention_days: int | None
    enabled: bool


class SourcePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: str
    status: str
    reviewed_at: datetime
    reviewer: str
    commercial_use_status: str
    storage_permission: str
    derived_data_permission: str
    llm_processing_permission: str
    retention_days: int | None
    terms_url: str | None
    notes: str | None


class SourceHealthResponse(BaseModel):
    source_key: str
    enabled: bool
    latest_run_status: str | None
    latest_run_at: datetime | None
    last_success_at: datetime | None
    open_quality_event_count: int
    incomplete_collection_count: int


class SourceRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    related_source_id: uuid.UUID
    relationship_type: str
    scope: str
    independence_effect: str
    status: str
    rationale: str
    reviewed_at: datetime
    reviewer: str


class CreateSourceIndependenceReviewRequest(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    new_status: str
    reviewer: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=4_000)
    evidence_references: list[str] = Field(default_factory=list, max_length=20)


class ApproveSourcePolicyRequest(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    reviewer: str = Field(min_length=1, max_length=200)
    commercial_use_status: str
    storage_permission: str
    derived_data_permission: str
    llm_processing_permission: str
    retention_days: int = Field(ge=1, le=3_650)
    terms_url: str | None = Field(default=None, max_length=800)
    notes: str | None = Field(default=None, max_length=4_000)


class SetSourceEnabledRequest(BaseModel):
    enabled: bool


class SourceIndependenceReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    version: str
    previous_status: str
    new_status: str
    reviewer: str
    rationale: str
    evidence_references: list[str]
    reviewed_at: datetime


@router.get("", response_model=list[SourceResponse])
def list_sources(session: DatabaseSession) -> list[DataSource]:
    return list(session.scalars(select(DataSource).order_by(DataSource.key)))


@router.get("/{source_key}/policies", response_model=list[SourcePolicyResponse])
def list_source_policies(
    source_key: str,
    session: DatabaseSession,
) -> list[SourcePolicy]:
    source = session.scalar(select(DataSource).where(DataSource.key == source_key))
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return list(
        session.scalars(
            select(SourcePolicy)
            .where(SourcePolicy.source_id == source.id)
            .order_by(SourcePolicy.reviewed_at.desc())
        )
    )


@router.post(
    "/{source_key}/policies",
    response_model=SourcePolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def approve_source_policy(
    source_key: str,
    request: ApproveSourcePolicyRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> SourcePolicy:
    _ensure_governance_enabled(settings)
    try:
        return SourceRegistryService(session).approve_policy(
            source_key,
            PolicyApproval(**request.model_dump()),
        )
    except SourceRegistryError as exc:
        raise _source_registry_http_error(exc) from exc


@router.patch(
    "/{source_key}/enabled",
    response_model=SourceResponse,
)
def set_source_enabled(
    source_key: str,
    request: SetSourceEnabledRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> DataSource:
    _ensure_governance_enabled(settings)
    try:
        return SourceRegistryService(session).set_enabled(
            source_key,
            enabled=request.enabled,
        )
    except SourceRegistryError as exc:
        raise _source_registry_http_error(exc) from exc


@router.get(
    "/{source_key}/independence-reviews",
    response_model=list[SourceIndependenceReviewResponse],
)
def list_source_independence_reviews(
    source_key: str,
    session: DatabaseSession,
) -> list[SourceIndependenceReview]:
    source = session.scalar(
        select(DataSource).where(DataSource.key == source_key)
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return list(
        session.scalars(
            select(SourceIndependenceReview)
            .where(SourceIndependenceReview.source_id == source.id)
            .order_by(SourceIndependenceReview.reviewed_at.desc())
        )
    )


@router.post(
    "/{source_key}/independence-reviews",
    response_model=SourceIndependenceReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source_independence_review(
    source_key: str,
    request: CreateSourceIndependenceReviewRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> SourceIndependenceReview:
    _ensure_governance_enabled(settings)
    try:
        return SourceRegistryService(session).review_independence(
            source_key,
            SourceIndependenceDecision(
                version=request.version,
                new_status=request.new_status,
                reviewer=request.reviewer,
                rationale=request.rationale,
                evidence_references=tuple(request.evidence_references),
            ),
        )
    except SourceRegistryError as exc:
        raise _source_registry_http_error(exc) from exc


@router.get(
    "/{source_key}/relationships",
    response_model=list[SourceRelationshipResponse],
)
def list_source_relationships(
    source_key: str,
    session: DatabaseSession,
) -> list[SourceRelationship]:
    source = session.scalar(
        select(DataSource).where(DataSource.key == source_key)
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return list(
        session.scalars(
            select(SourceRelationship)
            .where(
                or_(
                    SourceRelationship.source_id == source.id,
                    SourceRelationship.related_source_id == source.id,
                )
            )
            .order_by(SourceRelationship.reviewed_at.desc())
        )
    )


@router.get("/{source_key}/health", response_model=SourceHealthResponse)
def get_source_health(
    source_key: str,
    session: DatabaseSession,
) -> SourceHealthResponse:
    source = session.scalar(select(DataSource).where(DataSource.key == source_key))
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    latest_run = session.scalar(
        select(IngestionRun)
        .where(IngestionRun.source_id == source.id)
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    )
    last_success_at = session.scalar(
        select(func.max(IngestionRun.finished_at)).where(
            IngestionRun.source_id == source.id,
            IngestionRun.status == "succeeded",
        )
    )
    open_quality_event_count = session.scalar(
        select(func.count())
        .select_from(DataQualityEvent)
        .where(
            DataQualityEvent.source_id == source.id,
            DataQualityEvent.resolved_at.is_(None),
        )
    )
    incomplete_collection_count = session.scalar(
        select(func.count())
        .select_from(IngestionCollection)
        .where(
            IngestionCollection.source_id == source.id,
            IngestionCollection.is_complete.is_(False),
        )
    )
    return SourceHealthResponse(
        source_key=source.key,
        enabled=source.enabled,
        latest_run_status=latest_run.status if latest_run else None,
        latest_run_at=latest_run.started_at if latest_run else None,
        last_success_at=last_success_at,
        open_quality_event_count=open_quality_event_count or 0,
        incomplete_collection_count=incomplete_collection_count or 0,
    )


def _ensure_governance_enabled(settings: Settings) -> None:
    if not settings.source_governance_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Source governance API is disabled",
        )


def _source_registry_http_error(exc: SourceRegistryError) -> HTTPException:
    detail = str(exc)
    return HTTPException(
        status_code=(
            status.HTTP_404_NOT_FOUND
            if detail.startswith("Source not found")
            else status.HTTP_409_CONFLICT
        ),
        detail=detail,
    )
