"""TestClient checks the HTTP contract against a replaceable test DB."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_get_and_filter(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "first"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "TODO"
    assert client.get(f"/tasks/{task['id']}").json() == task
    assert client.get("/tasks").json() == [task]
    assert client.get("/tasks", params={"task_status": "DONE"}).json() == []


def test_patch_description_and_status(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "first", "description": "old"}).json()
    result = client.patch(f"/tasks/{task['id']}", json={"description": None, "status": "DONE"})
    assert result.status_code == 200
    assert result.json()["description"] is None
    assert result.json()["status"] == "DONE"


def test_delete_and_missing(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "delete"}).json()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.delete(f"/tasks/{uuid4()}").status_code == 404


def test_missing_update(client: TestClient) -> None:
    assert client.patch(f"/tasks/{uuid4()}", json={"title": "missing"}).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "X" * 101}, {"title": "ok", "status": "BAD"}],
)
def test_invalid_create(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/tasks", json=payload).status_code == 422


def test_invalid_patch(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "valid"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/tasks/{task['id']}", json={"status": None}).status_code == 422


def test_invalid_uuid(client: TestClient) -> None:
    assert client.get("/tasks/invalid-uuid").status_code == 422


def test_isolated_test_database(client: TestClient) -> None:
    assert client.get("/tasks").json() == []
