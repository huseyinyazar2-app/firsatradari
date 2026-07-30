from datetime import UTC, datetime
from typing import Any

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


class GitHubConnector(DataConnector):
    source_key = "github"
    version = "0.1.0"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=True,
        incremental=True,
        historical=False,
        deletions=False,
        conditional_requests=True,
        pagination="page",
        rate_limit_headers=True,
        source_timestamps=True,
    )

    def __init__(
        self,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Firsat-Radari",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(15.0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _rate_limit(response: httpx.Response) -> tuple[int | None, datetime | None]:
        remaining_header = response.headers.get("x-ratelimit-remaining")
        reset_header = response.headers.get("x-ratelimit-reset")
        remaining = int(remaining_header) if remaining_header else None
        reset_at = datetime.fromtimestamp(int(reset_header), tz=UTC) if reset_header else None
        return remaining, reset_at

    @staticmethod
    def _error_result(
        status: CollectionStatus,
        message: str,
        response: httpx.Response | None = None,
    ) -> CollectionResult:
        remaining = None
        reset_at = None
        if response is not None:
            remaining, reset_at = GitHubConnector._rate_limit(response)
        return CollectionResult(
            status=status,
            is_complete=False,
            rate_limit_remaining=remaining,
            rate_limit_reset_at=reset_at,
            errors=[message],
        )

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response | CollectionResult:
        try:
            response = await self._client.get(path, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return self._error_result(CollectionStatus.FAILED_TRANSIENT, type(exc).__name__)

        if response.status_code in {403, 429}:
            return self._error_result(CollectionStatus.RATE_LIMITED, "rate_limited", response)
        if response.status_code >= 500:
            return self._error_result(
                CollectionStatus.FAILED_TRANSIENT,
                f"http_{response.status_code}",
                response,
            )
        if response.status_code >= 400:
            return self._error_result(
                CollectionStatus.FAILED_PERMANENT,
                f"http_{response.status_code}",
                response,
            )
        return response

    async def discover(
        self,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None = None,
    ) -> CollectionResult:
        page = int((checkpoint or {}).get("page", 1))
        per_page = min(int(query.get("per_page", 100)), 100)
        params = {
            "q": query["q"],
            "sort": query.get("sort", "updated"),
            "order": query.get("order", "desc"),
            "page": page,
            "per_page": per_page,
        }
        response = await self._get("/search/repositories", params)
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        observed_at = datetime.now(UTC)
        items = [
            RawItem(
                external_type="repository",
                external_id=str(item["id"]),
                payload=item,
                observed_at=observed_at,
                source_created_at=_parse_datetime(item.get("created_at")),
                source_updated_at=_parse_datetime(item.get("updated_at")),
            )
            for item in payload.get("items", [])
        ]
        expected_total = int(payload.get("total_count", 0))
        accessible_total = min(expected_total, 1_000)
        collected_through = (page - 1) * per_page + len(items)
        reached_accessible_total = collected_through >= accessible_total
        truncated = expected_total > accessible_total
        incomplete_results = bool(payload.get("incomplete_results", False))
        status = CollectionStatus.SUCCEEDED
        checkpoint = None if reached_accessible_total else {"page": page + 1}
        is_complete = reached_accessible_total and not truncated and not incomplete_results
        resume_available = True
        completeness_reason = None
        errors: list[str] = []
        if incomplete_results:
            status = CollectionStatus.PARTIAL
            checkpoint = {"page": page}
            completeness_reason = "incomplete_search_results"
            errors = [completeness_reason]
        elif truncated and reached_accessible_total:
            status = CollectionStatus.PARTIAL
            checkpoint = None
            resume_available = False
            completeness_reason = "search_result_cap"
            errors = [completeness_reason]
        elif not items and not reached_accessible_total:
            status = CollectionStatus.PARTIAL
            checkpoint = None
            resume_available = False
            completeness_reason = "unexpected_empty_page"
            errors = [completeness_reason]
        remaining, reset_at = self._rate_limit(response)
        return CollectionResult(
            status=status,
            items=items,
            checkpoint=checkpoint,
            is_complete=is_complete,
            resume_available=resume_available,
            completeness_reason=completeness_reason,
            expected_total=expected_total,
            rate_limit_remaining=remaining,
            rate_limit_reset_at=reset_at,
            errors=errors,
        )

    async def fetch(self, external_id: str) -> CollectionResult:
        response = await self._get(f"/repos/{external_id}")
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        remaining, reset_at = self._rate_limit(response)
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=[
                RawItem(
                    external_type="repository",
                    external_id=str(payload["id"]),
                    payload=payload,
                    observed_at=datetime.now(UTC),
                    source_created_at=_parse_datetime(payload.get("created_at")),
                    source_updated_at=_parse_datetime(payload.get("updated_at")),
                )
            ],
            is_complete=True,
            rate_limit_remaining=remaining,
            rate_limit_reset_at=reset_at,
        )
