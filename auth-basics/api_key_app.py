"""第19章: APIキーによる認証と、タスクの所有者による認可の学習用サンプル。"""

import os
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader

from tasks import (
    AUTH_ERROR_RESPONSES,
    TASK_ACCESS_ERROR_RESPONSES,
    Task,
    TaskCreate,
    create_task,
    get_owned_task,
    list_tasks,
)

app = FastAPI(title="Auth Basics - API Key")

api_key_header = APIKeyHeader(name="X-API-Key", description="発行済みのAPIキー")


def load_api_keys() -> dict[str, str]:
    """環境変数 API_KEYS（例: alice=キー1,bob=キー2）を「クライアント名→キー」の辞書にする。"""
    keys: dict[str, str] = {}
    for item in os.environ.get("API_KEYS", "").split(","):
        name, separator, key = item.strip().partition("=")
        if separator and name and key:
            keys[name] = key
    return keys


def current_client(key: Annotated[str, Depends(api_key_header)]) -> str:
    """APIキーを照合し、リクエストしたクライアント名を返す（認証）。"""
    for client, expected in load_api_keys().items():
        if secrets.compare_digest(key.encode(), expected.encode()):
            return client
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "APIKey"},
    )


CurrentClient = Annotated[str, Depends(current_client)]


@app.get("/me", responses=AUTH_ERROR_RESPONSES)
def me(client: CurrentClient) -> dict[str, str]:
    return {"client": client}


@app.get("/tasks", responses=AUTH_ERROR_RESPONSES)
def read_tasks(client: CurrentClient) -> list[Task]:
    return list_tasks(owner=client)


@app.post("/tasks", status_code=status.HTTP_201_CREATED, responses=AUTH_ERROR_RESPONSES)
def add_task(payload: TaskCreate, client: CurrentClient) -> Task:
    return create_task(payload, owner=client)


@app.get("/tasks/{task_id}", responses=TASK_ACCESS_ERROR_RESPONSES)
def read_task(task_id: int, client: CurrentClient) -> Task:
    return get_owned_task(task_id, owner=client)
