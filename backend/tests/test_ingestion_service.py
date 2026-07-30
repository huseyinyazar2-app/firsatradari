from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)
from firsat_radari.db.base import Base
from firsat_radari.db.models import (
    CollectionPage,
    DataQualityEvent,
    DataSource,
    IngestionCheckpoint,
    IngestionCollection,
    IngestionRun,
    RawSnapshot,
    RawSnapshotObservation,
    RequestRecord,
)
from firsat_radari.ingestion.errors import SourcePolicyError
from firsat_radari.ingestion.service import IngestionService
from firsat_radari.operations.retention import RetentionService
from firsat_radari.storage.filesystem import FileObjectStore


class FakeConnector(DataConnector):
    source_key = "fake"
    version = "test-1"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=False,
        incremental=True,
        historical=False,
        deletions=False,
        conditional_requests=False,
        pagination="cursor",
        rate_limit_headers=True,
        source_timestamps=True,
    )

    def __init__(self, results: list[CollectionResult | Exception]) -> None:
        self._results = iter(results)
        self.checkpoints: list[dict | None] = []

    async def discover(
        self,
        query: dict,
        checkpoint: dict | None = None,
    ) -> CollectionResult:
        self.checkpoints.append(checkpoint)
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result

    async def fetch(self, external_id: str) -> CollectionResult:
        raise NotImplementedError


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_source(
    session: Session,
    *,
    enabled: bool = True,
    policy_status: str = "approved",
    policy_version: str | None = "2026-07-29",
    storage_permission: str = "allowed",
) -> DataSource:
    source = DataSource(
        key="fake",
        source_type="test",
        owner="test",
        base_url="https://example.test",
        policy_status=policy_status,
        policy_version=policy_version,
        commercial_use_status="allowed",
        storage_permission=storage_permission,
        derived_data_permission="unknown",
        llm_processing_permission="unknown",
        retention_days=30,
        enabled=enabled,
    )
    session.add(source)
    session.commit()
    return source


def raw_item(external_id: str, value: str) -> RawItem:
    return RawItem(
        external_type="record",
        external_id=external_id,
        payload={"id": external_id, "value": value},
        observed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_policy_gate_blocks_unapproved_source(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session, policy_status="candidate")
    service = IngestionService(session, FileObjectStore(tmp_path))

    with pytest.raises(SourcePolicyError, match="not approved"):
        await service.discover(FakeConnector([]), {"q": "test"})

    assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0


@pytest.mark.asyncio
async def test_discovery_persists_pages_and_request_audit(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    first_checkpoint = {"cursor": "page-2"}
    connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("1", "first")],
                checkpoint=first_checkpoint,
                is_complete=False,
                rate_limit_remaining=9,
            ),
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("2", "second")],
                checkpoint=None,
                is_complete=True,
                rate_limit_remaining=8,
            ),
        ]
    )
    store = FileObjectStore(tmp_path)

    outcome = await IngestionService(session, store).discover(connector, {"q": "test"})

    assert outcome.status == "succeeded"
    assert outcome.request_count == 2
    assert outcome.response_count == 2
    assert outcome.raw_item_count == 2
    assert outcome.duplicate_item_count == 0
    snapshots = session.scalars(select(RawSnapshot)).all()
    assert len(snapshots) == 2
    assert all(store.exists(snapshot.object_storage_key) for snapshot in snapshots)
    assert all(snapshot.retention_until is not None for snapshot in snapshots)
    assert session.scalar(select(func.count()).select_from(RequestRecord)) == 2


