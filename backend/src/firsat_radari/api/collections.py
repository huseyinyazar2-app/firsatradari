import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.db.models import CollectionPage, DataSource, IngestionCollection

router = APIRouter(prefix="/collections", tags=["ingestion"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    job_type: str
    query_fingerprint: str
    query_definition: dict[str, Any]
    status: str
    started_at: datetime
    completed_at: datetime | None
    expected_total: int | None
    collected_total: int
    page_count: int
    is_complete: bool
    resume_available: bool
    completeness_reason: str | None


class CollectionPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    page_number: int
    status: str
    cursor_in: dict[str, Any] | None
    cursor_out: dict[str, Any] | None
    items_returned: int
    is_last_page: bool
    is_complete: bool
    resume_available: bool
    completeness_reason: str | None
    expected_total: int | None
    collected_total: int
    observed_at: datetime


@router.get("", response_model=list[CollectionResponse])
def list_collections(
    session: DatabaseSession,
    source_key: str | None = None,
    complete: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[IngestionCollection]:
    statement = (
        select(IngestionCollection).order_by(IngestionCollection.started_at.desc()).limit(limit)
    )
    if source_key is not None:
        statement = statement.join(DataSource).where(DataSource.key == source_key)
    if complete is not None:
        statement = statement.where(IngestionCollection.is_complete == complete)
    return list(session.scalars(statement))


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: uuid.UUID,
    session: DatabaseSession,
) -> IngestionCollection:
    collection = session.get(IngestionCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return collection


@router.get(
    "/{collection_id}/pages",
    response_model=list[CollectionPageResponse],
)
def list_collection_pages(
    collection_id: uuid.UUID,
    session: DatabaseSession,
) -> list[CollectionPage]:
    if session.get(IngestionCollection, collection_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return list(
        session.scalars(
            select(CollectionPage)
            .where(CollectionPage.collection_id == collection_id)
            .order_by(CollectionPage.page_number)
        )
    )
