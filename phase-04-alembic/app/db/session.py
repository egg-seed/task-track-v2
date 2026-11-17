"""Engine and per-request Session. Tables are created by Alembic."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.config import DEFAULT_DATABASE_URL, load_settings

__all__ = ["DEFAULT_DATABASE_URL", "build_engine", "database_url", "engine", "get_session"]


def database_url() -> str:
    """Return the DB URL: TASKS_DATABASE_URL, then DATABASE_URL, then local SQLite.

    DATABASE_URL is the name FastAPI Cloud's Neon integration injects (Chapter 30).
    The rules live in app.config.Settings (Chapter 27).
    """
    return load_settings().resolved_database_url()


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
