"""FastAPI entrypoint: Alembic, not app startup, manages the DB schema."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes import health, tasks
from app.db.session import engine, session_factory


def create_app(db_engine: AsyncEngine = engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        # Close pooled connections inside the event loop that opened them.
        await db_engine.dispose()

    app = FastAPI(title="Task Track API - Phase 04 (async)", lifespan=lifespan)
    app.state.session_factory = session_factory(db_engine)
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()
