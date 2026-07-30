from datetime import datetime

import httpx
import pytest

from firsat_radari.connectors.base import CollectionStatus
from firsat_radari.connectors.github import GitHubConnector


@pytest.mark.asyncio
async def test_discover_returns_checkpoint_and_rate_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "topic:testing"
        assert request.url.params["page"] == "1"
        return httpx.Response(
            200,
            headers={
                "x-ratelimit-remaining": "8",
                "x-ratelimit-reset": "1785342693",
            },
            json={
                "total_count": 2,
                "items": [
                    {
                        "id": 10,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.test",
    )
    connector = GitHubConnector(client=client)

    result = await connector.discover({"q": "topic:testing", "per_page": 1})

    assert result.status is CollectionStatus.SUCCEEDED
    assert result.is_complete is False
    assert result.checkpoint == {"page": 2}
    assert result.rate_limit_remaining == 8
    assert isinstance(result.rate_limit_reset_at, datetime)
    assert result.items[0].external_id == "10"
    await client.aclose()


@pytest.mark.asyncio
async def test_rate_limit_does_not_expose_response_body() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0"},
            json={"message": "secret upstream detail"},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.test",
    )
    connector = GitHubConnector(client=client)

    result = await connector.fetch("owner/repository")

    assert result.status is CollectionStatus.RATE_LIMITED
    assert result.errors == ["rate_limited"]
    await client.aclose()

