"""第19章: OAuth2PasswordBearer と /token によるパスワードフローの学習用サンプル。

アクセストークンは推測できないランダムな文字列で、サーバーのメモリに保存する。
JWTによるトークン検証は第33章で扱う。
"""

import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from functools import cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from tasks import (
    AUTH_ERROR_RESPONSES,
    TASK_ACCESS_ERROR_RESPONSES,
    Task,
    TaskCreate,
    create_task,
    get_owned_task,
    list_tasks,
)

app = FastAPI(title="Auth Basics - OAuth2 Password")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

TOKEN_TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class StoredUser:
    """DBに保存する想定のユーザー情報。パスワードそのものは保存しない。"""

    username: str
    salt: bytes
    password_hash: bytes


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


@cache
def user_db() -> dict[str, StoredUser]:
    """環境変数 DEMO_PASSWORDS（例: alice=パスワード1,bob=パスワード2）からユーザーを作る。"""
    users: dict[str, StoredUser] = {}
    for item in os.environ.get("DEMO_PASSWORDS", "").split(","):
        username, separator, password = item.strip().partition("=")
        if separator and username and password:
            salt = secrets.token_bytes(16)
            users[username] = StoredUser(username, salt, hash_password(password, salt))
    return users


# 存在しないユーザーでも同じ計算をして、応答時間からユーザーの有無を推測されにくくする
_DUMMY_USER = StoredUser("", b"0" * 16, b"")

# アクセストークン → (ユーザー名, 有効期限)
TOKENS: dict[str, tuple[str, float]] = {}


def authenticate(username: str, password: str) -> StoredUser | None:
    user = user_db().get(username, _DUMMY_USER)
    password_hash = hash_password(password, user.salt)
    if user is _DUMMY_USER or not secrets.compare_digest(password_hash, user.password_hash):
        return None
    return user


@app.post("/token", responses=AUTH_ERROR_RESPONSES)
def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict[str, str]:
    """ユーザー名とパスワードを確認し、アクセストークンを発行する。"""
    user = authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = secrets.token_urlsafe(32)
    TOKENS[token] = (user.username, time.monotonic() + TOKEN_TTL_SECONDS)
    return {"access_token": token, "token_type": "bearer"}


def current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """アクセストークンを確認し、ユーザー名を返す（認証）。"""
    entry = TOKENS.get(token)
    if entry is None or entry[1] < time.monotonic():
        TOKENS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return entry[0]


CurrentUser = Annotated[str, Depends(current_user)]


@app.get("/me", responses=AUTH_ERROR_RESPONSES)
def me(user: CurrentUser) -> dict[str, str]:
    return {"user": user}


@app.get("/tasks", responses=AUTH_ERROR_RESPONSES)
def read_tasks(user: CurrentUser) -> list[Task]:
    return list_tasks(owner=user)


@app.post("/tasks", status_code=status.HTTP_201_CREATED, responses=AUTH_ERROR_RESPONSES)
def add_task(payload: TaskCreate, user: CurrentUser) -> Task:
    return create_task(payload, owner=user)


@app.get("/tasks/{task_id}", responses=TASK_ACCESS_ERROR_RESPONSES)
def read_task(task_id: int, user: CurrentUser) -> Task:
    return get_owned_task(task_id, owner=user)
