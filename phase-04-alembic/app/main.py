"""FastAPI entrypoint: Alembic, not app startup, manages the DB schema."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app import observability
from app.api.routes import health, tasks
from app.config import load_settings
from app.db.session import engine

observability.configure_logging()


def create_app(db_engine: Engine = engine) -> FastAPI:
    app = FastAPI(title="Task Track API - Phase 04")
    app.state.db_engine = db_engine
    observability.install(app)
    # The Kanban frontend runs on another origin (Chapter 21).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=load_settings().cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()
