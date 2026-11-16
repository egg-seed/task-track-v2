"""Integration tests execute SQL on a real isolated SQLite DB via aiosqlite."""

from uuid import uuid4

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.repositories import task as repository
from app.schemas.task import TaskCreate, TaskPatch, TaskStatus

pytestmark = pytest.mark.anyio


async def test_create_and_get(session: AsyncSession) -> None:
    task = await repository.create_task(session, TaskCreate(title="new"))
    loaded = await repository.get_task(session, task.id)
    assert loaded is not None
    assert loaded.title == "new"
    assert loaded.status == TaskStatus.TODO


async def test_filter_and_update(session: AsyncSession) -> None:
    first = await repository.create_task(session, TaskCreate(title="first"))
    await repository.create_task(session, TaskCreate(title="second", status=TaskStatus.DONE))
    assert len(await repository.list_tasks(session)) == 2
    assert len(await repository.list_tasks(session, TaskStatus.DONE)) == 1
    updated = await repository.update_task(session, first, TaskPatch(status=TaskStatus.DONE))
    assert updated.status == TaskStatus.DONE
    assert len(await repository.list_tasks(session, TaskStatus.DONE)) == 2


async def test_delete_and_missing(session: AsyncSession) -> None:
    task = await repository.create_task(session, TaskCreate(title="delete"))
    await repository.delete_task(session, task)
    assert await repository.get_task(session, task.id) is None
    assert await repository.get_task(session, uuid4()) is None


async def test_each_test_starts_empty(session: AsyncSession) -> None:
    assert await repository.list_tasks(session) == []
