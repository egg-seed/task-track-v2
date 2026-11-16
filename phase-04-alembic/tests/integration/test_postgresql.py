"""Run the Alembic revisions and the API against a real PostgreSQL database.

These tests run only when TASKS_TEST_POSTGRES_URL is set, for example:

    TASKS_TEST_POSTGRES_URL=postgresql://tasks:devpass@localhost:5432/tasks_test

The database is emptied (downgrade to base) before and after each test, so the
database name must end with "_test" to avoid wiping a real database by mistake.
"""

import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, make_url, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from app.db.session import build_engine
from app.main import create_app

POSTGRES_URL = os.environ.get("TASKS_TEST_POSTGRES_URL", "")

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="TASKS_TEST_POSTGRES_URL is not set")


def enum_type_exists(engine: Engine) -> bool:
    with engine.connect() as conn:
        found = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'taskstatus'"))
        return found.first() is not None


@pytest.fixture
def pg_config(monkeypatch: pytest.MonkeyPatch) -> Generator[Config]:
    database = make_url(POSTGRES_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"refusing to reset database {database!r}: name must end with '_test'")
    monkeypatch.setenv("TASKS_DATABASE_URL", POSTGRES_URL)
    cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    command.downgrade(cfg, "base")
    yield cfg
    command.downgrade(cfg, "base")


@pytest.fixture
def pg_engine(pg_config: Config) -> Generator[Engine]:
    engine = build_engine(POSTGRES_URL)
    yield engine
    engine.dispose()


def test_upgrade_downgrade_upgrade_round_trip(pg_config: Config, pg_engine: Engine) -> None:
    command.upgrade(pg_config, "head")
    assert enum_type_exists(pg_engine)

    command.downgrade(pg_config, "base")
    assert "task" not in inspect(pg_engine).get_table_names()
    # DROP TABLE alone leaves the ENUM type behind on PostgreSQL.
    assert not enum_type_exists(pg_engine)

    command.upgrade(pg_config, "head")
    assert "priority" in {c["name"] for c in inspect(pg_engine).get_columns("task")}


def test_upgrade_keeps_existing_data(pg_config: Config, pg_engine: Engine) -> None:
    command.upgrade(pg_config, "0001")
    with pg_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO task (id, title, status) VALUES (:id, :title, 'TODO')"),
            {"id": uuid4(), "title": "keep me"},
        )

    command.upgrade(pg_config, "head")

    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT title, priority FROM task")).one()
    assert tuple(row) == ("keep me", 0)


def test_migrated_database_matches_sqlmodel_metadata(pg_config: Config, pg_engine: Engine) -> None:
    command.upgrade(pg_config, "head")
    with pg_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, SQLModel.metadata)
    assert differences == []


def test_api_reads_and_writes_postgresql(pg_config: Config, pg_engine: Engine) -> None:
    command.upgrade(pg_config, "head")
    with TestClient(create_app(pg_engine)) as client:
        created = client.post("/tasks", json={"title": "本番DBの確認", "priority": 3})
        assert created.status_code == 201
        task_id = created.json()["id"]

        fetched = client.get(f"/tasks/{task_id}")
        assert fetched.status_code == 200
        assert fetched.json()["priority"] == 3
        assert fetched.json()["status"] == "TODO"
