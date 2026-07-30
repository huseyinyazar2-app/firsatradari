import httpx
import pytest

from firsat_radari.connectors.base import CollectionStatus
from firsat_radari.connectors.github_work_items import GitHubWorkItemConnector


@pytest.mark.asyncio
async def test_work_item_search_keeps_issue_and_pull_request_payloads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/issues"
        assert request.url.params["q"] == "repo:example/radar is:open"
        return httpx.Response(
            200,
            headers={"x-ratelimit-remaining": "7"},
            json={
                "total_count": 2,
                "items": [
                    {
                        "id": 10,
                        "number": 1,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                    },
                    {
                        "id": 11,
                        "number": 2,
                        "pull_request": {
                            "url": "https://api.github.test/repos/example/radar/pulls/2"
                        },
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                    },
                ],
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.test",
    )
    connector = GitHubWorkItemConnector(client=client)

    result = await connector.discover(
        {
            "q": "repo:example/radar is:open",
            "per_page": 100,
        }
    )

    assert result.status is CollectionStatus.SUCCEEDED
    assert result.is_complete is True
    assert result.expected_total == 2
    assert len(result.items) == 2
    assert "pull_request" not in result.items[0].payload
    assert "pull_request" in result.items[1].payload
    await client.aclose()


@pytest.mark.asyncio
async def test_work_item_fetch_rejects_noncanonical_identifier() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
        base_url="https://api.github.test",
    )
    connector = GitHubWorkItemConnector(client=client)

    result = await connector.fetch("invalid")

    assert result.status is CollectionStatus.FAILED_PERMANENT
    assert result.errors == ["invalid_work_item_external_id"]
    await client.aclose()


@pytest.mark.asyncio
async def test_search_result_cap_is_never_reported_as_complete() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 1_001,
                "items": [
                    {
                        "id": item_id,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                    }
                    for item_id in range(100)
                ],
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.test",
    )
    connector = GitHubWorkItemConnector(client=client)

    result = await connector.discover(
        {"q": "is:open", "per_page": 100},
        checkpoint={"page": 10},
    )

    assert result.status is CollectionStatus.PARTIAL
    assert result.is_complete is False
    assert result.resume_available is False
    assert result.completeness_reason == "search_result_cap"
    assert result.expected_total == 1_001
    assert result.checkpoint is None
    await client.aclose()
