from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class NpmConnector(DataConnector):
    source_key = "npm"
    version = "0.1.0"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=True,
        incremental=False,
        historical=True,
        deletions=False,
        conditional_requests=True,
        pagination="offset",
        rate_limit_headers=False,
        source_timestamps=True,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://registry.npmjs.org",
            headers={"User-Agent": "Firsat-Radari"},
            timeout=httpx.Timeout(15.0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _error_result(status: CollectionStatus, message: str) -> CollectionResult:
        return CollectionResult(status=status, is_complete=False, errors=[message])

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response | CollectionResult:
        try:
            response = await self._client.get(path, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return self._error_result(CollectionStatus.FAILED_TRANSIENT, type(exc).__name__)

        if response.status_code == 429:
            return self._error_result(CollectionStatus.RATE_LIMITED, "rate_limited")
        if response.status_code >= 500:
            return self._error_result(
                CollectionStatus.FAILED_TRANSIENT, f"http_{response.status_code}"
            )
        if response.status_code >= 400:
            return self._error_result(
                CollectionStatus.FAILED_PERMANENT, f"http_{response.status_code}"
            )
        return response

    async def discover(
        self,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None = None,
    ) -> CollectionResult:
        offset = int((checkpoint or {}).get("offset", 0))
        size = min(int(query.get("size", 100)), 250)
        response = await self._get(
            "/-/v1/search",
            {"text": query["text"], "size": size, "from": offset},
        )
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        observed_at = datetime.now(UTC)
        objects = payload.get("objects", [])
        items = [
            RawItem(
                external_type="package_search_result",
                external_id=item["package"]["name"],
                payload=item,
                observed_at=observed_at,
                source_updated_at=_parse_datetime(item["package"].get("date")),
            )
            for item in objects
        ]
        total = int(payload.get("total", 0))
        next_offset = offset + len(items)
        is_complete = not items or next_offset >= total
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=items,
            checkpoint=None if is_complete else {"offset": next_offset},
            is_complete=is_complete,
            expected_total=total,
        )

    async def fetch(self, external_id: str) -> CollectionResult:
        response = await self._get(f"/{quote(external_id, safe='')}")
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        time_data = payload.get("time", {})
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=[
                RawItem(
                    external_type="package",
                    external_id=payload["_id"],
                    payload=payload,
                    observed_at=datetime.now(UTC),
                    source_created_at=_parse_datetime(time_data.get("created")),
                    source_updated_at=_parse_datetime(time_data.get("modified")),
                )
            ],
            is_complete=True,
        )
