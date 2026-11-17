"""Request IDs, JSON logs, and health checks (Chapter 32)."""

import json
import logging
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.main import create_app
from app.observability import REQUEST_ID_HEADER, JsonFormatter


@pytest.fixture
def app_logs(caplog: pytest.LogCaptureFixture) -> Generator[pytest.LogCaptureFixture]:
    # The "app" logger does not propagate to the root logger, so attach caplog directly.
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    yield caplog
    app_logger.removeHandler(caplog.handler)


def request_logs(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "app.request"]


def test_response_has_generated_request_id(client: TestClient) -> None:
    response = client.get("/health")
    request_id = response.headers[REQUEST_ID_HEADER]
    assert len(request_id) == 32


def test_valid_incoming_request_id_is_kept(client: TestClient) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "client-req-123"})
    assert response.headers[REQUEST_ID_HEADER] == "client-req-123"


@pytest.mark.parametrize("incoming", ["x" * 65, "bad id with spaces", "a\nb"])
def test_invalid_incoming_request_id_is_replaced(client: TestClient, incoming: str) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: incoming})
    assert response.headers[REQUEST_ID_HEADER] != incoming
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


def test_request_log_uses_route_template_and_hides_secrets(
    client: TestClient, app_logs: pytest.LogCaptureFixture
) -> None:
    task = client.post("/tasks", json={"title": "log me"}).json()
    app_logs.clear()
    response = client.get(
        f"/tasks/{task['id']}?token=secret-in-query",
        headers={"Authorization": "Bearer secret-token"},
    )
    [record] = request_logs(app_logs)
    line = JsonFormatter().format(record)
    entry = json.loads(line)
    assert entry["message"] == "request"
    assert entry["route"] == "/tasks/{task_id}"
    assert entry["status_code"] == 200
    assert entry["method"] == "GET"
    assert entry["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert entry["duration_ms"] >= 0
    assert task["id"] not in line
    assert "secret" not in line


def test_unmatched_path_is_logged_without_the_raw_path(
    client: TestClient, app_logs: pytest.LogCaptureFixture
) -> None:
    assert client.get("/no/such/path/12345").status_code == 404
    [record] = request_logs(app_logs)
    assert JsonFormatter().format(record).count("12345") == 0
    assert json.loads(JsonFormatter().format(record))["route"] == "unmatched"


def test_unhandled_error_returns_500_with_request_id(
    test_engine: Engine, app_logs: pytest.LogCaptureFixture
) -> None:
    app = create_app(test_engine)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database password=hunter2 leaked into message")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    request_id = response.headers[REQUEST_ID_HEADER]
    assert response.json() == {"detail": "Internal Server Error", "request_id": request_id}
    [record] = request_logs(app_logs)
    entry = json.loads(JsonFormatter().format(record))
    assert entry["level"] == "ERROR"
    assert entry["message"] == "unhandled_error"
    assert entry["request_id"] == request_id
    assert "RuntimeError" in entry["exception"]
    # The traceback stays in the server log; the client never sees it.
    assert "hunter2" not in response.text


def test_readiness_checks_the_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readiness_reports_503_when_database_is_down(
    tmp_path: Path, app_logs: pytest.LogCaptureFixture
) -> None:
    broken = create_engine(f"sqlite:///{tmp_path}/missing-dir/tasks.db")
    with TestClient(create_app(broken)) as client:
        ready = client.get("/health/ready")
        live = client.get("/health")
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable", "database": "error"}
    # Liveness stays green: restarting the process would not fix the database.
    assert live.status_code == 200
    [error] = [r for r in app_logs.records if r.name == "app.health"]
    assert json.loads(JsonFormatter().format(error))["error"] == "OperationalError"
    broken.dispose()


def test_uvicorn_access_log_is_replaced() -> None:
    # Uvicorn's access log would print query strings such as "?token=...".
    assert logging.getLogger("uvicorn.access").disabled
