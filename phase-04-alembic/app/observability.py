"""Structured JSON logs and a request ID for every request (Chapter 31).

Only the standard library is used. Each request writes one "request" log line:

    {"timestamp": "...", "level": "INFO", "logger": "app.request", "message": "request",
     "request_id": "...", "method": "GET", "route": "/tasks/{task_id}",
     "status_code": 200, "duration_ms": 3.1}

Headers, query strings, and request bodies are never logged: they may contain
tokens, API keys, or personal data.
"""

import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.config import load_settings

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller's ID only if it is short and plain; otherwise generate our own.
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Fields that may be attached with `extra=` and copied into the JSON line.
EXTRA_FIELDS = ("method", "route", "status_code", "duration_ms", "error")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("app.request")


class JsonFormatter(logging.Formatter):
    """Format a log record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        for field in EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    """Send the app's logs ("app.*") to stdout as JSON and replace Uvicorn's access log.

    Uvicorn's access log prints the full path with the query string (for example
    "GET /tasks?token=..."). The JSON request log below covers the same requests
    without it, so the access log is turned off. Uvicorn's startup and error logs stay.
    """
    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app_logger.addHandler(handler)
    app_logger.setLevel(level or load_settings().log_level)
    app_logger.propagate = False
    logging.getLogger("uvicorn.access").disabled = True


def resolve_request_id(incoming: str | None) -> str:
    if incoming and VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


def route_template(request: Request) -> str:
    # "/tasks/{task_id}" instead of the real path keeps IDs out of logs and metrics.
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Log the traceback with the request ID, then answer without internal details.
        logger.exception("unhandled_error", extra=request_fields(request, 500, started))
        response = JSONResponse(
            {"detail": "Internal Server Error", "request_id": request_id}, status_code=500
        )
    else:
        logger.info("request", extra=request_fields(request, response.status_code, started))
    finally:
        request_id_var.reset(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def request_fields(request: Request, status_code: int, started: float) -> dict[str, object]:
    return {
        "request_id": request_id_var.get(),
        "method": request.method,
        "route": route_template(request),
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def install(app: FastAPI) -> None:
    app.middleware("http")(log_requests)
