from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx

from firsat_radari.connectors.base import (
    CollectionResult,
    CollectionStatus,
    ConnectorCapabilities,
    DataConnector,
    RawItem,
)

_QUESTION_FIELDS = frozenset(
    {
        "accepted_answer_id",
        "answer_count",
        "body",
        "bounty_amount",
        "bounty_closes_date",
        "closed_date",
        "closed_reason",
        "content_license",
        "creation_date",
        "is_answered",
        "last_activity_date",
        "last_edit_date",
        "link",
        "question_id",
        "score",
        "tags",
        "title",
        "view_count",
    }
)


class StackExchangeConnector(DataConnector):
    source_key = "stack_exchange"
    job_type = "stack_exchange_questions"
    version = "0.1.0"
    capabilities = ConnectorCapabilities(
        discovery=True,
        detail=True,
        incremental=True,
        historical=True,
        deletions=False,
        conditional_requests=False,
        pagination="page",
        rate_limit_headers=False,
        source_timestamps=True,
    )

    def __init__(
        self,
        key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._key = key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://api.stackexchange.com",
            headers={"User-Agent": "Firsat-Radari"},
            timeout=httpx.Timeout(20.0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def discover(
        self,
        query: dict[str, Any],
        checkpoint: dict[str, Any] | None = None,
    ) -> CollectionResult:
        page = int((checkpoint or {}).get("page", 1))
        params = _question_params(query, page=page)
        response = await self._get("/2.3/questions", params)
        if isinstance(response, CollectionResult):
            return response
        return _question_result(
            response,
            site=str(query["site"]),
            page=page,
        )

    async def fetch(self, external_id: str) -> CollectionResult:
        parsed = _parse_external_id(external_id)
        if parsed is None:
            return CollectionResult(
                status=CollectionStatus.FAILED_PERMANENT,
                is_complete=False,
                resume_available=False,
                errors=["invalid_stack_exchange_question_id"],
            )
        site, question_id = parsed
        response = await self._get(
            f"/2.3/questions/{question_id}",
            {
                "site": site,
                "filter": "withbody",
                **({"key": self._key} if self._key else {}),
            },
        )
        if isinstance(response, CollectionResult):
            return response
        result = _question_result(response, site=site, page=1)
        if not result.items and result.status is CollectionStatus.SUCCEEDED:
            return CollectionResult(
                status=CollectionStatus.FAILED_PERMANENT,
                is_complete=False,
                resume_available=False,
                rate_limit_remaining=result.rate_limit_remaining,
                errors=["question_not_found"],
            )
        return result

    async def _get(
        self,
        path: str,
        params: dict[str, Any],
    ) -> httpx.Response | CollectionResult:
        if self._key:
            params = {**params, "key": self._key}
        try:
            response = await self._client.get(path, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return CollectionResult(
                status=CollectionStatus.FAILED_TRANSIENT,
                is_complete=False,
                errors=[type(exc).__name__],
            )
        if response.status_code == 429:
            return CollectionResult(
                status=CollectionStatus.RATE_LIMITED,
                is_complete=False,
                errors=["rate_limited"],
            )
        if response.status_code >= 500:
            return CollectionResult(
                status=CollectionStatus.FAILED_TRANSIENT,
                is_complete=False,
                errors=[f"http_{response.status_code}"],
            )
        if response.status_code >= 400:
            error_name = _error_name(response)
            return CollectionResult(
                status=CollectionStatus.FAILED_PERMANENT,
                is_complete=False,
                resume_available=False,
                errors=[error_name or f"http_{response.status_code}"],
            )
        return response


def _question_params(query: dict[str, Any], *, page: int) -> dict[str, Any]:
    from_date = date.fromisoformat(str(query["from_date"]))
    to_date = date.fromisoformat(str(query["to_date"]))
    params: dict[str, Any] = {
        "site": query["site"],
        "tagged": ";".join(query["tags"]),
        "fromdate": int(
            datetime.combine(from_date, time.min, tzinfo=UTC).timestamp()
        ),
        "todate": int(
            datetime.combine(to_date, time.max, tzinfo=UTC).timestamp()
        ),
        "sort": query.get("sort", "creation"),
        "order": query.get("order", "asc"),
        "page": page,
        "pagesize": int(query.get("page_size", 100)),
        "filter": "withbody",
    }
    return params


def _question_result(
    response: httpx.Response,
    *,
    site: str,
    page: int,
) -> CollectionResult:
    payload = response.json()
    observed_at = datetime.now(UTC)
    items = [
        RawItem(
            external_type="stack_exchange_question",
            external_id=f"{site}:{item['question_id']}",
            payload={
                "site": site,
                **{
                    key: value
                    for key, value in item.items()
                    if key in _QUESTION_FIELDS
                },
            },
            observed_at=observed_at,
            source_created_at=_epoch_datetime(item.get("creation_date")),
            source_updated_at=_epoch_datetime(
                item.get("last_activity_date")
            ),
        )
        for item in payload.get("items", [])
        if isinstance(item, dict)
        and isinstance(item.get("question_id"), int)
    ]
    has_more = bool(payload.get("has_more", False))
    next_checkpoint = {"page": page + 1} if has_more else None
    remaining = _optional_nonnegative_int(payload.get("quota_remaining"))
    backoff = _optional_nonnegative_int(payload.get("backoff"))
    status = CollectionStatus.SUCCEEDED
    errors: list[str] = []
    reset_at = None
    if backoff is not None and backoff > 0:
        status = CollectionStatus.RATE_LIMITED
        errors.append("api_backoff")
        reset_at = observed_at + timedelta(seconds=backoff)
    elif remaining == 0 and has_more:
        status = CollectionStatus.RATE_LIMITED
        errors.append("quota_exhausted")
    return CollectionResult(
        status=status,
        items=items,
        checkpoint=next_checkpoint,
        is_complete=status is CollectionStatus.SUCCEEDED and not has_more,
        resume_available=True,
        rate_limit_remaining=remaining,
        rate_limit_reset_at=reset_at,
        errors=errors,
    )


def _epoch_datetime(value: Any) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _optional_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _parse_external_id(value: str) -> tuple[str, int] | None:
    site, separator, raw_question_id = value.partition(":")
    if not separator or not site or not raw_question_id.isdigit():
        return None
    question_id = int(raw_question_id)
    if question_id < 1:
        return None
    return site, question_id


def _error_name(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    value = payload.get("error_name")
    return value if isinstance(value, str) and value else None
