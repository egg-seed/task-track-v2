"""FastAPI entrypoint: Alembic, not app startup, manages the DB schema."""

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from app.api.routes import health, tasks
from app.db.session import engine


def create_app(db_engine: Engine = engine) -> FastAPI:
    app = FastAPI(title="Task Track API - Phase 04")
    app.state.db_engine = db_engine
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()
