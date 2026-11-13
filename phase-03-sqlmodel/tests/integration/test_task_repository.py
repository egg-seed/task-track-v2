"""Integration tests execute SQL on a real isolated SQLite DB."""

from uuid import uuid4

from sqlmodel import Session

from app.repositories import task as repository
from app.schemas.task import TaskCreate, TaskPatch, TaskStatus


def test_create_and_get(session: Session) -> None:
    task = repository.create_task(session, TaskCreate(title="new"))
    loaded = repository.get_task(session, task.id)
    assert loaded is not None
    assert loaded.title == "new"
    assert loaded.status == TaskStatus.TODO


def test_filter_and_update(session: Session) -> None:
    first = repository.create_task(session, TaskCreate(title="first"))
    repository.create_task(session, TaskCreate(title="second", status=TaskStatus.DONE))
    assert len(repository.list_tasks(session)) == 2
    assert len(repository.list_tasks(session, TaskStatus.DONE)) == 1
    updated = repository.update_task(session, first, TaskPatch(status=TaskStatus.DONE))
    assert updated.status == TaskStatus.DONE
    assert len(repository.list_tasks(session, TaskStatus.DONE)) == 2


def test_delete_and_missing(session: Session) -> None:
    task = repository.create_task(session, TaskCreate(title="delete"))
    repository.delete_task(session, task)
    assert repository.get_task(session, task.id) is None
    assert repository.get_task(session, uuid4()) is None


def test_each_test_starts_empty(session: Session) -> None:
    assert repository.list_tasks(session) == []
