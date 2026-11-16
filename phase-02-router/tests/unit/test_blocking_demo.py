"""The blocking demo endpoints answer; their timing is measured by blocking_load.py (Chapter 14)."""

import pytest
from fastapi.testclient import TestClient
from tutorials.blocking_demo import create_blocking_app


@pytest.mark.parametrize(
    ("path", "mode"),
    [
        ("/sync-sleep", "def + time.sleep"),
        ("/async-blocking", "async def + time.sleep"),
        ("/async-sleep", "async def + await asyncio.sleep"),
    ],
)
def test_each_endpoint_waits_and_answers(path: str, mode: str) -> None:
    with TestClient(create_blocking_app(wait_seconds=0)) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"mode": mode}


def test_health() -> None:
    with TestClient(create_blocking_app(wait_seconds=0)) as client:
        assert client.get("/health").json() == {"status": "ok"}
