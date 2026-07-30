from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import (
    BACKEND_ROOT,
    PROJECT_ROOT,
    Settings,
    get_settings,
)
from firsat_radari.db.base import Base
from firsat_radari.main import create_app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_raw_storage_path_is_independent_from_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    settings = Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path="data/raw",
    )

    assert settings.raw_storage_path == (BACKEND_ROOT / "data" / "raw").resolve()
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"


@pytest.mark.asyncio
async def test_local_research_ui_origin_is_allowed() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3002",
                "Access-Control-Request-Method": "GET",
            },
        )
        mutation_response = await client.options(
            "/opportunity-exports",
            headers={
                "Origin": "http://localhost:3002",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "content-type,x-firsat-api-key,x-firsat-actor"
                ),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3002"
    assert "GET" in response.headers["access-control-allow-methods"]

    assert mutation_response.status_code == 200
    assert "POST" in mutation_response.headers[
        "access-control-allow-methods"
    ]


@pytest.mark.asyncio
async def test_configured_mutation_key_protects_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIRSAT_MUTATION_API_KEY", "test-secret-key-value")
    get_settings.cache_clear()
    try:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            rejected = await client.post("/health")
            accepted = await client.post(
                "/health",
                headers={"X-Firsat-Api-Key": "test-secret-key-value"},
            )
    finally:
        get_settings.cache_clear()

    assert rejected.status_code == 401
    assert accepted.status_code == 405


@pytest.mark.asyncio
async def test_production_read_endpoints_require_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIRSAT_ENVIRONMENT", "production")
    monkeypatch.setenv("FIRSAT_MUTATION_API_KEY", "production-secret")
    get_settings.cache_clear()
    try:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            health = await client.get("/health")
            protected = await client.get("/sources")
    finally:
        get_settings.cache_clear()

    assert health.status_code == 200
    assert protected.status_code == 401


@pytest.mark.asyncio
async def test_mutations_have_redacted_persistent_audit_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setenv("FIRSAT_AUDIT_LOG_ENABLED", "true")
    monkeypatch.setattr("firsat_radari.db.session.SessionLocal", factory)
    get_settings.cache_clear()
    try:
        app = create_app()

        def override_session():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db_session] = override_session
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            mutation = await client.post(
                "/health?secret=not-stored",
                headers={"X-Firsat-Actor": "audit-test"},
            )
            events = await client.get("/audit-events")
    finally:
        get_settings.cache_clear()
        Base.metadata.drop_all(engine)
        engine.dispose()

    assert mutation.status_code == 405
    assert events.status_code == 200
    assert len(events.json()) == 1
    event = events.json()[0]
    assert event["actor"] == "audit-test"
    assert event["method"] == "POST"
    assert event["path"] == "/health"
    assert event["outcome"] == "rejected"
    assert "secret" not in event["details"]
