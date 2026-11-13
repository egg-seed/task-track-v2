"""Phase 01: a single-file in-memory Todo API."""

from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus | None = None


class TaskRead(TaskCreate):
    id: UUID


def create_app() -> FastAPI:
    app = FastAPI(title="Task Track API - Phase 01")
    tasks: dict[UUID, TaskRead] = {}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/tasks", response_model=list[TaskRead])
    def list_tasks(task_status: TaskStatus | None = None) -> list[TaskRead]:
        values = list(tasks.values())
        return [task for task in values if task.status == task_status] if task_status else values

    @app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(data: TaskCreate) -> TaskRead:
        task = TaskRead(id=uuid4(), **data.model_dump())
        tasks[task.id] = task
        return task

    @app.get("/tasks/{task_id}", response_model=TaskRead)
    def get_task(task_id: UUID) -> TaskRead:
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return tasks[task_id]

    @app.patch("/tasks/{task_id}", response_model=TaskRead)
    def update_task(task_id: UUID, data: TaskPatch) -> TaskRead:
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        changes = data.model_dump(exclude_unset=True)
        if changes.get("title", "supplied") is None or changes.get("status", "supplied") is None:
            raise HTTPException(status_code=422, detail="title and status cannot be null")
        updated = TaskRead.model_validate({**tasks[task_id].model_dump(), **changes})
        tasks[task_id] = updated
        return updated

    @app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(task_id: UUID) -> None:
        if tasks.pop(task_id, None) is None:
            raise HTTPException(status_code=404, detail="Task not found")

    return app


app = create_app()
