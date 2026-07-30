import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import OpportunityExport, OpportunityResearchRun
from firsat_radari.research.service import (
    ExportRequest,
    OpportunityResearchService,
    ResearchError,
    ResearchRequest,
)

router = APIRouter(tags=["research"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class CreateResearchRunRequest(BaseModel):
    research_tier: str = "evidence_review"
    focus_questions: list[str] = Field(default_factory=list, max_length=20)
    requested_by: str = Field(min_length=1, max_length=200)


class ResearchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_version_id: uuid.UUID
    research_tier: str
    focus_questions: list[str]
    input_fingerprint: str
    status: str
    evidence_snapshot: dict
    findings: dict
    blockers: list[str]
    requested_by: str
    started_at: datetime
    finished_at: datetime | None


class PrepareExportRequest(BaseModel):
    opportunity_version_id: uuid.UUID
    research_run_id: uuid.UUID
    destination: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=3, max_length=120)
    created_by: str = Field(min_length=1, max_length=200)


class AcknowledgeExportRequest(BaseModel):
    external_reference: str = Field(min_length=1, max_length=300)


class OpportunityExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_version_id: uuid.UUID
    research_run_id: uuid.UUID
    destination: str
    idempotency_key: str
    payload_hash: str
    payload: dict
    status: str
    created_by: str
    created_at: datetime
    exported_at: datetime | None
    external_reference: str | None


@router.post(
    "/opportunity-versions/{version_id}/research-runs",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_run(
    version_id: uuid.UUID,
    request: CreateResearchRunRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityResearchRun:
    if not settings.research_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research API is disabled",
        )
    try:
        return OpportunityResearchService(session).research(
            ResearchRequest(
                opportunity_version_id=version_id,
                research_tier=request.research_tier,
                focus_questions=tuple(request.focus_questions),
                requested_by=request.requested_by,
            )
        )
    except ResearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/opportunity-versions/{version_id}/research-runs",
    response_model=list[ResearchRunResponse],
)
def list_research_runs(
    version_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[OpportunityResearchRun]:
    return list(
        session.scalars(
            select(OpportunityResearchRun)
            .where(
                OpportunityResearchRun.opportunity_version_id == version_id
            )
            .order_by(OpportunityResearchRun.started_at.desc())
            .limit(limit)
        )
    )


@router.post(
    "/opportunity-exports",
    response_model=OpportunityExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def prepare_opportunity_export(
    request: PrepareExportRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityExport:
    if not settings.sales_export_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sales export API is disabled",
        )
    try:
        return OpportunityResearchService(session).prepare_export(
            ExportRequest(**request.model_dump())
        )
    except ResearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/opportunity-exports",
    response_model=list[OpportunityExportResponse],
)
def list_opportunity_exports(
    session: DatabaseSession,
    opportunity_version_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OpportunityExport]:
    statement = (
        select(OpportunityExport)
        .order_by(OpportunityExport.created_at.desc())
        .limit(limit)
    )
    if opportunity_version_id is not None:
        statement = statement.where(
            OpportunityExport.opportunity_version_id
            == opportunity_version_id
        )
    return list(session.scalars(statement))


@router.patch(
    "/opportunity-exports/{export_id}/acknowledge",
    response_model=OpportunityExportResponse,
)
def acknowledge_opportunity_export(
    export_id: uuid.UUID,
    request: AcknowledgeExportRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> OpportunityExport:
    if not settings.sales_export_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sales export API is disabled",
        )
    try:
        return OpportunityResearchService(session).acknowledge_export(
            export_id,
            request.external_reference,
        )
    except ResearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
