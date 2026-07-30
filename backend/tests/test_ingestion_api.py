from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)
from firsat_radari.db.base import Base
from firsat_radari.db.models import DataSource
from firsat_radari.main import create_app


class ApiFakeConnector(DataConnector):
    source_key = "npm"
    version = "api-test-1"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=False,
        incremental=False,
        historical=False,
        deletions=False,
        conditional_requests=False,
        pagination="offset",
        rate_limit_headers=False,
        source_timestamps=True,
    )

    async def discover(
        self,
        query: dict,
        checkpoint: dict | None = None,
    ) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=[
                RawItem(
                    external_type="package_search_result",
                    external_id="example-package",
                    payload={"package": {"name": "example-package"}},
                    observed_at=datetime.now(UTC),
                )
            ],
            is_complete=True,
        )

    async def fetch(self, external_id: str) -> CollectionResult:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None


@pytest.fixture
def api_context(tmp_path: Path) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        ingestion_api_enabled=True,
        ingestion_api_max_pages=2,
        normalization_api_enabled=True,
        normalization_api_max_items=10,
    )

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    yield app, session_factory

    Base.metadata.drop_all(engine)
    engine.dispose()


def add_approved_npm_source(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(
            DataSource(
                key="npm",
                source_type="registry",
                owner="npm",
                base_url="https://registry.npmjs.org",
                policy_status="approved",
                policy_version="test-policy",
                commercial_use_status="allowed",
                storage_permission="allowed",
                derived_data_permission="allowed",
                llm_processing_permission="prohibited",
                retention_days=30,
                enabled=True,
            )
        )
        session.commit()


@pytest.mark.asyncio
async def test_ingestion_api_runs_with_validated_query_and_exposes_status(
    api_context: tuple[FastAPI, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session_factory = api_context
    add_approved_npm_source(session_factory)
    monkeypatch.setattr(
        "firsat_radari.api.ingestion.create_connector",
        lambda source_key, settings: ApiFakeConnector(),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/ingestion-runs",
            json={
                "source_key": "npm",
                "query": {"text": "testing", "size": 1},
                "max_pages": 1,
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "succeeded"
        assert payload["raw_item_count"] == 1
        run_response = await client.get(f"/ingestion-runs/{payload['id']}")
        assert run_response.status_code == 200
        runs = (await client.get("/ingestion-runs", params={"source_key": "npm"})).json()
        assert [run["id"] for run in runs] == [payload["id"]]
        quality_events = await client.get(f"/ingestion-runs/{payload['id']}/quality-events")
        assert quality_events.json() == []
        collection = await client.get(f"/collections/{payload['collection_id']}")
        assert collection.json()["is_complete"] is True
        pages = await client.get(f"/collections/{payload['collection_id']}/pages")
        assert pages.json()[0]["items_returned"] == 1
        sources = (await client.get("/sources")).json()
        assert [source["key"] for source in sources] == ["npm"]
        policies = await client.get("/sources/npm/policies")
        assert policies.json() == []
        health = (await client.get("/sources/npm/health")).json()
        assert health["latest_run_status"] == "succeeded"
        assert health["incomplete_collection_count"] == 0
        normalization = await client.post(
            "/normalization-runs",
            json={"source_key": "npm", "limit": 1},
        )
        assert normalization.status_code == 201
        assert normalization.json()["success_count"] == 1
        normalization_runs = (
            await client.get(
                "/normalization-runs",
                params={"source_key": "npm"},
            )
        ).json()
        assert normalization_runs[0]["id"] == normalization.json()["id"]


@pytest.mark.asyncio
async def test_ingestion_api_rejects_unknown_query_fields(
    api_context: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, session_factory = api_context
    add_approved_npm_source(session_factory)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/ingestion-runs",
            json={"source_key": "npm", "query": {"text": "testing", "unsafe": True}},
        )

        assert response.status_code == 422
        assert "Unsupported query fields" in response.json()["detail"]

        checkpoint_response = await client.post(
            "/ingestion-runs",
            json={
                "source_key": "npm",
                "query": {"text": "testing"},
                "checkpoint": {"page": 2},
            },
        )
        assert checkpoint_response.status_code == 422


@pytest.mark.asyncio
async def test_ingestion_api_is_disabled_by_default() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url="sqlite://",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/ingestion-runs",
            json={"source_key": "npm", "query": {"text": "testing"}},
        )

    assert response.status_code == 503
