"""Customise what Swagger UI shows (Chapter 9).

An independent example: the Phase 02 app in app/ is not changed.

    uv run fastapi dev tutorials/openapi_docs.py
    TASKS_SHOW_DOCS=false uv run fastapi dev tutorials/openapi_docs.py
"""

import os
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field

DESCRIPTION = """
タスクを `TODO`・`DOING`・`DONE` の3つの状態で管理するAPIです。

本文は **Markdown** で書けます。
"""

TAGS_METADATA = [
    {"name": "tasks", "description": "タスクの作成・取得・削除"},
    {"name": "health", "description": "稼働状況の確認"},
]


class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100,
        description="タスクの名前",
        examples=["設計レビューを行う"],
    )
    description: str | None = Field(
        default=None,
        description="補足の説明",
        examples=["APIの入出力を確認する"],
    )


class TaskRead(TaskCreate):
    id: UUID


class ErrorMessage(BaseModel):
    detail: str


TaskId = Annotated[UUID, Path(description="タスクのID")]


def create_docs_app(show_docs: bool = True) -> FastAPI:
    app = FastAPI(
        title="タスク管理API",
        summary="カンバン形式でタスクを管理する",
        description=DESCRIPTION,
        version="0.2.0",
        openapi_tags=TAGS_METADATA,
        # None removes the page. Without /openapi.json, /docs and /redoc have nothing to show.
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        openapi_url="/openapi.json" if show_docs else None,
    )
    tasks: dict[UUID, TaskRead] = {}

    @app.get("/health", tags=["health"], summary="稼働を確認する")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/tasks",
        tags=["tasks"],
        status_code=status.HTTP_201_CREATED,
        summary="タスクを作成する",
        response_description="作成したタスク",
    )
    def create_task(data: TaskCreate) -> TaskRead:
        """新しいタスクを作成します。

        IDはサーバーが発行します。
        """
        task = TaskRead(id=uuid4(), **data.model_dump())
        tasks[task.id] = task
        return task

    @app.get(
        "/tasks/{task_id}",
        tags=["tasks"],
        summary="タスクを1件取得する",
        responses={
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorMessage,
                "description": "指定したタスクが見つからない",
            }
        },
    )
    def get_task(task_id: TaskId) -> TaskRead:
        if task_id not in tasks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return tasks[task_id]

    @app.get("/todos", tags=["tasks"], summary="タスクの一覧（旧パス）", deprecated=True)
    def list_todos() -> list[TaskRead]:
        """`GET /tasks` に移行してください。"""
        return list(tasks.values())

    return app


app = create_docs_app(show_docs=os.environ.get("TASKS_SHOW_DOCS", "true") != "false")
