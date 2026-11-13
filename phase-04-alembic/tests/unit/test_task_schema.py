"""Schema tests run without an HTTP client or database."""

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskPatch, TaskStatus


def test_create_defaults() -> None:
    task = TaskCreate(title="new task")
    assert task.status is TaskStatus.TODO
    assert task.description is None
    assert task.priority == 0


@pytest.mark.parametrize("title", ["", "X" * 101])
def test_invalid_title(title: str) -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title=title)


def test_invalid_status() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "new task", "status": "INVALID"})


def test_patch_omission() -> None:
    patch = TaskPatch()
    assert patch.model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize("field", ["title", "status", "priority"])
def test_patch_rejects_null(field: str) -> None:
    with pytest.raises(ValidationError):
        TaskPatch.model_validate({field: None})


@pytest.mark.parametrize("priority", [0, 5])
def test_priority_accepts_boundary_values(priority: int) -> None:
    created = TaskCreate(title="boundary", priority=priority)
    updated = TaskPatch(priority=priority)
    assert created.priority == priority
    assert updated.model_dump(exclude_unset=True) == {"priority": priority}


@pytest.mark.parametrize("priority", [-1, 6])
def test_create_rejects_out_of_range_priority(priority: int) -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title="invalid", priority=priority)


@pytest.mark.parametrize("priority", [-1, 6])
def test_patch_rejects_out_of_range_priority(priority: int) -> None:
    with pytest.raises(ValidationError):
        TaskPatch(priority=priority)


def test_patch_description_can_be_null() -> None:
    payload = TaskPatch(description=None).model_dump(exclude_unset=True)
    assert payload == {"description": None}
