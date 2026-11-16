"""Health check routes: liveness (/health) and readiness (/health/ready)."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()
logger = logging.getLogger("app.health")


@router.get("/health")
def health() -> dict[str, str]:
    # Liveness: the process answers. It does not touch the database.
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def ready(request: Request) -> dict[str, str] | JSONResponse:
    # Readiness: the app can serve requests that need the database.
    try:
        with request.app.state.db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Log the error class only: the message may include the host or user name.
        logger.error("database_unavailable", extra={"error": type(exc).__name__})
        return JSONResponse({"status": "unavailable", "database": "error"}, status_code=503)
    return {"status": "ok", "database": "ok"}
