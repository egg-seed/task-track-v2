"""Create the app and register routers."""

from fastapi import FastAPI

from app.api.dependencies import TaskStore
from app.api.routes import health, tasks


def create_app() -> FastAPI:
    app = FastAPI(title="Task Track API", version="0.1.0")
    app.state.task_store = TaskStore()
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


app = create_app()
