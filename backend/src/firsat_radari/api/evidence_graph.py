import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    ClaimCommercialOutcomeLink,
    ClaimEvidenceLink,
    EvidenceClaim,
    EvidenceClaimReview,
)
from firsat_radari.evidence_graph.ontology import (
    EvidenceClaimReviewInput,
    OntologyClaimError,
    OntologyClaimProposalInput,
    OntologyClaimService,
)
from firsat_radari.evidence_graph.service import (
    EvidenceGraphError,
    EvidenceGraphService,
)

router = APIRouter(tags=["evidence-graph"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class EvidenceGraphMaterializationResponse(BaseModel):
    clustering_run_id: uuid.UUID
    claim_count: int
    created_count: int
    reused_count: int


class EvidenceClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cluster_id: uuid.UUID
    supersedes_claim_id: uuid.UUID | None
    claim_type: str
    statement: str
    status: str
    generator_key: str
    generator_version: str
    input_fingerprint: str
    evidence_level: str
    source_count: int
    independence_group_count: int
    supporting_evidence_count: int
    independence_blockers: list[str]
    is_current: bool
    created_by: str
    created_at: datetime


class ClaimEvidenceLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    problem_evidence_id: uuid.UUID
    source_id: uuid.UUID
    direction: str
    created_at: datetime


class ProposeOntologyClaimRequest(BaseModel):
    cluster_id: uuid.UUID
    claim_type: str
    statement: str = Field(min_length=1, max_length=4_000)
    supporting_problem_evidence_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=500,
    )
    refuting_problem_evidence_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=500,
    )
    commercial_outcome_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=100,
    )
    generator_key: str = Field(min_length=1, max_length=80)
    generator_version: str = Field(min_length=1, max_length=40)
    created_by: str = Field(min_length=1, max_length=200)


class ReviewEvidenceClaimRequest(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    decision: str
    reviewer: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=4_000)


class EvidenceClaimReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    version: str
    previous_status: str
    decision: str
    reviewer: str
    rationale: str
    reviewed_at: datetime


class ClaimCommercialOutcomeLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    outcome_id: uuid.UUID
    direction: str
    created_at: datetime


class OntologyDraftResponse(BaseModel):
    cluster_id: uuid.UUID
    claim_ids: dict[str, uuid.UUID]
    missing_claim_types: list[str]


@router.post(
    "/problem-clustering-runs/{run_id}/claims",
    response_model=EvidenceGraphMaterializationResponse,
    status_code=status.HTTP_201_CREATED,
)
def materialize_problem_claims(
    run_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
) -> EvidenceGraphMaterializationResponse:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = EvidenceGraphService(session).materialize_problem_claims(
            run_id
        )
    except EvidenceGraphError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return EvidenceGraphMaterializationResponse(
        clustering_run_id=outcome.clustering_run_id,
        claim_count=outcome.claim_count,
        created_count=outcome.created_count,
        reused_count=outcome.reused_count,
    )


@router.get("/evidence-claims", response_model=list[EvidenceClaimResponse])
def list_evidence_claims(
    session: DatabaseSession,
    cluster_id: uuid.UUID | None = None,
    claim_type: str | None = None,
    is_current: bool | None = True,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[EvidenceClaim]:
    statement = (
        select(EvidenceClaim)
        .order_by(EvidenceClaim.created_at.desc(), EvidenceClaim.id)
        .limit(limit)
    )
    if cluster_id is not None:
        statement = statement.where(EvidenceClaim.cluster_id == cluster_id)
    if claim_type is not None:
        statement = statement.where(EvidenceClaim.claim_type == claim_type)
    if is_current is not None:
        statement = statement.where(EvidenceClaim.is_current == is_current)
    return list(session.scalars(statement))


@router.get(
    "/evidence-claims/{claim_id}/evidence",
    response_model=list[ClaimEvidenceLinkResponse],
)
def list_claim_evidence(
    claim_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ClaimEvidenceLink]:
    if session.get(EvidenceClaim, claim_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence claim not found",
        )
    return list(
        session.scalars(
            select(ClaimEvidenceLink)
            .where(ClaimEvidenceLink.claim_id == claim_id)
            .order_by(
                ClaimEvidenceLink.direction,
                ClaimEvidenceLink.problem_evidence_id,
            )
        )
    )


@router.post(
    "/problem-clusters/{cluster_id}/ontology-drafts",
    response_model=OntologyDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_ontology_drafts(
    cluster_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
) -> OntologyDraftResponse:
    _ensure_ontology_claim_api(settings)
    try:
        outcome = OntologyClaimService(
            session
        ).generate_observed_drafts(cluster_id)
    except OntologyClaimError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return OntologyDraftResponse(
        cluster_id=outcome.cluster_id,
        claim_ids=outcome.claim_ids,
        missing_claim_types=list(outcome.missing_claim_types),
    )


@router.post(
    "/ontology-claims",
    response_model=EvidenceClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
def propose_ontology_claim(
    request: ProposeOntologyClaimRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> EvidenceClaim:
    _ensure_ontology_claim_api(settings)
    try:
        return OntologyClaimService(session).propose(
            OntologyClaimProposalInput(
                cluster_id=request.cluster_id,
                claim_type=request.claim_type,
                statement=request.statement,
                supporting_problem_evidence_ids=tuple(
                    request.supporting_problem_evidence_ids
                ),
                refuting_problem_evidence_ids=tuple(
                    request.refuting_problem_evidence_ids
                ),
                commercial_outcome_ids=tuple(
                    request.commercial_outcome_ids
                ),
                generator_key=request.generator_key,
                generator_version=request.generator_version,
                created_by=request.created_by,
            )
        )
    except OntologyClaimError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/evidence-claims/{claim_id}/reviews",
    response_model=EvidenceClaimReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def review_evidence_claim(
    claim_id: uuid.UUID,
    request: ReviewEvidenceClaimRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> EvidenceClaimReview:
    _ensure_ontology_claim_api(settings)
    try:
        return OntologyClaimService(session).review(
            EvidenceClaimReviewInput(
                claim_id=claim_id,
                version=request.version,
                decision=request.decision,
                reviewer=request.reviewer,
                rationale=request.rationale,
            )
        )
    except OntologyClaimError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/evidence-claims/{claim_id}/reviews",
    response_model=list[EvidenceClaimReviewResponse],
)
def list_evidence_claim_reviews(
    claim_id: uuid.UUID,
    session: DatabaseSession,
) -> list[EvidenceClaimReview]:
    if session.get(EvidenceClaim, claim_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence claim not found",
        )
    return list(
        session.scalars(
            select(EvidenceClaimReview)
            .where(EvidenceClaimReview.claim_id == claim_id)
            .order_by(EvidenceClaimReview.reviewed_at.desc())
        )
    )


@router.get(
    "/evidence-claims/{claim_id}/commercial-evidence",
    response_model=list[ClaimCommercialOutcomeLinkResponse],
)
def list_claim_commercial_evidence(
    claim_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ClaimCommercialOutcomeLink]:
    if session.get(EvidenceClaim, claim_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence claim not found",
        )
    return list(
        session.scalars(
            select(ClaimCommercialOutcomeLink)
            .where(ClaimCommercialOutcomeLink.claim_id == claim_id)
            .order_by(ClaimCommercialOutcomeLink.outcome_id)
        )
    )


def _ensure_ontology_claim_api(settings: Settings) -> None:
    if not settings.ontology_claim_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ontology claim API is disabled",
        )
