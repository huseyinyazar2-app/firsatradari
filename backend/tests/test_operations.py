from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from firsat_radari.api.dependencies import get_db_session
from firsat_radari.config import Settings, get_settings
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    CostEntry,
    DataSource,
    IngestionRun,
    OperationalAlert,
    RawSnapshot,
)
from firsat_radari.main import create_app
from firsat_radari.operations.service import (
    CostEntryInput,
    OperationsService,
)


def _context() -> Iterator[tuple[Session, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session, factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def _source(session: Session) -> DataSource:
    source = DataSource(
        key="example",
        source_type="api",
        evidence_family_key="community",
        independence_group_key="example",
        independence_status="independent",
        owner="Example",
        base_url="https://example.test",
        policy_status="approved",
        policy_version="1",
        commercial_use_status="allowed",
        storage_permission="allowed",
        derived_data_permission="allowed",
        llm_processing_permission="allowed",
        retention_days=30,
        enabled=True,
    )
    session.add(source)
    session.commit()
    return source


def test_cost_ledger_is_idempotent_and_budget_alert_is_persistent() -> None:
    context = _context()
    session, _ = next(context)
    try:
        source = _source(session)
        now = datetime.now(UTC)
        service = OperationsService(session)
        payload = CostEntryInput(
            external_key="request:test:1",
            operation_type="licensed_api_request",
            amount=Decimal("6.50"),
            currency="usd",
            occurred_at=now - timedelta(minutes=1),
            source_id=source.id,
            units=Decimal("1"),
        )
        first = service.record_cost(payload)
        repeated = service.record_cost(payload)
        result = service.evaluate(
            as_of=now,
            freshness_hours=24,
            daily_budget_usd=Decimal("5"),
            monthly_budget_usd=Decimal("100"),
        )

        assert first.id == repeated.id
        assert session.query(CostEntry).count() == 1
        assert result.open_alert_count == 2
        alerts = session.query(OperationalAlert).all()
        assert {item.category for item in alerts} == {"cost_budget", "freshness"}
    finally:
        context.close()


def test_operations_api_exposes_cost_and_health_summary() -> None:
    context = _context()
    session, factory = next(context)
    try:
        source = _source(session)
        settings = Settings(
            environment="test",
            database_url="sqlite://",
            operations_api_enabled=True,
            daily_cost_budget_usd=Decimal("1"),
            monthly_cost_budget_usd=Decimal("10"),
        )

        def override_session() -> Iterator[Session]:
            with factory() as database_session:
                yield database_session

        app = create_app()
        app.dependency_overrides[get_db_session] = override_session
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app) as client:
            created = client.post(
                "/cost-entries",
                json={
                    "external_key": "request:api:1",
                    "operation_type": "api_request",
                    "amount": "1.25",
                    "currency": "USD",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "source_id": str(source.id),
                    "details": {"provider": "example"},
                },
            )
            evaluated = client.post(
                "/operations/evaluate",
                json={"as_of": datetime.now(UTC).isoformat()},
            )
            summary = client.get("/operations/summary")
            weekly = client.get("/reports/weekly")

        assert created.status_code == 201
        assert evaluated.status_code == 200
        assert summary.status_code == 200
        assert summary.json()["budget_status"] == "blocked"
        assert summary.json()["daily_cost_usd"] == "1.250000"
        assert weekly.status_code == 200
        assert weekly.json()["period"] == "weekly"
        assert weekly.json()["cost_by_currency"] == {"USD": "1.250000"}
    finally:
        context.close()


def test_expired_raw_snapshot_opens_critical_retention_alert() -> None:
    context = _context()
    session, _ = next(context)
    try:
        source = _source(session)
        now = datetime.now(UTC)
        session.add(
            RawSnapshot(
                source_id=source.id,
                run_id=None,
                collection_id=None,
                external_type="example",
                external_id="expired-1",
                observed_at=now - timedelta(days=40),
                source_created_at=None,
                source_updated_at=None,
                content_hash="a" * 64,
                object_storage_key="example/expired.json",
                media_type="application/json",
                schema_hint=None,
                policy_version="1",
                retention_until=now - timedelta(days=10),
                is_deleted_at_source=False,
            )
        )
        session.commit()

        result = OperationsService(session).evaluate(
            as_of=now,
            freshness_hours=24,
            daily_budget_usd=Decimal("0"),
            monthly_budget_usd=Decimal("0"),
        )

        retention_alert = session.query(OperationalAlert).filter_by(
            category="retention_expiry"
        ).one()
        assert result.open_alert_count == 2
        assert retention_alert.severity == "critical"
        assert retention_alert.details == {"count": 1}
    finally:
        context.close()


def test_recent_partial_run_with_data_counts_as_fresh_but_warns() -> None:
    context = _context()
    session, _ = next(context)
    try:
        source = _source(session)
        now = datetime.now(UTC)
        session.add(
            IngestionRun(
                source_id=source.id,
                collection_id=None,
                connector_version="test",
                job_type="discovery",
                query_definition={},
                query_fingerprint=None,
                status="partial",
                checkpoint_before=None,
                checkpoint_after=None,
                started_at=now - timedelta(minutes=2),
                finished_at=now - timedelta(minutes=1),
                request_count=1,
                response_count=1,
                raw_item_count=10,
                normalized_item_count=0,
                duplicate_item_count=0,
                error_count=0,
                estimated_cost=Decimal("0"),
            )
        )
        session.commit()

        result = OperationsService(session).evaluate(
            as_of=now,
            freshness_hours=24,
            daily_budget_usd=Decimal("0"),
            monthly_budget_usd=Decimal("0"),
        )

        alerts = session.query(OperationalAlert).all()
        assert result.open_alert_count == 1
        assert alerts[0].category == "source_failure"
        assert alerts[0].severity == "warning"
    finally:
        context.close()
