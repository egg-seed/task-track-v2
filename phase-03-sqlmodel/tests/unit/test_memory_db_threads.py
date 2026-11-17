"""Only StaticPool with check_same_thread=False lets TestClient reach the in-memory tables."""

from typing import Any

from tutorials.memory_db_threads import ENGINES, make_engine, post_task


def run(label: str) -> tuple[str, list[str]]:
    opened_in: list[str] = []
    options: dict[str, Any] = ENGINES[label]
    engine = make_engine(options, opened_in)
    try:
        return post_task(engine), opened_in
    finally:
        engine.dispose()


def test_default_pool_opens_a_new_empty_database_per_thread() -> None:
    result, opened_in = run("既定のまま")
    assert result.startswith("POST /tasksで失敗 -> OperationalError")
    assert "no such table: task" in result
    assert len(opened_in) == 3


def test_static_pool_alone_is_refused_by_sqlite() -> None:
    result, opened_in = run("StaticPool だけ")
    assert result.startswith("起動（Lifespan）で失敗 -> ProgrammingError")
    assert opened_in == ["MainThread"]


def test_static_pool_shared_across_threads_works() -> None:
    result, opened_in = run("StaticPool ＋ check_same_thread=False")
    assert result == "POST /tasks -> 201 first"
    assert opened_in == ["MainThread"]
