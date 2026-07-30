from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CollectionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    RATE_LIMITED = "rate_limited"
    FAILED_TRANSIENT = "failed_transient"
    FAILED_PERMANENT = "failed_permanent"


@dataclass(frozen=True)
class ConnectorCapabilities:
    discovery: bool
    detail: bool
    incremental: bool
    historical: bool
    deletions: bool
    conditional_requests: bool
    pagination: str
    rate_limit_headers: bool
    source_timestamps: bool


@dataclass(frozen=True)
class RawItem:
    external_type: str
    external_id: str
    payload: dict[str, Any]
    observed_at: datetime
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None


@dataclass(frozen=True)
class CollectionResult:
    status: CollectionStatus
    items: list[RawItem] = field(default_factory=list)
    checkpoint: dict[str, Any] | None = None
    is_complete: bool = False
    resume_available: bool = True
    completeness_reason: str | None = None
    expected_total: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset_at: datetime | None = None
    errors: list[str] = field(default_factory=list)


class DataConnector(ABC):
    source_key: str
    job_type: str = "discovery"
    version: str
    capabilities: ConnectorCapabilities

    @abstractmethod
    async def discover(
        self,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None = None,
    ) -> CollectionResult:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, external_id: str) -> CollectionResult:
        raise NotImplementedError
