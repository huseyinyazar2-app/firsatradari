import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import DataSource, NormalizationRun
from firsat_radari.normalization.registry import (
    NormalizerRegistryError,
    create_normalizer,
)
from firsat_radari.normalization.service import (
    NormalizationPolicyError,
    NormalizationService,
)
from firsat_radari.storage.filesystem import FileObjectStore

router = APIRouter(prefix="/normalization-runs", tags=["normalization"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartNormalizationRequest(BaseModel):
    source_key: str = Field(min_length=2, max_length=80)
    normalizer_key: str | None = Field(default=None, min_length=2, max_length=80)
    limit: int | None = Field(default=None, ge=1)


class NormalizationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    normalizer_key: str
    normalizer_version: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    input_count: int
    success_count: int
    error_count: int


@router.post(
    "",
    response_model=NormalizationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_normalization(
    request: StartNormalizationRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> NormalizationRun:
    if not settings.normalization_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Normalization API is disabled",
        )
    limit = request.limit or settings.normalization_api_max_items
    if limit > settings.normalization_api_max_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(f"limit cannot exceed {settings.normalization_api_max_items}"),
        )
    try:
        normalizer_key = request.normalizer_key or request.source_key
        normalizer = create_normalizer(normalizer_key)
        if normalizer.source_key != request.source_key:
            raise NormalizerRegistryError("Normalizer does not belong to requested source")
    except NormalizerRegistryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    try:
        outcome = NormalizationService(
            session,
            FileObjectStore(settings.raw_storage_path),
        ).normalize_pending(normalizer, limit=limit)
    except NormalizationPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    run = session.get(NormalizationRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Normalization run could not be loaded",
        )
    return run


@router.get("", response_model=list[NormalizationRunResponse])
def list_normalization_runs(
    session: DatabaseSession,
    source_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NormalizationRun]:
    statement = select(NormalizationRun).order_by(NormalizationRun.started_at.desc()).limit(limit)
    if source_key is not None:
        statement = statement.join(DataSource).where(DataSource.key == source_key)
    return list(session.scalars(statement))


@router.get("/{run_id}", response_model=NormalizationRunResponse)
def get_normalization_run(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> NormalizationRun:
    run = session.get(NormalizationRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Normalization run not found",
        )
    return run
