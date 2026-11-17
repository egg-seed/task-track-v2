"""Why the test engine uses StaticPool and check_same_thread=False (Chapter 24).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.memory_db_threads

An in-memory SQLite database lives inside one connection. TestClient runs the
lifespan and the def endpoints in threads other than the test's own thread, so
the engine must hand the same connection to every thread.
"""

import logging
import threading
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.main import create_app
from app.models.task import Task  # noqa: F401

# The pool also logs the same error while it cleans up; hide it to keep the output short.
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)

ENGINES: dict[str, dict[str, Any]] = {
    "既定のまま": {},
    "StaticPool だけ": {"poolclass": StaticPool},
    "StaticPool ＋ check_same_thread=False": {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    },
}


def make_engine(options: dict[str, Any], opened_in: list[str]) -> Engine:
    engine = create_engine("sqlite://", **options)

    @event.listens_for(engine, "connect")
    def record_thread(dbapi_connection: object, connection_record: object) -> None:
        # Each new connection to "sqlite://" is a separate, empty database.
        opened_in.append(threading.current_thread().name)

    SQLModel.metadata.create_all(engine)
    return engine


def post_task(engine: Engine) -> str:
    """POST /tasks through TestClient, as the API tests do."""
    try:
        with TestClient(create_app(engine)) as client:
            response = client.post("/tasks", json={"title": "first"})
            return f"{response.status_code} {response.json()['title']}"
    except Exception as exc:
        return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"


def main() -> None:
    print(f"テストのスレッド: {threading.current_thread().name}")
    for label, options in ENGINES.items():
        opened_in: list[str] = []
        engine = make_engine(options, opened_in)
        result = post_task(engine)
        print(f"\n{label}（{type(engine.pool).__name__}）")
        print(f"  POST /tasks -> {result}")
        print(f"  接続を作ったスレッド: {', '.join(opened_in)}")
        engine.dispose()


if __name__ == "__main__":
    main()
