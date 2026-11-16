"""Engine and per-request Session. Tables are created by Alembic."""

import os
from collections.abc import Generator

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"


def database_url() -> str:
    """Return the DB URL: TASKS_DATABASE_URL, then DATABASE_URL, then local SQLite.

    DATABASE_URL is the name FastAPI Cloud's Neon integration injects (Chapter 27).
    """
    return (
        os.environ.get("TASKS_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )


def build_engine(url: str | None = None) -> Engine:
    db_url = url if url is not None else database_url()
    if db_url.startswith("sqlite:"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    # Server DBs (PostgreSQL, etc.) may close idle connections; check before reuse.
    return create_engine(db_url, pool_pre_ping=True)


engine = build_engine()


def get_session(request: Request) -> Generator[Session]:
    with Session(request.app.state.db_engine) as session:
        yield session
