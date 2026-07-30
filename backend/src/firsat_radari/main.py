import hmac
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from firsat_radari.api.collections import router as collections_router
from firsat_radari.api.commercial_validation import (
    router as commercial_validation_router,
)
from firsat_radari.api.entity_links import router as entity_links_router
from firsat_radari.api.evidence_graph import router as evidence_graph_router
from firsat_radari.api.health import router as health_router
from firsat_radari.api.ingestion import router as ingestion_router
from firsat_radari.api.metrics import router as metrics_router
from firsat_radari.api.normalization import router as normalization_router
from firsat_radari.api.operations import router as operations_router
from firsat_radari.api.opportunities import router as opportunities_router
from firsat_radari.api.problem_clusters import router as problem_clusters_router
from firsat_radari.api.problem_evidence import router as problem_evidence_router
from firsat_radari.api.profiles import router as profiles_router
from firsat_radari.api.reports import router as reports_router
from firsat_radari.api.research import router as research_router
from firsat_radari.api.scheduler import router as scheduler_router
from firsat_radari.api.sources import router as sources_router
from firsat_radari.config import get_settings
from firsat_radari.db.models import AuditEvent

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Fırsat Radarı API",
        version="0.1.0",
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=[
                "GET",
                "HEAD",
                "OPTIONS",
                "POST",
                "PATCH",
                "PUT",
                "DELETE",
            ],
            allow_headers=[
                "Accept",
                "Content-Type",
                "X-Firsat-Api-Key",
                "X-Firsat-Actor",
                "X-Request-ID",
            ],
        )

    @app.middleware("http")
    async def protect_mutations(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started_at = datetime.now(UTC)
        started_clock = monotonic()
        response = None
        is_mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
        is_protected_read = (
            settings.environment == "production"
            and request.method != "OPTIONS"
            and request.url.path != "/health"
        )
        requires_key = is_mutation or is_protected_read
        if requires_key:
            configured_key = (
                settings.mutation_api_key.get_secret_value()
                if settings.mutation_api_key is not None
                else None
            )
            if settings.environment == "production" and configured_key is None:
                response = JSONResponse(
                    {"detail": "API key is not configured"},
                    status_code=503,
                    headers={"X-Request-ID": request_id},
                )
            supplied_key = request.headers.get("X-Firsat-Api-Key")
            if response is None and configured_key is not None and (
                supplied_key is None
                or not hmac.compare_digest(supplied_key, configured_key)
            ):
                response = JSONResponse(
                    {"detail": "Invalid API key"},
                    status_code=401,
                    headers={"X-Request-ID": request_id},
                )
        try:
            if response is None:
                response = await call_next(request)
        except Exception:
            if settings.audit_log_enabled:
                _write_audit_event(
                    request=request,
                    request_id=request_id,
                    status_code=500,
                    started_at=started_at,
                    duration_ms=_duration_ms(started_clock),
                )
            raise
        response.headers["X-Request-ID"] = request_id
        if (
            settings.audit_log_enabled
            and is_mutation
        ):
            _write_audit_event(
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                started_at=started_at,
                duration_ms=_duration_ms(started_clock),
            )
        return response
    app.include_router(health_router)
    app.include_router(sources_router)
    app.include_router(ingestion_router)
    app.include_router(collections_router)
    app.include_router(normalization_router)
    app.include_router(metrics_router)
    app.include_router(problem_evidence_router)
    app.include_router(entity_links_router)
    app.include_router(problem_clusters_router)
    app.include_router(opportunities_router)
    app.include_router(evidence_graph_router)
    app.include_router(commercial_validation_router)
    app.include_router(operations_router)
    app.include_router(reports_router)
    app.include_router(research_router)
    app.include_router(profiles_router)
    app.include_router(scheduler_router)
    return app


app = create_app()


def _duration_ms(started_clock: float) -> int:
    return max(0, round((monotonic() - started_clock) * 1_000))


def _write_audit_event(
    *,
    request: Request,
    request_id: str,
    status_code: int,
    started_at: datetime,
    duration_ms: int,
) -> None:
    from firsat_radari.db.session import SessionLocal

    actor = request.headers.get("X-Firsat-Actor", "unknown").strip()
    if not actor:
        actor = "unknown"
    try:
        with SessionLocal() as session:
            session.add(
                AuditEvent(
                    request_id=request_id[:100],
                    actor=actor[:200],
                    method=request.method[:10],
                    path=request.url.path[:500],
                    status_code=status_code,
                    outcome="succeeded" if status_code < 400 else "rejected",
                    duration_ms=duration_ms,
                    details={},
                    occurred_at=started_at,
                )
            )
            session.commit()
    except Exception:
        logger.exception("Could not persist mutation audit event")
