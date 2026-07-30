import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import ProblemEvidence, ProblemExtractionRun
from firsat_radari.problem_mining.github import (
    GitHubProblemEvidenceExtractor,
    ProblemExtractionError,
)
from firsat_radari.problem_mining.stack_exchange import (
    StackExchangeProblemEvidenceExtractor,
)

router = APIRouter(tags=["problem-evidence"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartProblemExtractionRequest(BaseModel):
    source_key: str = Field(default="github", min_length=2, max_length=80)
    limit: int | None = Field(default=None, ge=1)


class ProblemExtractionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    extractor_key: str
    extractor_version: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    input_count: int
    success_count: int
    error_count: int
    evidence_count: int


class ProblemEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_record_id: uuid.UUID
    document_id: uuid.UUID
    entity_id: uuid.UUID
    evidence_type: str
    rule_key: str
    source_field: str
    char_start: int | None
    char_end: int | None
    excerpt: str
    confidence: Decimal
    attributes: dict[str, Any]
    policy_version: str
    retention_until: datetime | None
    created_at: datetime


@router.post(
    "/problem-extraction-runs",
    response_model=ProblemExtractionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_problem_extraction(
    request: StartProblemExtractionRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemExtractionRun:
    if not settings.problem_extraction_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Problem extraction API is disabled",
        )
    limit = request.limit or settings.problem_extraction_api_max_items
    if limit > settings.problem_extraction_api_max_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"limit cannot exceed {settings.problem_extraction_api_max_items}"
            ),
        )
    try:
        if request.source_key == "github":
            extractor = GitHubProblemEvidenceExtractor(session)
        elif request.source_key == "stack_exchange":
            extractor = StackExchangeProblemEvidenceExtractor(session)
        else:
            raise ProblemExtractionError(
                f"Unsupported problem extraction source: {request.source_key}"
            )
        outcome = extractor.extract_pending(limit=limit)
    except ProblemExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(ProblemExtractionRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Problem extraction run could not be loaded",
        )
    return run


@router.get(
    "/problem-extraction-runs",
    response_model=list[ProblemExtractionRunResponse],
)
def list_problem_extraction_runs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProblemExtractionRun]:
    return list(
        session.scalars(
            select(ProblemExtractionRun)
            .order_by(ProblemExtractionRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/problem-extraction-runs/{run_id}",
    response_model=ProblemExtractionRunResponse,
)
def get_problem_extraction_run(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> ProblemExtractionRun:
    run = session.get(ProblemExtractionRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem extraction run not found",
        )
    return run


@router.get("/problem-evidence", response_model=list[ProblemEvidenceResponse])
def list_problem_evidence(
    session: DatabaseSession,
    entity_id: uuid.UUID | None = None,
    evidence_type: str | None = None,
    minimum_confidence: Annotated[Decimal | None, Query(ge=0, le=1)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ProblemEvidence]:
    statement = (
        select(ProblemEvidence)
        .where(
            or_(
                ProblemEvidence.retention_until.is_(None),
                ProblemEvidence.retention_until >= datetime.now(UTC),
            )
        )
        .order_by(ProblemEvidence.created_at.desc(), ProblemEvidence.id)
        .limit(limit)
    )
    if entity_id is not None:
        statement = statement.where(ProblemEvidence.entity_id == entity_id)
    if evidence_type is not None:
        statement = statement.where(
            ProblemEvidence.evidence_type == evidence_type
        )
    if minimum_confidence is not None:
        statement = statement.where(
            ProblemEvidence.confidence >= minimum_confidence
        )
    return list(session.scalars(statement))
