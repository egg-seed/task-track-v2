"""HTTP contract tests, independent of the database."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_task_store
from app.main import create_app
from app.schemas.task import TaskRead, TaskStatus


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_empty(client: TestClient) -> None:
    assert client.get("/tasks").json() == []


def test_create(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "first"})
    assert response.status_code == 201
    assert response.json()["status"] == "TODO"


def test_get(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "first"}).json()
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_get_missing(client: TestClient) -> None:
    assert client.get(f"/tasks/{uuid4()}").status_code == 404


def test_list_filter(client: TestClient) -> None:
    client.post("/tasks", json={"title": "first"})
    client.post("/tasks", json={"title": "second", "status": "DONE"})
    assert len(client.get("/tasks").json()) == 2
    filtered = client.get("/tasks", params={"task_status": "DONE"})
    assert filtered.status_code == 200
    assert [item["title"] for item in filtered.json()] == ["second"]


def test_patch(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "first"}).json()
    response = client.patch(f"/tasks/{task['id']}", json={"status": "DOING"})
    assert response.status_code == 200
    assert response.json()["status"] == "DOING"
    assert response.json()["title"] == "first"


def test_patch_missing(client: TestClient) -> None:
    assert client.patch(f"/tasks/{uuid4()}", json={"title": "x"}).status_code == 404


def test_delete(client: TestClient) -> None:
    task = client.post("/tasks", json={"title": "first"}).json()
    response = client.delete(f"/tasks/{task['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_missing(client: TestClient) -> None:
    assert client.delete(f"/tasks/{uuid4()}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "X" * 101}, {"title": "ok", "status": "INVALID"}],
)
def test_invalid_create(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/tasks", json=payload).status_code == 422


@pytest.mark.parametrize("payload", [{"title": None}, {"status": None}])
def test_invalid_patch(client: TestClient, payload: dict[str, None]) -> None:
    task = client.post("/tasks", json={"title": "ok"}).json()
    assert client.patch(f"/tasks/{task['id']}", json=payload).status_code == 422


def test_invalid_uuid(client: TestClient) -> None:
    assert client.get("/tasks/not-a-uuid").status_code == 422


def test_dependency_override() -> None:
    app = create_app()
    task = TaskRead(id=uuid4(), title="injected", status=TaskStatus.DONE)
    app.dependency_overrides[get_task_store] = lambda: {task.id: task}
    with TestClient(app) as client:
        response = client.get("/tasks")
        assert response.status_code == 200
        assert response.json()[0]["title"] == "injected"
    app.dependency_overrides.clear()
