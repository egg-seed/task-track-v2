"""The external wait demo answers, and awaiting lets calls overlap (Chapter 22)."""

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from tutorials.external_wait import (
    create_app,
    create_upstream_app,
    one_request,
    start_server,
    stop_server,
    three_requests,
)

WAIT = 0.3


@pytest.fixture
def upstream_url() -> Iterator[str]:
    server, thread, url = start_server(create_upstream_app(wait_seconds=WAIT))
    yield url
    stop_server(server, thread)


@pytest.fixture
def app_url(upstream_url: str) -> Iterator[str]:
    server, thread, url = start_server(create_app(upstream_url))
    yield url
    stop_server(server, thread)


@pytest.mark.parametrize("path", ["/blocking/7", "/threaded/7", "/awaiting/7"])
def test_single_call_endpoints_return_the_task(upstream_url: str, path: str) -> None:
    with TestClient(create_app(upstream_url)) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"id": 7, "title": "task 7"}


@pytest.mark.parametrize("path", ["/summary/one-by-one", "/summary/gather"])
def test_summary_endpoints_return_three_tasks(upstream_url: str, path: str) -> None:
    with TestClient(create_app(upstream_url)) as client:
        response = client.get(path)
    assert [task["id"] for task in response.json()] == [1, 2, 3]


def test_gather_overlaps_the_three_calls(app_url: str) -> None:
    async def run() -> tuple[float, float]:
        async with httpx.AsyncClient(base_url=app_url, timeout=10.0) as client:
            return (
                await one_request(client, "/summary/one-by-one"),
                await one_request(client, "/summary/gather"),
            )

    one_by_one, gathered = asyncio.run(run())
    assert one_by_one >= WAIT * 3
    assert gathered < WAIT * 2


def test_sync_client_in_async_def_delays_health(app_url: str) -> None:
    async def run(prefix: str) -> float:
        async with httpx.AsyncClient(base_url=app_url, timeout=10.0) as client:
            _, (_, health_end) = await three_requests(client, prefix)
            return health_end

    assert asyncio.run(run("/blocking")) >= WAIT * 2
    assert asyncio.run(run("/awaiting")) < WAIT
