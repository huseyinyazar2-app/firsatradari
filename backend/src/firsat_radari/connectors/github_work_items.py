from datetime import UTC, datetime
from typing import Any

from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    RawItem,
)
from firsat_radari.connectors.github import GitHubConnector, _parse_datetime


class GitHubWorkItemConnector(GitHubConnector):
    job_type = "github_work_items"
    version = "0.1.0"

    async def discover(
        self,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None = None,
    ) -> CollectionResult:
        page = int((checkpoint or {}).get("page", 1))
        per_page = min(int(query.get("per_page", 100)), 100)
        response = await self._get(
            "/search/issues",
            {
                "q": query["q"],
                "sort": query.get("sort", "updated"),
                "order": query.get("order", "desc"),
                "page": page,
                "per_page": per_page,
            },
        )
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        observed_at = datetime.now(UTC)
        items = [
            RawItem(
                external_type="repository_work_item",
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
        try:
            repository, number_text = external_id.rsplit("#", 1)
            number = int(number_text)
        except (ValueError, TypeError):
            return self._error_result(
                CollectionStatus.FAILED_PERMANENT,
                "invalid_work_item_external_id",
            )
        if not repository or repository.count("/") != 1 or number < 1:
            return self._error_result(
                CollectionStatus.FAILED_PERMANENT,
                "invalid_work_item_external_id",
            )
        response = await self._get(f"/repos/{repository}/issues/{number}")
        if isinstance(response, CollectionResult):
            return response

        payload = response.json()
        remaining, reset_at = self._rate_limit(response)
        return CollectionResult(
            status=CollectionStatus.SUCCEEDED,
            items=[
                RawItem(
                    external_type="repository_work_item",
                    external_id=str(payload["id"]),
                    payload=payload,
                    observed_at=datetime.now(UTC),
                    source_created_at=_parse_datetime(payload.get("created_at")),
                    source_updated_at=_parse_datetime(payload.get("updated_at")),
                )
            ],
            is_complete=True,
            expected_total=1,
            rate_limit_remaining=remaining,
            rate_limit_reset_at=reset_at,
        )
