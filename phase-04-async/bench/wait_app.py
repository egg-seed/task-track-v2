"""A tiny app that waits on PostgreSQL, to compare def and async def (Chapter 12 column).

Each request runs SELECT pg_sleep(0.5). Start one mode at a time:

    BENCH_MODE=sync  uv run uvicorn bench.wait_app:app --port 8766
    BENCH_MODE=async uv run uvicorn bench.wait_app:app --port 8766

BENCH_POOL_SIZE sets the connection pool size (default 5, plus 10 overflow).
Sync mode also serves /wait-dep, which takes the connection from a yield dependency.
BENCH_LIMIT caps that dependency with Depends(max_concurrency=...).

/health is a plain def endpoint, like Phase 04's, so it needs a worker thread to answer.
"""

import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import Connection, text

from app.db.session import async_database_url, database_url

MODE = os.environ.get("BENCH_MODE", "async")
POOL_SIZE = int(os.environ.get("BENCH_POOL_SIZE", "5"))
MAX_OVERFLOW = 10 if POOL_SIZE == 5 else 0
LIMIT = int(os.environ["BENCH_LIMIT"]) if os.environ.get("BENCH_LIMIT") else None
WAIT = text("SELECT pg_sleep(0.5)")

app = FastAPI(title=f"wait app ({MODE})")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if MODE == "sync":
    from sqlalchemy import create_engine

    sync_engine = create_engine(database_url(), pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW)

    @app.get("/wait")
    def wait_sync() -> dict[str, str]:
        with sync_engine.connect() as connection:
            connection.execute(WAIT)
        return {"mode": "sync"}

    def get_connection() -> Iterator[Connection]:
        with sync_engine.connect() as connection:
            yield connection

    # Requests over the limit wait here without holding a worker thread.
    ConnectionDep = Annotated[Connection, Depends(get_connection, max_concurrency=LIMIT)]

    @app.get("/wait-dep")
    def wait_sync_dependency(connection: ConnectionDep) -> dict[str, str]:
        connection.execute(WAIT)
        return {"mode": "sync-dependency"}

else:
    from sqlalchemy.ext.asyncio import create_async_engine

    async_engine = create_async_engine(
        async_database_url(database_url()), pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW
    )

    @app.get("/wait")
    async def wait_async() -> dict[str, str]:
        async with async_engine.connect() as connection:
            await connection.execute(WAIT)
        return {"mode": "async"}
