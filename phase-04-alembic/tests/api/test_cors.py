"""The Kanban frontend runs on another origin (port 5173) and calls this API (Chapter 20)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.main import create_app

FRONTEND = "http://localhost:5173"


def preflight(client: TestClient, origin: str, method: str) -> dict[str, str]:
    response = client.options(
        "/tasks/00000000-0000-4000-8000-000000000000",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    return {"status": str(response.status_code), **response.headers}


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_preflight_allows_frontend(client: TestClient, method: str) -> None:
    headers = preflight(client, FRONTEND, method)
    assert headers["status"] == "200"
    assert headers["access-control-allow-origin"] == FRONTEND
    assert method in headers["access-control-allow-methods"]


def test_response_exposes_request_id_to_frontend(client: TestClient) -> None:
    response = client.get("/tasks", headers={"Origin": FRONTEND})
    assert response.headers["access-control-allow-origin"] == FRONTEND
    # Without this, browser JavaScript cannot read X-Request-ID (Chapter 31).
    assert response.headers["access-control-expose-headers"] == "X-Request-ID"


def test_other_origins_are_not_allowed(client: TestClient) -> None:
    headers = preflight(client, "https://evil.example", "DELETE")
    assert headers["status"] == "400"
    assert "access-control-allow-origin" not in headers
    response = client.get("/tasks", headers={"Origin": "https://evil.example"})
    # The API still answers; the browser hides the body from the other site's JavaScript.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_origins_come_from_settings(test_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKS_CORS_ORIGINS", '["https://kanban.example.com"]')
    with TestClient(create_app(test_engine)) as client:
        allowed = preflight(client, "https://kanban.example.com", "PATCH")
        default = preflight(client, FRONTEND, "PATCH")
    assert allowed["access-control-allow-origin"] == "https://kanban.example.com"
    assert default["status"] == "400"
