import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    MetricDefinition,
    NormalizedDocument,
    ProblemCluster,
    ProblemClusterAudit,
    ProblemClusteringQualitySnapshot,
    ProblemClusteringRun,
    ProblemClusterLineage,
    ProblemClusterLineageRun,
    ProblemClusterMembership,
    ProblemClusterMetricObservation,
    ProblemClusterMetricRun,
    ProblemEvidence,
)
from firsat_radari.metrics.problem_clusters import (
    ProblemClusterMetricEngine,
    ProblemClusterMetricError,
)
from firsat_radari.problem_mining.clustering import (
    ProblemClusteringEngine,
    ProblemClusteringError,
)
from firsat_radari.problem_mining.lineage import (
    ProblemClusterLineageError,
    ProblemClusterLineageService,
)
from firsat_radari.problem_mining.quality import (
    ClusterAuditInput,
    ProblemClusterQualityError,
    ProblemClusterQualityService,
)

router = APIRouter(tags=["problem-clusters"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartProblemClusteringRequest(BaseModel):
    as_of: datetime | None = None
    source_created_from: datetime | None = None


class ProblemClusteringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    algorithm_key: str
    algorithm_version: str
    input_fingerprint: str
    input_definition: dict
    as_of: datetime
    status: str
    started_at: datetime
    finished_at: datetime | None
    input_count: int
    eligible_count: int
    cluster_count: int
    singleton_count: int
    error_count: int


class ProblemClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    fingerprint: str
    signature: list[str]
    label: str
    status: str
    representative_evidence_id: uuid.UUID
    document_count: int
    entity_count: int
    source_count: int
    cohesion_min: Decimal
    cohesion_mean: Decimal
    first_source_created_at: datetime | None
    last_source_created_at: datetime | None
    created_at: datetime


class ProblemClusterMemberResponse(BaseModel):
    membership_id: uuid.UUID
    evidence_id: uuid.UUID
    document_id: uuid.UUID
    entity_id: uuid.UUID
    source_id: uuid.UUID
    similarity_to_representative: Decimal
    excerpt: str
    canonical_url: str | None
    source_created_at: datetime | None


class StartProblemClusterMetricRequest(BaseModel):
    clustering_run_id: uuid.UUID


class ProblemClusterMetricRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clustering_run_id: uuid.UUID
    definition_set_version: str
    input_fingerprint: str
    as_of: datetime
    status: str
    started_at: datetime
    finished_at: datetime | None
    cluster_count: int
    metric_count: int
    error_count: int


class ProblemClusterMetricObservationResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    cluster_id: uuid.UUID
    metric_key: str
    as_of: datetime
    numerator: Decimal | None
    denominator: Decimal | None
    value: Decimal | None
    unit: str
    sample_size: int
    status: str
    confidence_lower: Decimal | None
    confidence_upper: Decimal | None
    calculation: dict


class CreateProblemClusterAuditRequest(BaseModel):
    reviewer: str
    verdict: str
    sample_method: str = "random_member_sample"
    sampled_member_count: int
    coherent_member_count: int
    notes: str | None = None


class ProblemClusterAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clustering_run_id: uuid.UUID
    cluster_id: uuid.UUID
    supersedes_audit_id: uuid.UUID | None
    reviewer: str
    verdict: str
    sample_method: str
    sampled_member_count: int
    coherent_member_count: int
    purity: Decimal
    notes: str | None
    created_at: datetime


class ProblemClusteringQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clustering_run_id: uuid.UUID
    input_fingerprint: str
    status: str
    eligible_cluster_count: int
    audited_cluster_count: int
    coherent_cluster_count: int
    sampled_member_count: int
    coherent_member_count: int
    audit_coverage: Decimal
    cluster_coherence_rate: Decimal | None
    member_purity: Decimal | None
    purity_confidence_lower: Decimal | None
    purity_confidence_upper: Decimal | None
    passes_quality_gate: bool
    calculation: dict
    calculated_at: datetime


class CreateProblemClusterLineageRequest(BaseModel):
    previous_clustering_run_id: uuid.UUID
    current_clustering_run_id: uuid.UUID


class ProblemClusterLineageRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_clustering_run_id: uuid.UUID
    current_clustering_run_id: uuid.UUID
    algorithm_version: str
    status: str
    previous_cluster_count: int
    current_cluster_count: int
    matched_cluster_count: int
    stable_cluster_count: int
    split_relation_count: int
    merge_relation_count: int
    new_cluster_count: int
    disappeared_cluster_count: int
    stability_rate: Decimal | None
    mean_best_member_jaccard: Decimal | None
    passes_stability_gate: bool
    calculation: dict
    started_at: datetime
    finished_at: datetime | None


class ProblemClusterLineageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lineage_run_id: uuid.UUID
    previous_cluster_id: uuid.UUID | None
    current_cluster_id: uuid.UUID | None
    relation_type: str
    member_jaccard: Decimal | None
    signature_jaccard: Decimal | None
    created_at: datetime


@router.post(
    "/problem-clustering-runs",
    response_model=ProblemClusteringRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_problem_clustering(
    request: StartProblemClusteringRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusteringRun:
    if not settings.problem_clustering_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Problem clustering API is disabled",
        )
    try:
        outcome = ProblemClusteringEngine(session).cluster(
            as_of=request.as_of,
            source_created_from=request.source_created_from,
        )
    except ProblemClusteringError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(ProblemClusteringRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Problem clustering run could not be loaded",
        )
    return run


@router.get(
    "/problem-clustering-runs",
    response_model=list[ProblemClusteringRunResponse],
)
def list_problem_clustering_runs(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProblemClusteringRun]:
    return list(
        session.scalars(
            select(ProblemClusteringRun)
            .order_by(ProblemClusteringRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get("/problem-clusters", response_model=list[ProblemClusterResponse])
def list_problem_clusters(
    session: DatabaseSession,
    run_id: uuid.UUID | None = None,
    cluster_status: str | None = Query(default=None, alias="status"),
    minimum_entity_count: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ProblemCluster]:
    statement = (
        select(ProblemCluster)
        .where(ProblemCluster.entity_count >= minimum_entity_count)
        .order_by(
            ProblemCluster.entity_count.desc(),
            ProblemCluster.document_count.desc(),
            ProblemCluster.cohesion_mean.desc(),
        )
        .limit(limit)
    )
    if run_id is not None:
        statement = statement.where(ProblemCluster.run_id == run_id)
    if cluster_status is not None:
        statement = statement.where(ProblemCluster.status == cluster_status)
    return list(session.scalars(statement))


@router.get(
    "/problem-clusters/{cluster_id}/members",
    response_model=list[ProblemClusterMemberResponse],
)
def list_problem_cluster_members(
    cluster_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ProblemClusterMemberResponse]:
    if session.get(ProblemCluster, cluster_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem cluster not found",
        )
    rows = session.execute(
        select(
            ProblemClusterMembership,
            ProblemEvidence.excerpt,
            NormalizedDocument.canonical_url,
            NormalizedDocument.source_created_at,
        )
        .join(
            ProblemEvidence,
            ProblemEvidence.id == ProblemClusterMembership.evidence_id,
        )
        .join(
            NormalizedDocument,
            NormalizedDocument.id == ProblemClusterMembership.document_id,
        )
        .where(ProblemClusterMembership.cluster_id == cluster_id)
        .order_by(ProblemClusterMembership.similarity_to_representative.desc())
    )
    return [
        ProblemClusterMemberResponse(
            membership_id=membership.id,
            evidence_id=membership.evidence_id,
            document_id=membership.document_id,
            entity_id=membership.entity_id,
            source_id=membership.source_id,
            similarity_to_representative=(
                membership.similarity_to_representative
            ),
            excerpt=excerpt,
            canonical_url=canonical_url,
            source_created_at=source_created_at,
        )
        for membership, excerpt, canonical_url, source_created_at in rows
    ]


@router.post(
    "/problem-cluster-metric-runs",
    response_model=ProblemClusterMetricRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_problem_cluster_metric_run(
    request: StartProblemClusterMetricRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusterMetricRun:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = ProblemClusterMetricEngine(session).calculate(
            request.clustering_run_id
        )
    except ProblemClusterMetricError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(ProblemClusterMetricRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Problem cluster metric run could not be loaded",
        )
    return run


@router.get(
    "/problem-cluster-metric-runs/{run_id}/observations",
    response_model=list[ProblemClusterMetricObservationResponse],
)
def list_problem_cluster_metric_observations(
    run_id: uuid.UUID,
    session: DatabaseSession,
    cluster_id: uuid.UUID | None = None,
) -> list[ProblemClusterMetricObservationResponse]:
    if session.get(ProblemClusterMetricRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem cluster metric run not found",
        )
    statement = (
        select(
            ProblemClusterMetricObservation,
            MetricDefinition.key,
        )
        .join(
            MetricDefinition,
            MetricDefinition.id
            == ProblemClusterMetricObservation.metric_definition_id,
        )
        .where(ProblemClusterMetricObservation.run_id == run_id)
        .order_by(
            ProblemClusterMetricObservation.cluster_id,
            MetricDefinition.key,
        )
    )
    if cluster_id is not None:
        statement = statement.where(
            ProblemClusterMetricObservation.cluster_id == cluster_id
        )
    rows = session.execute(statement)
    return [
        ProblemClusterMetricObservationResponse(
            id=observation.id,
            run_id=observation.run_id,
            cluster_id=observation.cluster_id,
            metric_key=metric_key,
            as_of=observation.as_of,
            numerator=observation.numerator,
            denominator=observation.denominator,
            value=observation.value,
            unit=observation.unit,
            sample_size=observation.sample_size,
            status=observation.status,
            confidence_lower=observation.confidence_lower,
            confidence_upper=observation.confidence_upper,
            calculation=observation.calculation,
        )
        for observation, metric_key in rows
    ]


@router.post(
    "/problem-clusters/{cluster_id}/audits",
    response_model=ProblemClusterAuditResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_problem_cluster_audit(
    cluster_id: uuid.UUID,
    request: CreateProblemClusterAuditRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusterAudit:
    if not settings.problem_cluster_review_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Problem cluster review API is disabled",
        )
    try:
        return ProblemClusterQualityService(session).add_audit(
            ClusterAuditInput(
                cluster_id=cluster_id,
                reviewer=request.reviewer,
                verdict=request.verdict,
                sample_method=request.sample_method,
                sampled_member_count=request.sampled_member_count,
                coherent_member_count=request.coherent_member_count,
                notes=request.notes,
            )
        )
    except ProblemClusterQualityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/problem-clusters/{cluster_id}/audits",
    response_model=list[ProblemClusterAuditResponse],
)
def list_problem_cluster_audits(
    cluster_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ProblemClusterAudit]:
    if session.get(ProblemCluster, cluster_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem cluster not found",
        )
    return list(
        session.scalars(
            select(ProblemClusterAudit)
            .where(ProblemClusterAudit.cluster_id == cluster_id)
            .order_by(
                ProblemClusterAudit.created_at.desc(),
                ProblemClusterAudit.id.desc(),
            )
        )
    )


@router.post(
    "/problem-clustering-runs/{run_id}/quality-snapshots",
    response_model=ProblemClusteringQualityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_problem_clustering_quality_snapshot(
    run_id: uuid.UUID,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusteringQualitySnapshot:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = ProblemClusterQualityService(session).calculate(run_id)
    except ProblemClusterQualityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    snapshot = session.get(
        ProblemClusteringQualitySnapshot,
        outcome.snapshot_id,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Problem clustering quality snapshot could not be loaded",
        )
    return snapshot


@router.get(
    "/problem-clustering-runs/{run_id}/quality-snapshots",
    response_model=list[ProblemClusteringQualityResponse],
)
def list_problem_clustering_quality_snapshots(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ProblemClusteringQualitySnapshot]:
    if session.get(ProblemClusteringRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem clustering run not found",
        )
    return list(
        session.scalars(
            select(ProblemClusteringQualitySnapshot)
            .where(
                ProblemClusteringQualitySnapshot.clustering_run_id == run_id
            )
            .order_by(
                ProblemClusteringQualitySnapshot.calculated_at.desc()
            )
        )
    )


@router.post(
    "/problem-cluster-lineage-runs",
    response_model=ProblemClusterLineageRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_problem_cluster_lineage_run(
    request: CreateProblemClusterLineageRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusterLineageRun:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = ProblemClusterLineageService(session).compare(
            request.previous_clustering_run_id,
            request.current_clustering_run_id,
        )
    except ProblemClusterLineageError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(ProblemClusterLineageRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Problem cluster lineage run could not be loaded",
        )
    return run


@router.get(
    "/problem-cluster-lineage-runs/{run_id}/relations",
    response_model=list[ProblemClusterLineageResponse],
)
def list_problem_cluster_lineage_relations(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ProblemClusterLineage]:
    if session.get(ProblemClusterLineageRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem cluster lineage run not found",
        )
    return list(
        session.scalars(
            select(ProblemClusterLineage)
            .where(ProblemClusterLineage.lineage_run_id == run_id)
            .order_by(
                ProblemClusterLineage.relation_type,
                ProblemClusterLineage.id,
            )
        )
    )
