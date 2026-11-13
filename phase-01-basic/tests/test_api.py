"""Phase 01's basic request tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "はじめてのタスク"})
    assert created.status_code == 201
    assert created.json()["status"] == "TODO"
    assert client.get("/tasks").json() == [created.json()]


def test_read_update_delete(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "作業"}).json()
    task_id = task["id"]
    assert client.get(f"/tasks/{task_id}").json() == task
    updated = client.patch(f"/tasks/{task_id}", json={"status": "DONE"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "DONE"
    assert client.get("/tasks", params={"task_status": "DONE"}).json() == [updated.json()]
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_invalid_input(client: TestClient) -> None:
    assert client.post("/tasks", json={"title": ""}).status_code == 422


@pytest.mark.parametrize("field", ["title", "status"])
def test_patch_rejects_explicit_null(client: TestClient, field: str) -> None:
    task = client.post("/tasks", json={"title": "作業"}).json()
    task_id = task["id"]
    response = client.patch(f"/tasks/{task_id}", json={field: None})
    assert response.status_code == 422
    # A rejected partial update must not modify the stored task.
    assert client.get(f"/tasks/{task_id}").json() == task


def test_isolation(client: TestClient) -> None:
    assert client.get("/tasks").json() == []
