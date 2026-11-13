"""Exercise both Alembic revisions and preserve a preexisting task."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from app.models.task import Task
from app.schemas.task import TaskStatus


def test_upgrade_keeps_existing_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("TASKS_DATABASE_URL", db_url)
    cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    command.upgrade(cfg, "0001")
    engine = create_engine(db_url)
    task_id = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO task (id, title, status) VALUES (:id, :title, :status)"),
            {"id": task_id.replace("-", ""), "title": "keep me", "status": "TODO"},
        )
    command.upgrade(cfg, "head")
    assert "priority" in {c["name"] for c in inspect(engine).get_columns("task")}
    with engine.connect() as conn:
        row = conn.execute(text("SELECT title, priority FROM task")).one()
    assert row == ("keep me", 0)
    # Verify that an old row can be read through the current SQLModel mapping.
    with Session(engine) as session:
        restored = session.get(Task, UUID(task_id))
        assert restored is not None
        assert restored.title == "keep me"
        assert restored.status == TaskStatus.TODO
        assert restored.priority == 0
    command.downgrade(cfg, "0001")
    assert "priority" not in {c["name"] for c in inspect(engine).get_columns("task")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT title FROM task")).scalar_one() == "keep me"
    engine.dispose()


def test_migrated_database_matches_sqlmodel_metadata(test_engine: Engine) -> None:
    # Alembic autogenerate must see no pending changes at revision head.
    with test_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, SQLModel.metadata)
    assert differences == []
