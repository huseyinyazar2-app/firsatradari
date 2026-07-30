import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    PackageRepositoryLink,
    PackageRepositoryLinkReview,
)

router = APIRouter(prefix="/entity-links", tags=["entity-links"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class PackageRepositoryLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_id: uuid.UUID
    repository_id: uuid.UUID | None
    repository_full_name: str
    source_url: str
    repository_directory: str | None
    match_method: str
    confidence: Decimal
    status: str
    evidence: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    reviewer: str | None
    review_notes: str | None


class ReviewPackageRepositoryLinkRequest(BaseModel):
    status: Literal["confirmed", "rejected"]
    reviewer: str = Field(min_length=2, max_length=200)
    notes: str | None = Field(default=None, max_length=5_000)


@router.get(
    "/package-repositories",
    response_model=list[PackageRepositoryLinkResponse],
)
def list_package_repository_links(
    session: DatabaseSession,
    link_status: str | None = Query(default=None, alias="status"),
    repository_full_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[PackageRepositoryLink]:
    statement = (
        select(PackageRepositoryLink)
        .order_by(PackageRepositoryLink.updated_at.desc())
        .limit(limit)
    )
    if link_status is not None:
        statement = statement.where(PackageRepositoryLink.status == link_status)
    if repository_full_name is not None:
        statement = statement.where(
            PackageRepositoryLink.repository_full_name
            == repository_full_name.lower()
        )
    return list(session.scalars(statement))


@router.patch(
    "/package-repositories/{link_id}",
    response_model=PackageRepositoryLinkResponse,
)
def review_package_repository_link(
    link_id: uuid.UUID,
    request: ReviewPackageRepositoryLinkRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> PackageRepositoryLink:
    if not settings.entity_link_review_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Entity-link review API is disabled",
        )
    link = session.get(PackageRepositoryLink, link_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package-repository link not found",
        )
    if request.status == "confirmed" and link.repository_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository entity must exist before confirmation",
        )
    reviewed_at = datetime.now(UTC)
    session.add(
        PackageRepositoryLinkReview(
            link_id=link.id,
            previous_status=link.status,
            new_status=request.status,
            reviewer=request.reviewer,
            notes=request.notes,
            reviewed_at=reviewed_at,
        )
    )
    link.status = request.status
    link.reviewer = request.reviewer
    link.review_notes = request.notes
    link.reviewed_at = reviewed_at
    link.updated_at = reviewed_at
    session.commit()
    return link
