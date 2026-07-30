import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.connectors.registry import (
    ConnectorRegistryError,
    create_connector,
    validate_discovery_checkpoint,
    validate_discovery_query,
)
from firsat_radari.db.models import DataQualityEvent, DataSource, IngestionRun
from firsat_radari.ingestion.errors import SourcePolicyError
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.storage.filesystem import FileObjectStore

router = APIRouter(prefix="/ingestion-runs", tags=["ingestion"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartIngestionRequest(BaseModel):
    source_key: str = Field(min_length=2, max_length=80)
    connector_key: str | None = Field(default=None, min_length=2, max_length=80)
    query: dict[str, Any]
    checkpoint: dict[str, Any] | None = None
    resume: bool = True
    max_pages: int | None = Field(default=None, ge=1)


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    collection_id: uuid.UUID | None
    connector_version: str
    job_type: str
    query_definition: dict[str, Any]
    query_fingerprint: str | None
    status: str
    checkpoint_before: dict[str, Any] | None
    checkpoint_after: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    request_count: int
    response_count: int
    raw_item_count: int
    normalized_item_count: int
    duplicate_item_count: int
    error_count: int
    estimated_cost: Decimal


class DataQualityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    severity: str
    external_type: str | None
    external_id: str | None
    details: dict[str, Any]
    observed_at: datetime
    resolved_at: datetime | None


@router.post("", response_model=IngestionRunResponse, status_code=status.HTTP_201_CREATED)
async def start_ingestion(
    request: StartIngestionRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> IngestionRun:
    if not settings.ingestion_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion API is disabled",
        )

    max_pages = request.max_pages or settings.ingestion_api_max_pages
    if max_pages > settings.ingestion_api_max_pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"max_pages cannot exceed {settings.ingestion_api_max_pages}",
        )

    try:
        connector_key = request.connector_key or request.source_key
        query = validate_discovery_query(connector_key, request.query)
        checkpoint = validate_discovery_checkpoint(
            connector_key,
            request.checkpoint,
        )
        connector = create_connector(connector_key, settings)
        if connector.source_key != request.source_key:
            raise ConnectorRegistryError("Connector does not belong to requested source")
    except ConnectorRegistryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    try:
        outcome = await IngestionService(
            session,
            FileObjectStore(settings.raw_storage_path),
        ).discover(
            connector,
            query,
            checkpoint=checkpoint,
            resume=request.resume,
            max_pages=max_pages,
        )
    except SourcePolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    finally:
        close = getattr(connector, "aclose", None)
        if close is not None:
            await close()

    run = session.get(IngestionRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion run could not be loaded",
        )
    return run


@router.get("", response_model=list[IngestionRunResponse])
def list_ingestion_runs(
    session: DatabaseSession,
    source_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[IngestionRun]:
    statement = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    if source_key is not None:
        statement = statement.join(DataSource).where(DataSource.key == source_key)
    return list(session.scalars(statement))


@router.get("/{run_id}", response_model=IngestionRunResponse)
def get_ingestion_run(run_id: uuid.UUID, session: DatabaseSession) -> IngestionRun:
    run = session.get(IngestionRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion run not found",
        )
    return run


@router.get(
    "/{run_id}/quality-events",
    response_model=list[DataQualityEventResponse],
)
def list_run_quality_events(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[DataQualityEvent]:
    if session.get(IngestionRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion run not found",
        )
    return list(
        session.scalars(
            select(DataQualityEvent)
            .where(DataQualityEvent.run_id == run_id)
            .order_by(DataQualityEvent.observed_at)
        )
    )
