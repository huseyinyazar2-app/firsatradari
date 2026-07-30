from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import RawSnapshot
from firsat_radari.storage.base import ObjectStore


@dataclass(frozen=True)
class RetentionOutcome:
    considered_count: int
    purged_count: int
    missing_object_count: int
    error_count: int
    applied: bool
    as_of: datetime


class RetentionService:
    def __init__(self, session: Session, object_store: ObjectStore) -> None:
        self._session = session
        self._object_store = object_store

    def purge_expired(
        self,
        *,
        as_of: datetime,
        limit: int = 500,
        apply: bool = False,
    ) -> RetentionOutcome:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        cutoff = _as_utc(as_of)
        snapshots = list(
            self._session.scalars(
                select(RawSnapshot)
                .where(
                    RawSnapshot.retention_until.is_not(None),
                    RawSnapshot.retention_until < cutoff,
                    RawSnapshot.purged_at.is_(None),
                )
                .order_by(RawSnapshot.retention_until, RawSnapshot.id)
                .limit(limit)
            )
        )
        if not apply:
            return RetentionOutcome(
                considered_count=len(snapshots),
                purged_count=0,
                missing_object_count=0,
                error_count=0,
                applied=False,
                as_of=cutoff,
            )

        purged_count = 0
        missing_count = 0
        error_count = 0
        for snapshot in snapshots:
            try:
                existed = self._object_store.delete(
                    snapshot.object_storage_key
                )
                if not existed:
                    missing_count += 1
                snapshot.purged_at = cutoff
                self._session.commit()
                purged_count += 1
            except Exception:
                self._session.rollback()
                error_count += 1
        return RetentionOutcome(
            considered_count=len(snapshots),
            purged_count=purged_count,
            missing_object_count=missing_count,
            error_count=error_count,
            applied=True,
            as_of=cutoff,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
