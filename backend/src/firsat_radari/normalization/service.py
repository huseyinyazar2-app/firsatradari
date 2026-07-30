import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import (
    DataSource,
    IngestionRun,
    NormalizationRun,
    NormalizedDocument,
    RawSnapshot,
)
from firsat_radari.normalization.base import (
    NormalizationValidationError,
    SnapshotNormalizer,
)
from firsat_radari.storage.base import ObjectStore

_PERMITTED_DERIVED_STATUSES = frozenset({"allowed", "approved"})


class NormalizationPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizationOutcome:
    run_id: uuid.UUID
    status: str
    input_count: int
    success_count: int
    error_count: int


class NormalizationService:
    def __init__(self, session: Session, object_store: ObjectStore) -> None:
        self._session = session
        self._object_store = object_store

    def normalize_pending(
        self,
        normalizer: SnapshotNormalizer,
        *,
        limit: int = 100,
    ) -> NormalizationOutcome:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")

        source = self._session.scalar(
            select(DataSource).where(DataSource.key == normalizer.source_key)
        )
        self._enforce_policy(source, normalizer.source_key)
        run = NormalizationRun(
            source_id=source.id,
            normalizer_key=normalizer.key,
            normalizer_version=normalizer.version,
            status="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            input_count=0,
            success_count=0,
            error_count=0,
        )
        self._session.add(run)
        self._session.commit()

        already_normalized = exists().where(
            NormalizedDocument.snapshot_id == RawSnapshot.id,
            NormalizedDocument.normalizer_key == normalizer.key,
            NormalizedDocument.normalizer_version == normalizer.version,
        )
        snapshots = list(
            self._session.scalars(
                select(RawSnapshot)
                .where(
                    RawSnapshot.source_id == source.id,
                    RawSnapshot.external_type.in_(normalizer.supported_external_types),
                    RawSnapshot.purged_at.is_(None),
                    ~already_normalized,
                )
                .order_by(RawSnapshot.observed_at, RawSnapshot.id)
                .limit(limit)
            )
        )

        for snapshot in snapshots:
            run.input_count += 1
            had_successful_normalization = bool(
                self._session.scalar(
                    select(
                        exists().where(
                            NormalizedDocument.snapshot_id == snapshot.id,
                            NormalizedDocument.status == "succeeded",
                        )
                    )
                )
            )
            try:
                with self._session.begin_nested():
                    payload = self._load_payload(snapshot)
                    record = normalizer.normalize(
                        self._session,
                        source,
                        snapshot,
                        payload,
                    )
                    self._session.add(
                        NormalizedDocument(
                            normalization_run_id=run.id,
                            snapshot_id=snapshot.id,
                            entity_id=record.entity_id,
                            normalizer_key=normalizer.key,
                            normalizer_version=normalizer.version,
                            document_type=record.document_type,
                            schema_version=record.schema_version,
                            title=record.title,
                            body=record.body,
                            canonical_url=record.canonical_url,
                            language=record.language,
                            attributes=record.attributes,
                            source_created_at=record.source_created_at,
                            source_updated_at=record.source_updated_at,
                            normalized_at=datetime.now(UTC),
                            status="succeeded",
                            error_class=None,
                        )
                    )
                run.success_count += 1
                if not had_successful_normalization and snapshot.run_id is not None:
                    ingestion_run = self._session.get(IngestionRun, snapshot.run_id)
                    if ingestion_run is not None:
                        ingestion_run.normalized_item_count += 1
            except NormalizationValidationError as exc:
                run.error_count += 1
                self._session.add(
                    NormalizedDocument(
                        normalization_run_id=run.id,
                        snapshot_id=snapshot.id,
                        entity_id=None,
                        normalizer_key=normalizer.key,
                        normalizer_version=normalizer.version,
                        document_type=snapshot.external_type,
                        schema_version="1",
                        title=snapshot.external_id,
                        body=None,
                        canonical_url=None,
                        language=None,
                        attributes={},
                        source_created_at=snapshot.source_created_at,
                        source_updated_at=snapshot.source_updated_at,
                        normalized_at=datetime.now(UTC),
                        status="failed",
                        error_class=exc.error_class[:80],
                    )
                )
            except Exception:
                run.error_count += 1
                run.status = "partial" if run.success_count > 0 else "failed_transient"
                run.finished_at = datetime.now(UTC)
                self._session.commit()
                raise
            self._session.commit()

        if run.error_count == 0:
            run.status = "succeeded"
        elif run.success_count > 0:
            run.status = "partial"
        else:
            run.status = "failed_permanent"
        run.finished_at = datetime.now(UTC)
        self._session.commit()
        return NormalizationOutcome(
            run_id=run.id,
            status=run.status,
            input_count=run.input_count,
            success_count=run.success_count,
            error_count=run.error_count,
        )

    def _load_payload(self, snapshot: RawSnapshot) -> dict:
        content = self._object_store.read(snapshot.object_storage_key)
        if hashlib.sha256(content).hexdigest() != snapshot.content_hash:
            raise NormalizationValidationError("content_hash_mismatch")
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NormalizationValidationError("invalid_json") from exc
        if not isinstance(payload, dict):
            raise NormalizationValidationError("payload_not_object")
        return payload

    @staticmethod
    def _enforce_policy(source: DataSource | None, source_key: str) -> None:
        if source is None:
            raise NormalizationPolicyError(f"Source is not registered: {source_key}")
        if source.policy_status != "approved" or not source.policy_version:
            raise NormalizationPolicyError(f"Source policy is not approved: {source_key}")
        if source.derived_data_permission not in _PERMITTED_DERIVED_STATUSES:
            raise NormalizationPolicyError(f"Derived data is not permitted: {source_key}")
