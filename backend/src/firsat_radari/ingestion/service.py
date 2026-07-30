import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    DataConnector,
    RawItem,
)
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
    SourceSchemaProfile,
)
from firsat_radari.ingestion.errors import SourcePolicyError
from firsat_radari.storage.base import ObjectStore

_PERMITTED_STORAGE_STATUSES = frozenset({"allowed", "approved"})


@dataclass(frozen=True)
class IngestionOutcome:
    run_id: uuid.UUID
    status: str
    request_count: int
    response_count: int
    raw_item_count: int
    duplicate_item_count: int
    error_count: int
    checkpoint: dict[str, Any] | None


class IngestionService:
    def __init__(self, session: Session, object_store: ObjectStore) -> None:
        self._session = session
        self._object_store = object_store

    async def discover(
        self,
        connector: DataConnector,
        query: dict[str, Any],
        *,
        checkpoint: dict[str, Any] | None = None,
        resume: bool = True,
        max_pages: int = 100,
    ) -> IngestionOutcome:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        source = self._session.scalar(
            select(DataSource).where(DataSource.key == connector.source_key)
        )
        self._enforce_source_policy(source, connector.source_key)

        query_fingerprint = _query_fingerprint(
            connector.source_key,
            connector.job_type,
            query,
        )
        saved_checkpoint = self._session.scalar(
            select(IngestionCheckpoint).where(
                IngestionCheckpoint.source_id == source.id,
                IngestionCheckpoint.job_type == connector.job_type,
                IngestionCheckpoint.query_fingerprint == query_fingerprint,
            )
        )
        effective_checkpoint = checkpoint
        collection = None
        checkpoint_version_mismatch = False
        if (
            resume
            and saved_checkpoint is not None
            and not saved_checkpoint.is_complete
            and saved_checkpoint.resume_available
            and (checkpoint is None or checkpoint == saved_checkpoint.checkpoint)
        ):
            if saved_checkpoint.connector_version == connector.version:
                effective_checkpoint = saved_checkpoint.checkpoint
                collection = self._session.get(
                    IngestionCollection,
                    saved_checkpoint.collection_id,
                )
            else:
                checkpoint_version_mismatch = True

        if collection is None:
            collection = IngestionCollection(
                source_id=source.id,
                job_type=connector.job_type,
                query_fingerprint=query_fingerprint,
                query_definition=query,
                status="running",
                started_at=datetime.now(UTC),
                completed_at=None,
                expected_total=None,
                collected_total=0,
                page_count=0,
                is_complete=False,
                resume_available=True,
                completeness_reason=None,
            )
            self._session.add(collection)
            self._session.flush()

        run = IngestionRun(
            source_id=source.id,
            collection_id=collection.id,
            connector_version=connector.version,
            job_type=connector.job_type,
            query_definition=query,
            query_fingerprint=query_fingerprint,
            status="running",
            checkpoint_before=effective_checkpoint,
            checkpoint_after=effective_checkpoint,
            started_at=datetime.now(UTC),
            request_count=0,
            response_count=0,
            raw_item_count=0,
            normalized_item_count=0,
            duplicate_item_count=0,
            error_count=0,
            estimated_cost=Decimal("0"),
        )
        self._session.add(run)
        self._session.commit()

        if checkpoint_version_mismatch:
            self._record_run_event(
                source=source,
                run=run,
                event_type="checkpoint_version_mismatch",
                severity="warning",
                details={
                    "current_connector_version": connector.version,
                    "saved_connector_version": saved_checkpoint.connector_version,
                },
            )

        current_checkpoint = effective_checkpoint
        terminal_status = "partial"
        for page_number in range(1, max_pages + 1):
            requested_at = datetime.now(UTC)
            try:
                result = await connector.discover(query, current_checkpoint)
            except Exception:
                self._record_connector_exception(
                    run=run,
                    connector=connector,
                    query=query,
                    checkpoint=current_checkpoint,
                    requested_at=requested_at,
                    page_number=page_number,
                )
                saved_checkpoint = self._save_checkpoint(
                    existing=saved_checkpoint,
                    source=source,
                    collection=collection,
                    run=run,
                    connector=connector,
                    query_fingerprint=query_fingerprint,
                    checkpoint=current_checkpoint,
                    is_complete=False,
                    resume_available=True,
                )
                collection.completeness_reason = "connector_exception"
                terminal_status = "partial" if run.raw_item_count > 0 else "failed_transient"
                break

            had_prior_items = run.raw_item_count > 0
            next_checkpoint = result.checkpoint
            if (
                result.status is not CollectionStatus.SUCCEEDED
                and result.resume_available
                and next_checkpoint is None
            ):
                next_checkpoint = current_checkpoint
            self._record_request(
                run=run,
                connector=connector,
                query=query,
                checkpoint=current_checkpoint,
                requested_at=requested_at,
                result=result,
                page_number=page_number,
            )
            self._persist_items(source, run, result.items)
            self._record_collection_page(
                source=source,
                collection=collection,
                run=run,
                cursor_in=current_checkpoint,
                cursor_out=next_checkpoint,
                result=result,
            )
            run.checkpoint_after = next_checkpoint
            saved_checkpoint = self._save_checkpoint(
                existing=saved_checkpoint,
                source=source,
                collection=collection,
                run=run,
                connector=connector,
                query_fingerprint=query_fingerprint,
                checkpoint=next_checkpoint,
                is_complete=(result.status is CollectionStatus.SUCCEEDED and result.is_complete),
                resume_available=result.resume_available,
            )
            if result.status is CollectionStatus.SUCCEEDED:
                run.error_count += len(result.errors)
            else:
                run.error_count += max(1, len(result.errors))
            self._session.commit()

            if result.status is not CollectionStatus.SUCCEEDED:
                if result.status in {
                    CollectionStatus.FAILED_TRANSIENT,
                    CollectionStatus.FAILED_PERMANENT,
                } and (had_prior_items or bool(result.items)):
                    terminal_status = "partial"
                else:
                    terminal_status = result.status.value
                break
            if result.is_complete:
                terminal_status = "succeeded"
                break
            if next_checkpoint is None or next_checkpoint == current_checkpoint:
                run.error_count += 1
                terminal_status = "partial"
                break

            current_checkpoint = next_checkpoint
        else:
            terminal_status = "partial"

        if terminal_status == "succeeded" and run.error_count > 0:
            terminal_status = "partial"
        self._record_run_quality(source, run)
        run.status = terminal_status
        run.finished_at = datetime.now(UTC)
        collection.status = terminal_status
        collection.is_complete = terminal_status == "succeeded"
        if terminal_status == "failed_permanent":
            collection.resume_available = False
            collection.completeness_reason = collection.completeness_reason or "failed_permanent"
        if collection.is_complete:
            collection.resume_available = False
            collection.completeness_reason = None
        collection.completed_at = (
            run.finished_at if collection.is_complete or not collection.resume_available else None
        )
        self._save_checkpoint(
            existing=saved_checkpoint,
            source=source,
            collection=collection,
            run=run,
            connector=connector,
            query_fingerprint=query_fingerprint,
            checkpoint=None if collection.is_complete else run.checkpoint_after,
            is_complete=collection.is_complete,
            resume_available=collection.resume_available,
        )
        self._session.commit()
        return self._outcome(run)

    @staticmethod
    def _enforce_source_policy(source: DataSource | None, source_key: str) -> None:
        if source is None:
            raise SourcePolicyError(f"Source is not registered: {source_key}")
        if not source.enabled:
            raise SourcePolicyError(f"Source is disabled: {source_key}")
        if source.policy_status != "approved":
            raise SourcePolicyError(f"Source policy is not approved: {source_key}")
        if not source.policy_version:
            raise SourcePolicyError(f"Source policy version is missing: {source_key}")
        if source.storage_permission not in _PERMITTED_STORAGE_STATUSES:
            raise SourcePolicyError(f"Raw storage is not permitted: {source_key}")
        if source.retention_days is None or source.retention_days < 1:
            raise SourcePolicyError(f"Source retention policy is missing: {source_key}")

    def _persist_items(
        self,
        source: DataSource,
        run: IngestionRun,
        items: list[RawItem],
    ) -> None:
        for item in items:
            if not isinstance(item.external_type, str) or not item.external_type.strip():
                run.error_count += 1
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="missing_external_type",
                    severity="error",
                )
                continue
            if not isinstance(item.external_id, str) or not item.external_id.strip():
                run.error_count += 1
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="missing_external_id",
                    severity="error",
                )
                continue
            if len(item.external_type) > 80 or len(item.external_id) > 300:
                run.error_count += 1
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="identity_field_too_long",
                    severity="error",
                )
                continue
            if not item.payload:
                run.error_count += 1
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="empty_payload",
                    severity="error",
                )
                continue

            try:
                if not all(isinstance(key, str) for key in item.payload):
                    raise TypeError
                content = _canonical_json(item.payload)
            except (TypeError, ValueError):
                run.error_count += 1
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="non_json_payload",
                    severity="error",
                )
                continue
            self._record_timestamp_quality(source, run, item)
            schema_hint = self._record_schema_quality(source, run, item)
            content_hash = hashlib.sha256(content).hexdigest()
            existing_id = self._session.scalar(
                select(RawSnapshot.id).where(
                    RawSnapshot.source_id == source.id,
                    RawSnapshot.external_type == item.external_type,
                    RawSnapshot.external_id == item.external_id,
                    RawSnapshot.content_hash == content_hash,
                )
            )
            if existing_id is not None:
                self._record_snapshot_observation(
                    source=source,
                    run=run,
                    snapshot_id=existing_id,
                    observed_at=item.observed_at,
                    is_duplicate=True,
                )
                run.duplicate_item_count += 1
                continue

            object_key = _object_key(
                source.key,
                item.external_type,
                item.external_id,
                content_hash,
            )
            self._object_store.put_if_absent(object_key, content)
            snapshot_id = uuid.uuid4()
            self._session.add(
                RawSnapshot(
                    id=snapshot_id,
                    source_id=source.id,
                    run_id=run.id,
                    collection_id=run.collection_id,
                    external_type=item.external_type,
                    external_id=item.external_id,
                    observed_at=item.observed_at,
                    source_created_at=item.source_created_at,
                    source_updated_at=item.source_updated_at,
                    content_hash=content_hash,
                    object_storage_key=object_key,
                    media_type="application/json",
                    schema_hint=schema_hint,
                    policy_version=source.policy_version,
                    retention_until=item.observed_at + timedelta(days=source.retention_days),
                    is_deleted_at_source=False,
                )
            )
            self._record_snapshot_observation(
                source=source,
                run=run,
                snapshot_id=snapshot_id,
                observed_at=item.observed_at,
                is_duplicate=False,
            )
            run.raw_item_count += 1

    def _record_snapshot_observation(
        self,
        *,
        source: DataSource,
        run: IngestionRun,
        snapshot_id: uuid.UUID,
        observed_at: datetime,
        is_duplicate: bool,
    ) -> None:
        if run.collection_id is None:
            raise RuntimeError("Ingestion run is missing its collection")
        existing_id = self._session.scalar(
            select(RawSnapshotObservation.id).where(
                RawSnapshotObservation.collection_id == run.collection_id,
                RawSnapshotObservation.snapshot_id == snapshot_id,
            )
        )
        if existing_id is not None:
            return
        self._session.add(
            RawSnapshotObservation(
                snapshot_id=snapshot_id,
                source_id=source.id,
                run_id=run.id,
                collection_id=run.collection_id,
                observed_at=observed_at,
                is_duplicate=is_duplicate,
            )
        )

    def _record_schema_quality(
        self,
        source: DataSource,
        run: IngestionRun,
        item: RawItem,
    ) -> str:
        schema = {key: _json_type(value) for key, value in sorted(item.payload.items())}
        fingerprint = hashlib.sha256(_canonical_json(schema)).hexdigest()
        profile = self._session.scalar(
            select(SourceSchemaProfile).where(
                SourceSchemaProfile.source_id == source.id,
                SourceSchemaProfile.external_type == item.external_type,
                SourceSchemaProfile.fingerprint == fingerprint,
            )
        )
        if profile is not None:
            profile.last_seen_at = item.observed_at
            profile.observation_count += 1
            return fingerprint

        previous = self._session.scalar(
            select(SourceSchemaProfile)
            .where(
                SourceSchemaProfile.source_id == source.id,
                SourceSchemaProfile.external_type == item.external_type,
            )
            .order_by(SourceSchemaProfile.last_seen_at.desc())
            .limit(1)
        )
        self._session.add(
            SourceSchemaProfile(
                source_id=source.id,
                external_type=item.external_type,
                fingerprint=fingerprint,
                top_level_schema=schema,
                first_seen_at=item.observed_at,
                last_seen_at=item.observed_at,
                observation_count=1,
            )
        )
        if previous is not None:
            previous_schema = previous.top_level_schema
            current_keys = set(schema)
            previous_keys = set(previous_schema)
            type_changes = sorted(
                key
                for key in current_keys & previous_keys
                if not _json_types_compatible(
                    schema[key],
                    previous_schema[key],
                )
            )
            self._record_quality_event(
                source=source,
                run=run,
                item=item,
                event_type="source_schema_changed",
                severity="warning" if type_changes else "info",
                details={
                    "added_fields": sorted(current_keys - previous_keys),
                    "removed_fields": sorted(previous_keys - current_keys),
                    "type_changes": type_changes,
                    "previous_fingerprint": previous.fingerprint,
                    "current_fingerprint": fingerprint,
                },
            )
        return fingerprint

    def _record_collection_page(
        self,
        *,
        source: DataSource,
        collection: IngestionCollection,
        run: IngestionRun,
        cursor_in: dict[str, Any] | None,
        cursor_out: dict[str, Any] | None,
        result: CollectionResult,
    ) -> None:
        if (
            collection.expected_total is not None
            and result.expected_total is not None
            and collection.expected_total != result.expected_total
        ):
            self._record_run_event(
                source=source,
                run=run,
                event_type="expected_total_changed",
                severity="warning",
                details={
                    "previous_total": collection.expected_total,
                    "current_total": result.expected_total,
                },
            )
        if result.expected_total is not None:
            collection.expected_total = result.expected_total
        collection.resume_available = result.resume_available
        collection.completeness_reason = result.completeness_reason
        collection.page_count += 1
        collection.collected_total += len(result.items)
        self._session.add(
            CollectionPage(
                collection_id=collection.id,
                run_id=run.id,
                page_number=collection.page_count,
                status=result.status.value,
                cursor_in=cursor_in,
                cursor_out=cursor_out,
                items_returned=len(result.items),
                is_last_page=result.is_complete,
                is_complete=(result.status is CollectionStatus.SUCCEEDED and result.is_complete),
                resume_available=result.resume_available,
                completeness_reason=result.completeness_reason,
                expected_total=result.expected_total,
                collected_total=collection.collected_total,
                observed_at=datetime.now(UTC),
            )
        )

    def _save_checkpoint(
        self,
        *,
        existing: IngestionCheckpoint | None,
        source: DataSource,
        collection: IngestionCollection,
        run: IngestionRun,
        connector: DataConnector,
        query_fingerprint: str,
        checkpoint: dict[str, Any] | None,
        is_complete: bool,
        resume_available: bool,
    ) -> IngestionCheckpoint:
        checkpoint_record = existing
        if checkpoint_record is None:
            checkpoint_record = IngestionCheckpoint(
                source_id=source.id,
                collection_id=collection.id,
                last_run_id=run.id,
                job_type=connector.job_type,
                query_fingerprint=query_fingerprint,
                connector_version=connector.version,
                checkpoint=checkpoint,
                is_complete=is_complete,
                resume_available=resume_available,
                updated_at=datetime.now(UTC),
            )
            self._session.add(checkpoint_record)
            return checkpoint_record

        checkpoint_record.collection_id = collection.id
        checkpoint_record.last_run_id = run.id
        checkpoint_record.connector_version = connector.version
        checkpoint_record.checkpoint = checkpoint
        checkpoint_record.is_complete = is_complete
        checkpoint_record.resume_available = resume_available
        checkpoint_record.updated_at = datetime.now(UTC)
        return checkpoint_record

    def _record_timestamp_quality(
        self,
        source: DataSource,
        run: IngestionRun,
        item: RawItem,
    ) -> None:
        future_limit = _as_utc(item.observed_at) + timedelta(days=1)
        timestamp_fields = (
            ("source_created_at", item.source_created_at),
            ("source_updated_at", item.source_updated_at),
        )
        for field_name, value in timestamp_fields:
            if value is not None and _as_utc(value) > future_limit:
                self._record_quality_event(
                    source=source,
                    run=run,
                    item=item,
                    event_type="future_source_timestamp",
                    severity="warning",
                    details={"field": field_name},
                )

        if (
            item.source_created_at is not None
            and item.source_updated_at is not None
            and _as_utc(item.source_updated_at) < _as_utc(item.source_created_at)
        ):
            self._record_quality_event(
                source=source,
                run=run,
                item=item,
                event_type="inverted_source_timestamps",
                severity="warning",
            )

    def _record_run_quality(self, source: DataSource, run: IngestionRun) -> None:
        total_items = run.raw_item_count + run.duplicate_item_count
        if total_items < 10:
            return
        duplicate_ratio = run.duplicate_item_count / total_items
        if duplicate_ratio >= 0.8:
            self._session.add(
                DataQualityEvent(
                    run_id=run.id,
                    source_id=source.id,
                    snapshot_id=None,
                    event_type="excessive_duplicates",
                    severity="warning",
                    external_type=None,
                    external_id=None,
                    details={
                        "duplicate_count": run.duplicate_item_count,
                        "item_count": total_items,
                        "ratio": round(duplicate_ratio, 4),
                    },
                    observed_at=datetime.now(UTC),
                    resolved_at=None,
                )
            )

    def _record_run_event(
        self,
        *,
        source: DataSource,
        run: IngestionRun,
        event_type: str,
        severity: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            DataQualityEvent(
                run_id=run.id,
                source_id=source.id,
                snapshot_id=None,
                event_type=event_type,
                severity=severity,
                external_type=None,
                external_id=None,
                details=details or {},
                observed_at=datetime.now(UTC),
                resolved_at=None,
            )
        )

    def _record_quality_event(
        self,
        *,
        source: DataSource,
        run: IngestionRun,
        item: RawItem,
        event_type: str,
        severity: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            DataQualityEvent(
                run_id=run.id,
                source_id=source.id,
                snapshot_id=None,
                event_type=event_type,
                severity=severity,
                external_type=(
                    item.external_type[:80]
                    if isinstance(item.external_type, str) and item.external_type
                    else None
                ),
                external_id=(
                    item.external_id[:300]
                    if isinstance(item.external_id, str) and item.external_id
                    else None
                ),
                details=details or {},
                observed_at=datetime.now(UTC),
                resolved_at=None,
            )
        )

    def _record_request(
        self,
        *,
        run: IngestionRun,
        connector: DataConnector,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None,
        requested_at: datetime,
        result: CollectionResult,
        page_number: int,
    ) -> None:
        run.request_count += 1
        run.response_count += 1
        self._session.add(
            RequestRecord(
                run_id=run.id,
                endpoint_key=connector.job_type,
                request_fingerprint=_request_fingerprint(
                    connector.source_key,
                    connector.version,
                    query,
                    checkpoint,
                ),
                requested_at=requested_at,
                response_at=datetime.now(UTC),
                http_status=None,
                etag=None,
                rate_limit_limit=None,
                rate_limit_remaining=result.rate_limit_remaining,
                rate_limit_reset_at=result.rate_limit_reset_at,
                retry_after_seconds=None,
                attempt_number=page_number,
                error_class=result.errors[0][:50] if result.errors else None,
            )
        )

    def _record_connector_exception(
        self,
        *,
        run: IngestionRun,
        connector: DataConnector,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None,
        requested_at: datetime,
        page_number: int,
    ) -> None:
        run.request_count += 1
        run.error_count += 1
        self._session.add(
            RequestRecord(
                run_id=run.id,
                endpoint_key=connector.job_type,
                request_fingerprint=_request_fingerprint(
                    connector.source_key,
                    connector.version,
                    query,
                    checkpoint,
                ),
                requested_at=requested_at,
                response_at=None,
                http_status=None,
                etag=None,
                rate_limit_limit=None,
                rate_limit_remaining=None,
                rate_limit_reset_at=None,
                retry_after_seconds=None,
                attempt_number=page_number,
                error_class="connector_exception",
            )
        )
        self._session.commit()

    @staticmethod
    def _outcome(run: IngestionRun) -> IngestionOutcome:
        return IngestionOutcome(
            run_id=run.id,
            status=run.status,
            request_count=run.request_count,
            response_count=run.response_count,
            raw_item_count=run.raw_item_count,
            duplicate_item_count=run.duplicate_item_count,
            error_count=run.error_count,
            checkpoint=run.checkpoint_after,
        )


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_types_compatible(current: str, previous: str) -> bool:
    return current == previous or "null" in {current, previous}


def _query_fingerprint(
    source_key: str,
    job_type: str,
    query: dict[str, Any],
) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "job_type": job_type,
                "query": query,
                "source_key": source_key,
            }
        )
    ).hexdigest()


def _request_fingerprint(
    source_key: str,
    connector_version: str,
    query: dict[str, Any],
    checkpoint: dict[str, Any] | None,
) -> str:
    content = _canonical_json(
        {
            "checkpoint": checkpoint,
            "connector_version": connector_version,
            "query": query,
            "source_key": source_key,
        }
    )
    return hashlib.sha256(content).hexdigest()


def _object_key(
    source_key: str,
    external_type: str,
    external_id: str,
    content_hash: str,
) -> str:
    identity = "\0".join((source_key, external_type, external_id)).encode()
    identity_hash = hashlib.sha256(identity).hexdigest()
    return f"{identity_hash}/{content_hash}.json"
