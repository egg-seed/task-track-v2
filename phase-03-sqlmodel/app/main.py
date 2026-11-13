"""Register API routes and initialize the teaching database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from app.api.routes import health, tasks
from app.db.session import create_db_and_tables, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables(app.state.db_engine)
    yield


def create_app(db_engine: Engine = engine) -> FastAPI:
    app = FastAPI(title="Task Track API - Phase 03", lifespan=lifespan)
    app.state.db_engine = db_engine
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()
