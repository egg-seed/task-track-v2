"""Standalone Cognito access-token verification example (not a deployed app)."""

import os
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from tasks import (
    AUTH_ERROR_RESPONSES,
    TASK_ACCESS_ERROR_RESPONSES,
    Task,
    TaskCreate,
    create_task,
    get_owned_task,
    list_tasks,
)

app = FastAPI(title="Cognito JWT verification demo")
bearer = HTTPBearer(auto_error=False)

JWKS_TIMEOUT_SECONDS = 5
JWKS_CACHE_SECONDS = 300


def settings() -> tuple[str, str]:
    """Required at runtime; use a real User Pool / App Client in production."""
    region = os.environ["COGNITO_REGION"]
    pool = os.environ["COGNITO_USER_POOL_ID"]
    client = os.environ["COGNITO_APP_CLIENT_ID"]
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool}"
    return issuer, client


@lru_cache
def jwks_client(issuer: str) -> PyJWKClient:
    # The whole JWKS is cached for `lifespan` seconds and refetched when an unknown kid
    # arrives. Per-key caching (cache_keys=True) is off: it never expires, so a key that
    # Cognito removed would keep being accepted.
    return PyJWKClient(
        f"{issuer}/.well-known/jwks.json",
        cache_keys=False,
        lifespan=JWKS_CACHE_SECONDS,
        timeout=JWKS_TIMEOUT_SECONDS,
    )


def verify_access_token(token: str) -> dict[str, Any]:
    issuer, client_id = settings()
    try:
        key = jwks_client(issuer).get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_aud": False,  # Cognito access-token client_id is checked below.
                "require": ["exp", "iat", "iss", "sub", "client_id", "token_use"],
            },
        )
        if claims["token_use"] != "access" or claims["client_id"] != client_id:
            raise InvalidTokenError("Wrong token type or client")
        return claims
    except (InvalidTokenError, PyJWKClientError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def current_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(credentials.credentials)


def current_user(claims: Annotated[dict[str, Any], Depends(current_claims)]) -> str:
    """Return the verified user's sub. Same role as current_client() in Chapter 20."""
    sub: str = claims["sub"]
    return sub


CurrentUser = Annotated[str, Depends(current_user)]


@app.get("/me", responses=AUTH_ERROR_RESPONSES)
def me(user: CurrentUser) -> dict[str, str]:
    return {"sub": user}


# The routes below are the same as Chapter 20's api_key_app.py.
# Only the authentication dependency changed: CurrentClient -> CurrentUser.
@app.get("/tasks", responses=AUTH_ERROR_RESPONSES)
def read_tasks(user: CurrentUser) -> list[Task]:
    return list_tasks(owner=user)


@app.post("/tasks", status_code=status.HTTP_201_CREATED, responses=AUTH_ERROR_RESPONSES)
def add_task(payload: TaskCreate, user: CurrentUser) -> Task:
    return create_task(payload, owner=user)


@app.get("/tasks/{task_id}", responses=TASK_ACCESS_ERROR_RESPONSES)
def read_task(task_id: int, user: CurrentUser) -> Task:
    return get_owned_task(task_id, owner=user)
