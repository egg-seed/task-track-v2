"""Exercise HTTPX transport, status errors and validation without external requests."""

import httpx
import pytest
from tutorials.httpx_client import UpstreamError, fetch_task


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_fetch_task_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tasks/7"
        return httpx.Response(200, json={"id": 7, "title": "sample"})

    async with httpx.AsyncClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(handler),
        timeout=3.0,
    ) as client:
        result = await fetch_task(client, 7)
    assert result.id == 7
    assert result.title == "sample"


@pytest.mark.anyio
async def test_fetch_task_upstream_error() -> None:
    async with httpx.AsyncClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    ) as client:
        with pytest.raises(UpstreamError, match="External API request failed"):
            await fetch_task(client, 7)


@pytest.mark.anyio
async def test_fetch_task_invalid_json_shape() -> None:
    async with httpx.AsyncClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "bad"})),
    ) as client:
        with pytest.raises(UpstreamError, match="External API response was invalid"):
            await fetch_task(client, 7)


@pytest.mark.anyio
async def test_fetch_task_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(
        base_url="https://example.invalid",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(UpstreamError, match="External API request failed"):
            await fetch_task(client, 7)
