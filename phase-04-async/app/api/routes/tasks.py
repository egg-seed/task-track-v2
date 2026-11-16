"""Task HTTP routes delegate persistence to the Repository."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SessionDep
from app.repositories import task as repository
from app.schemas.task import TaskCreate, TaskPatch, TaskRead, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(session: SessionDep, task_status: TaskStatus | None = None) -> list[TaskRead]:
    tasks = await repository.list_tasks(session, task_status)
    return [TaskRead.model_validate(task, from_attributes=True) for task in tasks]


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, session: SessionDep) -> TaskRead:
    task = await repository.create_task(session, data)
    return TaskRead.model_validate(task, from_attributes=True)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, session: SessionDep) -> TaskRead:
    task = await repository.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRead.model_validate(task, from_attributes=True)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: UUID, data: TaskPatch, session: SessionDep) -> TaskRead:
    task = await repository.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = await repository.update_task(session, task, data)
    return TaskRead.model_validate(updated, from_attributes=True)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, session: SessionDep) -> None:
    task = await repository.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await repository.delete_task(session, task)