@pytest.mark.asyncio
async def test_repeated_payload_is_deduplicated(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    store = FileObjectStore(tmp_path)
    result = CollectionResult(
        status=CollectionStatus.SUCCEEDED,
        items=[raw_item("1", "same")],
        is_complete=True,
    )

    first = await IngestionService(session, store).discover(
        FakeConnector([result]),
        {"q": "test"},
    )
    second = await IngestionService(session, store).discover(
        FakeConnector([result]),
        {"q": "test"},
    )

    assert first.raw_item_count == 1
    assert second.raw_item_count == 0
    assert second.duplicate_item_count == 1
    assert session.scalar(select(func.count()).select_from(RawSnapshot)) == 1
    observations = session.scalars(
        select(RawSnapshotObservation).order_by(RawSnapshotObservation.is_duplicate)
    ).all()
    assert len(observations) == 2
    assert {observation.collection_id for observation in observations} == {
        collection_id for collection_id in session.scalars(select(IngestionCollection.id))
    }
    assert [observation.is_duplicate for observation in observations] == [False, True]
    assert len(list(tmp_path.rglob("*.json"))) == 1


@pytest.mark.asyncio
async def test_reobserved_purged_payload_is_restored_and_retention_is_renewed(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    store = FileObjectStore(tmp_path)
    service = IngestionService(session, store)
    first_observation = datetime.now(UTC) - timedelta(days=40)
    first_result = CollectionResult(
        status=CollectionStatus.SUCCEEDED,
        items=[
            RawItem(
                external_type="record",
                external_id="1",
                payload={"id": "1", "value": "same"},
                observed_at=first_observation,
            )
        ],
        is_complete=True,
    )

    await service.discover(FakeConnector([first_result]), {"q": "test"})
    snapshot = session.scalar(select(RawSnapshot))
    assert snapshot is not None
    snapshot.retention_until = datetime.now(UTC) - timedelta(days=1)
    session.commit()

    purge = RetentionService(session, store).purge_expired(
        as_of=datetime.now(UTC),
        apply=True,
    )

    assert purge.purged_count == 1
    assert not store.exists(snapshot.object_storage_key)
    session.refresh(snapshot)
    assert snapshot.purged_at is not None

    observed_again_at = datetime.now(UTC)
    repeated_result = CollectionResult(
        status=CollectionStatus.SUCCEEDED,
        items=[
            RawItem(
                external_type="record",
                external_id="1",
                payload={"id": "1", "value": "same"},
                observed_at=observed_again_at,
            )
        ],
        is_complete=True,
    )
    outcome = await service.discover(
        FakeConnector([repeated_result]),
        {"q": "test"},
        resume=False,
    )

    session.refresh(snapshot)
    assert outcome.duplicate_item_count == 1
    assert session.scalar(select(func.count()).select_from(RawSnapshot)) == 1
    assert store.exists(snapshot.object_storage_key)
    assert snapshot.purged_at is None
    assert snapshot.retention_until is not None
    assert snapshot.retention_until.replace(tzinfo=UTC) >= (
        observed_again_at + timedelta(days=30)
    )


@pytest.mark.asyncio
async def test_later_page_failure_preserves_prior_page_and_checkpoint(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    checkpoint = {"cursor": "page-2"}
    connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("1", "kept")],
                checkpoint=checkpoint,
                is_complete=False,
            ),
            RuntimeError("upstream unavailable"),
        ]
    )

    outcome = await IngestionService(session, FileObjectStore(tmp_path)).discover(
        connector,
        {"q": "test"},
    )

    assert outcome.status == "partial"
    assert outcome.checkpoint == checkpoint
    assert outcome.request_count == 2
    assert outcome.response_count == 1
    assert outcome.raw_item_count == 1
    assert outcome.error_count == 1
    assert session.scalar(select(func.count()).select_from(RawSnapshot)) == 1
    assert session.scalar(select(func.count()).select_from(RequestRecord)) == 2


@pytest.mark.asyncio
async def test_rate_limit_is_recorded_without_losing_checkpoint(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    checkpoint = {"cursor": "page-2"}
    connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("1", "kept")],
                checkpoint=checkpoint,
                is_complete=False,
            ),
            CollectionResult(
                status=CollectionStatus.RATE_LIMITED,
                checkpoint=checkpoint,
                errors=["rate_limited"],
            ),
        ]
    )

    outcome = await IngestionService(session, FileObjectStore(tmp_path)).discover(
        connector,
        {"q": "test"},
    )

    assert outcome.status == "rate_limited"
    assert outcome.checkpoint == checkpoint
    assert outcome.raw_item_count == 1
    assert outcome.error_count == 1


def test_file_store_rejects_parent_path(tmp_path: Path) -> None:
    store = FileObjectStore(tmp_path)

    with pytest.raises(ValueError, match="safe relative path"):
        store.put_if_absent("../outside.json", b"{}")


@pytest.mark.asyncio
async def test_invalid_item_creates_quality_event_and_makes_run_partial(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    invalid_item = RawItem(
        external_type="record",
        external_id="",
        payload={"value": "unidentifiable"},
        observed_at=datetime.now(UTC),
    )
    connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[invalid_item],
                is_complete=True,
            )
        ]
    )

    outcome = await IngestionService(session, FileObjectStore(tmp_path)).discover(
        connector,
        {"q": "test"},
    )

    assert outcome.status == "partial"
    assert outcome.raw_item_count == 0
    event = session.scalar(select(DataQualityEvent))
    assert event is not None
    assert event.event_type == "missing_external_id"
    assert event.severity == "error"


@pytest.mark.asyncio
async def test_future_source_timestamp_creates_warning_without_dropping_item(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    observed_at = datetime.now(UTC)
    item = RawItem(
        external_type="record",
        external_id="future",
        payload={"value": "kept"},
        observed_at=observed_at,
        source_updated_at=observed_at + timedelta(days=2),
    )
    connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[item],
                is_complete=True,
            )
        ]
    )

    outcome = await IngestionService(session, FileObjectStore(tmp_path)).discover(
        connector,
        {"q": "test"},
    )

    assert outcome.status == "succeeded"
    assert outcome.raw_item_count == 1
    event = session.scalar(select(DataQualityEvent))
    assert event is not None
    assert event.event_type == "future_source_timestamp"
    assert event.details == {"field": "source_updated_at"}


