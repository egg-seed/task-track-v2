"""Transaction boundaries, rollback and optimistic locking in the tutorial."""

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from tutorials.transactions import (
    commit_each_step,
    commit_once,
    create_demo_engine,
    http_conflict,
    lost_update,
    optimistic_lock,
    use_after_failed_commit,
)


@pytest.fixture
def engine() -> Generator[Engine]:
    engine = create_demo_engine()
    yield engine
    engine.dispose()


def test_commit_each_step_leaves_the_first_change(engine: Engine) -> None:
    assert commit_each_step(engine) == ("IntegrityError", 1)


def test_commit_once_leaves_nothing(engine: Engine) -> None:
    assert commit_once(engine) == ("IntegrityError", 0)


def test_session_needs_rollback_after_failed_commit(engine: Engine) -> None:
    assert use_after_failed_commit(engine, rollback=False) == "PendingRollbackError"


def test_session_works_after_rollback(engine: Engine) -> None:
    assert use_after_failed_commit(engine, rollback=True) == "タスク1件"


def test_lost_update_keeps_only_the_last_write(engine: Engine) -> None:
    assert lost_update(engine) == "牛乳を買う（急ぎ）"


def test_optimistic_lock_rejects_the_second_update(engine: Engine) -> None:
    assert optimistic_lock(engine) == (True, False, "牛乳を買う（2本）", 2)


def test_http_conflict_returns_409(engine: Engine) -> None:
    (first_status, first_body), (second_status, _) = http_conflict(engine)
    assert first_status == 200
    assert first_body == {"body": "原稿を書く（下書き）", "version": 2}
    assert second_status == 409
