"""Async engine and per-request AsyncSession. Tables are created by Alembic."""

import os
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"

# Async drivers for the URL schemes this sample accepts. psycopg (v3) provides both
# a sync and an async API, so PostgreSQL URLs keep Neon's sslmode/channel_binding options.
ASYNC_DRIVERS = {"sqlite": "aiosqlite", "postgresql": "psycopg"}


def database_url() -> str:
    """Return the DB URL: TASKS_DATABASE_URL, then DATABASE_URL, then local SQLite.

    DATABASE_URL is the name FastAPI Cloud's Neon integration injects (Chapter 29).
    """
    return (
        os.environ.get("TASKS_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )


def async_database_url(url: str) -> str:
    """Rewrite e.g. postgresql:// to postgresql+psycopg:// so the async engine accepts it."""
    parsed = make_url(url)
    driver = ASYNC_DRIVERS.get(parsed.get_backend_name())
    if driver is None:
        raise ValueError(f"unsupported database: {parsed.drivername}")
    return parsed.set(drivername=f"{parsed.get_backend_name()}+{driver}").render_as_string(
        hide_password=False
    )


def build_engine(url: str | None = None) -> AsyncEngine:
    db_url = async_database_url(url if url is not None else database_url())
    if db_url.startswith("sqlite"):
        return create_async_engine(db_url)
    # Server DBs (PostgreSQL, etc.) may close idle connections; check before reuse.
    return create_async_engine(db_url, pool_pre_ping=True)


engine = build_engine()


def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # Keep attributes loaded after commit: an expired attribute would need a lazy
    # load, which an async session cannot do implicitly.
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