@pytest.mark.asyncio
async def test_partial_collection_resumes_from_persisted_checkpoint(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    checkpoint = {"cursor": "page-2"}
    first_connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("1", "first")],
                checkpoint=checkpoint,
                is_complete=False,
                expected_total=2,
            ),
            RuntimeError("connection lost"),
        ]
    )
    service = IngestionService(session, FileObjectStore(tmp_path))

    first = await service.discover(first_connector, {"q": "resume"})

    assert first.status == "partial"
    persisted_checkpoint = session.scalar(select(IngestionCheckpoint))
    assert persisted_checkpoint is not None
    assert persisted_checkpoint.checkpoint == checkpoint
    assert persisted_checkpoint.is_complete is False

    second_connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                items=[raw_item("2", "second")],
                is_complete=True,
                expected_total=2,
            )
        ]
    )
    second = await service.discover(second_connector, {"q": "resume"})

    assert second.status == "succeeded"
    assert second_connector.checkpoints == [checkpoint]
    collection = session.scalar(select(IngestionCollection))
    assert collection is not None
    assert collection.is_complete is True
    assert collection.collected_total == 2
    assert collection.page_count == 2
    assert session.scalar(select(func.count()).select_from(CollectionPage)) == 2
    assert session.scalar(select(func.count()).select_from(IngestionRun)) == 2
    session.refresh(persisted_checkpoint)
    assert persisted_checkpoint.is_complete is True
    assert persisted_checkpoint.checkpoint is None


@pytest.mark.asyncio
async def test_new_optional_top_level_field_creates_quality_information(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    service = IngestionService(session, FileObjectStore(tmp_path))
    first_item = RawItem(
        external_type="record",
        external_id="1",
        payload={"id": "1", "value": "first"},
        observed_at=datetime.now(UTC),
    )
    changed_item = RawItem(
        external_type="record",
        external_id="2",
        payload={"id": "2", "value": "second", "new_field": True},
        observed_at=datetime.now(UTC),
    )
    incompatible_item = RawItem(
        external_type="record",
        external_id="3",
        payload={"id": "3", "value": {"nested": True}, "new_field": True},
        observed_at=datetime.now(UTC),
    )

    await service.discover(
        FakeConnector(
            [
                CollectionResult(
                    status=CollectionStatus.SUCCEEDED,
                    items=[first_item],
                    is_complete=True,
                )
            ]
        ),
        {"q": "schema"},
    )
    await service.discover(
        FakeConnector(
            [
                CollectionResult(
                    status=CollectionStatus.SUCCEEDED,
                    items=[changed_item],
                    is_complete=True,
                )
            ]
        ),
        {"q": "schema"},
        resume=False,
    )
    await service.discover(
        FakeConnector(
            [
                CollectionResult(
                    status=CollectionStatus.SUCCEEDED,
                    items=[incompatible_item],
                    is_complete=True,
                )
            ]
        ),
        {"q": "schema"},
        resume=False,
    )

    events = list(
        session.scalars(
            select(DataQualityEvent).where(
                DataQualityEvent.event_type == "source_schema_changed"
            )
        )
    )
    assert {event.severity for event in events} == {"info", "warning"}
    information = next(event for event in events if event.severity == "info")
    warning = next(event for event in events if event.severity == "warning")
    assert information.details["added_fields"] == ["new_field"]
    assert warning.details["type_changes"] == ["value"]


@pytest.mark.asyncio
async def test_terminal_incomplete_collection_is_not_auto_resumed(
    session: Session,
    tmp_path: Path,
) -> None:
    add_source(session)
    service = IngestionService(session, FileObjectStore(tmp_path))
    first_connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.PARTIAL,
                items=[raw_item("1", "capped")],
                is_complete=False,
                resume_available=False,
                completeness_reason="search_result_cap",
                expected_total=1_001,
                errors=["search_result_cap"],
            )
        ]
    )

    first = await service.discover(first_connector, {"q": "capped"})

    assert first.status == "partial"
    checkpoint = session.scalar(select(IngestionCheckpoint))
    assert checkpoint is not None
    assert checkpoint.resume_available is False

    second_connector = FakeConnector(
        [
            CollectionResult(
                status=CollectionStatus.SUCCEEDED,
                is_complete=True,
                expected_total=0,
            )
        ]
    )
    await service.discover(second_connector, {"q": "capped"})

    assert second_connector.checkpoints == [None]
    assert session.scalar(select(func.count()).select_from(IngestionCollection)) == 2
