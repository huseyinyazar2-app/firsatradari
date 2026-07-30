import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from firsat_radari.db.models import DataSource, RawSnapshot


class NormalizationValidationError(ValueError):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


@dataclass(frozen=True)
class NormalizedRecord:
    entity_id: uuid.UUID
    document_type: str
    title: str | None
    body: str | None
    canonical_url: str | None
    language: str | None
    attributes: dict[str, Any]
    source_created_at: datetime | None
    source_updated_at: datetime | None
    schema_version: str = "1"


class SnapshotNormalizer(ABC):
    source_key: str
    key: str
    version: str
    supported_external_types: frozenset[str]

    @abstractmethod
    def normalize(
        self,
        session: Session,
        source: DataSource,
        snapshot: RawSnapshot,
        payload: dict[str, Any],
    ) -> NormalizedRecord:
        raise NotImplementedError
