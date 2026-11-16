"""2つの認証サンプルで共有する、タスクのデータと認可の処理。"""

from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str


class Task(BaseModel):
    id: int
    title: str
    owner: str


# OpenAPI（Swagger UI）に、認証・認可で返すエラーを載せるための宣言
AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "認証の失敗（資格情報がない、または無効）"},
}
TASK_ACCESS_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    **AUTH_ERROR_RESPONSES,
    403: {"description": "認可の失敗（他の主体のタスク）"},
    404: {"description": "タスクが存在しない"},
}

SEED_TASKS = (
    Task(id=1, title="aliceの買い物リスト", owner="alice"),
    Task(id=2, title="bobの議事録", owner="bob"),
)

TASKS: dict[int, Task] = {task.id: task for task in SEED_TASKS}


def reset_tasks() -> None:
    """保存されたタスクを初期状態に戻す（テスト用）。"""
    TASKS.clear()
    TASKS.update({task.id: task for task in SEED_TASKS})


def list_tasks(owner: str) -> list[Task]:
    """主体が所有するタスクだけを返す。"""
    return [task for task in TASKS.values() if task.owner == owner]


def create_task(payload: TaskCreate, owner: str) -> Task:
    task = Task(id=max(TASKS, default=0) + 1, title=payload.title, owner=owner)
    TASKS[task.id] = task
    return task


def get_owned_task(task_id: int, owner: str) -> Task:
    """タスクを取得し、主体が所有者かどうかを確認する（認可）。"""
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.owner != owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return task
