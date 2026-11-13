"""Small injectable store; replaced by a repository when adding SQLModel."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request

from app.schemas.task import TaskRead

TaskStore = dict[UUID, TaskRead]


def get_task_store(request: Request) -> TaskStore:
    return cast(TaskStore, request.app.state.task_store)


TaskStoreDep = Annotated[TaskStore, Depends(get_task_store)]
