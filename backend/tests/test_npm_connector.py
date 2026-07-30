import httpx
import pytest

from firsat_radari.connectors.base import CollectionStatus
from firsat_radari.connectors.npm import NpmConnector


@pytest.mark.asyncio
async def test_search_uses_offset_checkpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["from"] == "20"
        return httpx.Response(
            200,
            json={
                "total": 25,
                "objects": [
                    {
                        "package": {
                            "name": "example-package",
                            "date": "2026-07-01T00:00:00Z",
                        }
                    }
                ],
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://registry.npm.test",
    )
    connector = NpmConnector(client=client)

    result = await connector.discover(
        {"text": "testing", "size": 20},
        checkpoint={"offset": 20},
    )

    assert result.status is CollectionStatus.SUCCEEDED
    assert result.checkpoint == {"offset": 21}
    assert result.items[0].external_id == "example-package"
    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_encodes_scoped_package_name() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path == b"/%40scope%2Fpackage"
        return httpx.Response(
            200,
            json={
                "_id": "@scope/package",
                "time": {
                    "created": "2025-01-01T00:00:00Z",
                    "modified": "2026-01-01T00:00:00Z",
                },
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://registry.npm.test",
    )
    connector = NpmConnector(client=client)

    result = await connector.fetch("@scope/package")

    assert result.status is CollectionStatus.SUCCEEDED
    assert result.is_complete is True
    assert result.items[0].external_id == "@scope/package"
    await client.aclose()

