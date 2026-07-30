import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.models import (
    MetricDefinition,
    MetricObservation,
    MetricRun,
    ProblemClusterSignalObservation,
    ProblemClusterSignalRun,
    SignalDefinition,
    SignalValue,
)
from firsat_radari.metrics.cluster_signals import (
    ClusterSignalError,
    ProblemClusterSignalService,
)
from firsat_radari.metrics.github_problem import (
    GitHubProblemMetricEngine,
    MetricEngineError,
)

router = APIRouter(tags=["metrics"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class StartMetricRunRequest(BaseModel):
    collection_id: uuid.UUID


class StartClusterSignalRunRequest(BaseModel):
    clustering_run_id: uuid.UUID


class MetricDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    version: str
    name: str
    description: str
    unit: str
    numerator_description: str | None
    denominator_description: str | None
    minimum_sample_size: int
    window_days: int | None
    comparison_group_description: str
    freshness_policy: str
    confidence_method: str
    missing_data_policy: str
    outlier_policy: str
    active: bool


class MetricRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collection_id: uuid.UUID
    definition_set_version: str
    as_of: datetime
    status: str
    started_at: datetime
    finished_at: datetime | None
    input_document_count: int
    metric_count: int
    error_count: int


class MetricObservationResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    collection_id: uuid.UUID
    entity_id: uuid.UUID
    metric_key: str
    metric_version: str
    as_of: datetime
    numerator: Decimal | None
    denominator: Decimal | None
    value: Decimal | None
    unit: str
    sample_size: int
    status: str
    confidence_lower: Decimal | None
    confidence_upper: Decimal | None
    calculation: dict[str, Any]


class SignalValueResponse(BaseModel):
    id: uuid.UUID
    signal_key: str
    metric_key: str
    metric_observation_id: uuid.UUID
    baseline_observation_id: uuid.UUID | None
    entity_id: uuid.UUID
    as_of: datetime
    absolute_change: Decimal | None
    relative_change: Decimal | None
    direction: str | None
    status: str
    explanation: dict[str, Any]


class ClusterSignalRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clustering_run_id: uuid.UUID
    algorithm_version: str
    input_fingerprint: str
    status: str
    cluster_count: int
    observation_count: int
    started_at: datetime
    finished_at: datetime | None


class ClusterSignalObservationResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    cluster_id: uuid.UUID
    metric_key: str
    point_count: int
    first_at: datetime | None
    last_at: datetime | None
    slope_per_day: Decimal | None
    relative_change_30d: Decimal | None
    trend_direction: str | None
    anomaly_score: Decimal | None
    anomaly_status: str
    seasonality_period_days: int | None
    seasonality_strength: Decimal | None
    status: str
    calculation: dict[str, Any]


@router.post(
    "/metric-runs",
    response_model=MetricRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_metric_run(
    request: StartMetricRunRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> MetricRun:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = GitHubProblemMetricEngine(session).calculate(request.collection_id)
    except MetricEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(MetricRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metric run could not be loaded",
        )
    return run


@router.get(
    "/metric-definitions",
    response_model=list[MetricDefinitionResponse],
)
def list_metric_definitions(
    session: DatabaseSession,
    active: bool | None = None,
) -> list[MetricDefinition]:
    statement = select(MetricDefinition).order_by(
        MetricDefinition.key,
        MetricDefinition.version,
    )
    if active is not None:
        statement = statement.where(MetricDefinition.active == active)
    return list(session.scalars(statement))


@router.get("/metric-runs", response_model=list[MetricRunResponse])
def list_metric_runs(
    session: DatabaseSession,
    collection_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[MetricRun]:
    statement = select(MetricRun).order_by(MetricRun.started_at.desc()).limit(limit)
    if collection_id is not None:
        statement = statement.where(MetricRun.collection_id == collection_id)
    return list(session.scalars(statement))


@router.get("/metric-runs/{run_id}", response_model=MetricRunResponse)
def get_metric_run(run_id: uuid.UUID, session: DatabaseSession) -> MetricRun:
    run = session.get(MetricRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric run not found",
        )
    return run


@router.get(
    "/metric-runs/{run_id}/observations",
    response_model=list[MetricObservationResponse],
)
def list_metric_observations(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[MetricObservationResponse]:
    if session.get(MetricRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric run not found",
        )
    rows = session.execute(
        select(
            MetricObservation,
            MetricDefinition.key,
            MetricDefinition.version,
        )
        .join(
            MetricDefinition,
            MetricDefinition.id == MetricObservation.metric_definition_id,
        )
        .where(MetricObservation.run_id == run_id)
        .order_by(MetricDefinition.key)
    )
    return [
        MetricObservationResponse(
            id=observation.id,
            run_id=observation.run_id,
            collection_id=observation.collection_id,
            entity_id=observation.entity_id,
            metric_key=metric_key,
            metric_version=metric_version,
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
        for observation, metric_key, metric_version in rows
    ]


@router.get("/signals", response_model=list[SignalValueResponse])
def list_signal_values(
    session: DatabaseSession,
    entity_id: uuid.UUID | None = None,
    metric_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SignalValueResponse]:
    statement = (
        select(
            SignalValue,
            SignalDefinition.key,
            MetricDefinition.key,
        )
        .join(
            SignalDefinition,
            SignalDefinition.id == SignalValue.signal_definition_id,
        )
        .join(
            MetricObservation,
            MetricObservation.id == SignalValue.metric_observation_id,
        )
        .join(
            MetricDefinition,
            MetricDefinition.id == MetricObservation.metric_definition_id,
        )
        .order_by(SignalValue.as_of.desc())
        .limit(limit)
    )
    if entity_id is not None:
        statement = statement.where(SignalValue.entity_id == entity_id)
    if metric_key is not None:
        statement = statement.where(MetricDefinition.key == metric_key)
    rows = session.execute(statement)
    return [
        SignalValueResponse(
            id=signal.id,
            signal_key=signal_key,
            metric_key=row_metric_key,
            metric_observation_id=signal.metric_observation_id,
            baseline_observation_id=signal.baseline_observation_id,
            entity_id=signal.entity_id,
            as_of=signal.as_of,
            absolute_change=signal.absolute_change,
            relative_change=signal.relative_change,
            direction=signal.direction,
            status=signal.status,
            explanation=signal.explanation,
        )
        for signal, signal_key, row_metric_key in rows
    ]


@router.post(
    "/problem-cluster-signal-runs",
    response_model=ClusterSignalRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cluster_signal_run(
    request: StartClusterSignalRunRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> ProblemClusterSignalRun:
    if not settings.metrics_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics API is disabled",
        )
    try:
        outcome = ProblemClusterSignalService(session).calculate(
            request.clustering_run_id
        )
    except ClusterSignalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    run = session.get(ProblemClusterSignalRun, outcome.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cluster signal run could not be loaded",
        )
    return run


@router.get(
    "/problem-cluster-signal-runs/{run_id}/observations",
    response_model=list[ClusterSignalObservationResponse],
)
def list_cluster_signal_observations(
    run_id: uuid.UUID,
    session: DatabaseSession,
) -> list[ClusterSignalObservationResponse]:
    if session.get(ProblemClusterSignalRun, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster signal run not found",
        )
    return [
        ClusterSignalObservationResponse(
            id=observation.id,
            run_id=observation.run_id,
            cluster_id=observation.cluster_id,
            metric_key=metric_key,
            point_count=observation.point_count,
            first_at=observation.first_at,
            last_at=observation.last_at,
            slope_per_day=observation.slope_per_day,
            relative_change_30d=observation.relative_change_30d,
            trend_direction=observation.trend_direction,
            anomaly_score=observation.anomaly_score,
            anomaly_status=observation.anomaly_status,
            seasonality_period_days=observation.seasonality_period_days,
            seasonality_strength=observation.seasonality_strength,
            status=observation.status,
            calculation=observation.calculation,
        )
        for observation, metric_key in session.execute(
            select(
                ProblemClusterSignalObservation,
                MetricDefinition.key,
            )
            .join(
                MetricDefinition,
                MetricDefinition.id
                == ProblemClusterSignalObservation.metric_definition_id,
            )
            .where(ProblemClusterSignalObservation.run_id == run_id)
            .order_by(
                ProblemClusterSignalObservation.cluster_id,
                MetricDefinition.key,
            )
        )
    ]
