"""AsyncClient checks the HTTP contract against a replaceable test DB."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_get_and_filter(client: AsyncClient) -> None:
    created = await client.post("/tasks", json={"title": "first"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "TODO"
    assert task["priority"] == 0
    assert (await client.get(f"/tasks/{task['id']}")).json() == task
    assert (await client.get("/tasks")).json() == [task]
    assert (await client.get("/tasks", params={"task_status": "DONE"})).json() == []


async def test_patch_description_and_status(client: AsyncClient) -> None:
    task = (await client.post("/tasks", json={"title": "first", "description": "old"})).json()
    result = await client.patch(
        f"/tasks/{task['id']}", json={"description": None, "status": "DONE"}
    )
    assert result.status_code == 200
    assert result.json()["description"] is None
    assert result.json()["status"] == "DONE"


async def test_delete_and_missing(client: AsyncClient) -> None:
    task = (await client.post("/tasks", json={"title": "delete"})).json()
    assert (await client.delete(f"/tasks/{task['id']}")).status_code == 204
    assert (await client.get(f"/tasks/{task['id']}")).status_code == 404
    assert (await client.delete(f"/tasks/{uuid4()}")).status_code == 404


async def test_missing_update(client: AsyncClient) -> None:
    assert (await client.patch(f"/tasks/{uuid4()}", json={"title": "missing"})).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "X" * 101}, {"title": "ok", "status": "BAD"}],
    ids=["empty-title", "too-long-title", "unknown-status"],
)
async def test_invalid_create(client: AsyncClient, payload: dict[str, str]) -> None:
    assert (await client.post("/tasks", json=payload)).status_code == 422


async def test_invalid_patch(client: AsyncClient) -> None:
    task = (await client.post("/tasks", json={"title": "valid"})).json()
    assert (await client.patch(f"/tasks/{task['id']}", json={"title": None})).status_code == 422
    assert (await client.patch(f"/tasks/{task['id']}", json={"status": None})).status_code == 422


@pytest.mark.parametrize("priority", [-1, 6, None])
async def test_invalid_priority_create(client: AsyncClient, priority: int | None) -> None:
    response = await client.post("/tasks", json={"title": "invalid priority", "priority": priority})
    assert response.status_code == 422


@pytest.mark.parametrize("priority", [-1, 6, None])
async def test_invalid_priority_patch(client: AsyncClient, priority: int | None) -> None:
    task = (await client.post("/tasks", json={"title": "keep"})).json()
    response = await client.patch(f"/tasks/{task['id']}", json={"priority": priority})
    assert response.status_code == 422
    assert (await client.get(f"/tasks/{task['id']}")).json() == task


@pytest.mark.parametrize("priority", [0, 5])
async def test_priority_can_be_created_and_updated(client: AsyncClient, priority: int) -> None:
    created = await client.post("/tasks", json={"title": "task", "priority": priority})
    assert created.status_code == 201
    assert created.json()["priority"] == priority
    updated = await client.patch(f"/tasks/{created.json()['id']}", json={"priority": 5 - priority})
    assert updated.status_code == 200
    assert updated.json()["priority"] == 5 - priority


async def test_invalid_uuid(client: AsyncClient) -> None:
    assert (await client.get("/tasks/invalid-uuid")).status_code == 422


async def test_isolated_test_database(client: AsyncClient) -> None:
    assert (await client.get("/tasks")).json() == []
