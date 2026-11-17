"""The CRUD tutorial records which SQL each step sends."""

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from tutorials.crud_sql import create_demo_engine, lifecycle, repository_calls


@pytest.fixture
def engine() -> Generator[Engine]:
    engine = create_demo_engine()
    yield engine
    engine.dispose()


def test_lifecycle_states_and_sql(engine: Engine) -> None:
    steps = {label: (sql, state) for label, sql, state in lifecycle(engine)[:5]}
    assert steps["Task(...) を作る"] == ([], "transient")
    assert steps["session.add(task)"] == ([], "pending")
    flush_sql, flush_state = steps["session.flush()"]
    assert flush_state == "persistent"
    assert flush_sql[0] == "BEGIN"
    assert flush_sql[1].startswith("INSERT INTO task")
    assert steps["session.commit()"] == (["COMMIT"], "persistent")
    read_sql, _ = steps["task.title を読む"]
    assert read_sql[1].startswith("SELECT task.id")


def test_lifecycle_ends_detached_after_delete(engine: Engine) -> None:
    *_, (label, sql, state) = lifecycle(engine)
    assert label == "session.commit()"
    assert sql == ["DELETE FROM task WHERE task.id = ?", "COMMIT"]
    assert state == "detached"


def test_repository_calls_send_expected_statements(engine: Engine) -> None:
    calls = dict(repository_calls(engine))
    assert [line.split()[0] for line in calls["create_task"]] == [
        "BEGIN",
        "INSERT",
        "COMMIT",
        "BEGIN",
        "SELECT",
    ]
    assert calls["list_tasks(DONE)"][-1].endswith("WHERE task.status = ?")
    assert "UPDATE task SET status=? WHERE task.id = ?" in calls["get_task + update_task"]
    assert "DELETE FROM task WHERE task.id = ?" in calls["get_task + delete_task"]
