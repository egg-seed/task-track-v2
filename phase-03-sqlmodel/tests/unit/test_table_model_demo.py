"""The table model tutorial shows what SQLModel and SQLite check, and what they do not."""

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine
from tutorials.table_model_demo import (
    constructor_skips_validation,
    create_all_keeps_old_columns,
    create_table_sql,
    database_accepts_invalid_titles,
    model_validate_rejects,
    survives_restart,
)


@pytest.fixture
def memory_engine() -> Generator[Engine]:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_create_table_sql_has_primary_key_and_lengths(memory_engine: Engine) -> None:
    sql = create_table_sql(memory_engine)
    assert sql.startswith("CREATE TABLE task")
    assert "title VARCHAR(100) NOT NULL" in sql
    assert "PRIMARY KEY (id)" in sql


def test_constructor_does_not_validate() -> None:
    assert constructor_skips_validation().title == ""


def test_model_validate_rejects_empty_title() -> None:
    assert model_validate_rejects({"title": ""}) == ["string_too_short"]
    assert model_validate_rejects({"title": "ok"}) == []


def test_sqlite_stores_titles_that_break_field_rules(memory_engine: Engine) -> None:
    assert database_accepts_invalid_titles(memory_engine) == [0, 101]


def test_file_database_survives_a_new_engine(tmp_path: Path) -> None:
    assert survives_restart(tmp_path / "demo.db") == ["牛乳を買う"]


def test_create_all_does_not_add_missing_columns() -> None:
    engine = create_engine("sqlite://")
    try:
        assert create_all_keeps_old_columns(engine) == ["id", "title"]
    finally:
        engine.dispose()
