"""HTTP-facing task CRUD; persistence is added in later chapters."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import TaskStoreDep
from app.schemas.task import TaskCreate, TaskPatch, TaskRead, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(store: TaskStoreDep, task_status: TaskStatus | None = None) -> list[TaskRead]:
    values = list(store.values())
    if task_status is None:
        return values
    return [task for task in values if task.status == task_status]


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, store: TaskStoreDep) -> TaskRead:
    task = TaskRead(id=uuid4(), **data.model_dump())
    store[task.id] = task
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, store: TaskStoreDep) -> TaskRead:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: UUID, data: TaskPatch, store: TaskStoreDep) -> TaskRead:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = TaskRead.model_validate({**task.model_dump(), **data.model_dump(exclude_unset=True)})
    store[task_id] = updated
    return updated


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: UUID, store: TaskStoreDep) -> None:
    if store.pop(task_id, None) is None:
        raise HTTPException(status_code=404, detail="Task not found")
