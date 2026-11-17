"""Show the SQL each Repository function sends, and when it is sent (Chapter 16).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.crud_sql

The script uses an in-memory SQLite database, so tasks.db is not touched.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models.task import Task
from app.repositories import task as repository
from app.schemas.task import TaskCreate, TaskPatch, TaskStatus


def create_demo_engine() -> Engine:
    # StaticPool keeps one connection, so every Session sees the same in-memory DB.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def record_sql(engine: Engine) -> Iterator[list[str]]:
    """Collect BEGIN, each SQL statement, COMMIT and ROLLBACK while the block runs."""
    events: list[str] = []

    def on_begin(*_: Any) -> None:
        events.append("BEGIN")

    def on_execute(*args: Any) -> None:
        events.append(" ".join(str(args[2]).split()))

    def on_commit(*_: Any) -> None:
        events.append("COMMIT")

    def on_rollback(*_: Any) -> None:
        events.append("ROLLBACK")

    listeners: list[tuple[str, Callable[..., None]]] = [
        ("begin", on_begin),
        ("before_cursor_execute", on_execute),
        ("commit", on_commit),
        ("rollback", on_rollback),
    ]
    for name, listener in listeners:
        event.listen(engine, name, listener)
    try:
        yield events
    finally:
        for name, listener in listeners:
            event.remove(engine, name, listener)


def object_state(obj: object) -> str:
    """The ORM state of an object: transient, pending, persistent, deleted or detached."""
    state = inspect(obj)
    for name in ("transient", "pending", "persistent", "deleted", "detached"):
        if getattr(state, name):
            return name
    return "unknown"


Step = tuple[str, list[str], str]


def lifecycle(engine: Engine) -> list[Step]:
    """Follow one Task through add, flush, commit, attribute access, delete and close."""
    steps: list[Step] = []
    with Session(engine) as session:
        task = Task(title="牛乳を買う")
        steps.append(("Task(...) を作る", [], object_state(task)))
        with record_sql(engine) as sql:
            session.add(task)
        steps.append(("session.add(task)", sql, object_state(task)))
        with record_sql(engine) as sql:
            session.flush()
        steps.append(("session.flush()", sql, object_state(task)))
        with record_sql(engine) as sql:
            session.commit()
        steps.append(("session.commit()", sql, object_state(task)))
        with record_sql(engine) as sql:
            _ = task.title
        steps.append(("task.title を読む", sql, object_state(task)))
        with record_sql(engine) as sql:
            session.delete(task)
        steps.append(("session.delete(task)", sql, object_state(task)))
        with record_sql(engine) as sql:
            session.commit()
        steps.append(("session.commit()", sql, object_state(task)))
    return steps


def repository_calls(engine: Engine) -> list[tuple[str, list[str]]]:
    """Call each Repository function in its own Session, like one request each."""
    calls: list[tuple[str, list[str]]] = []

    def run(label: str, action: Callable[[Session], object]) -> object:
        with Session(engine) as session, record_sql(engine) as sql:
            result = action(session)
        calls.append((label, sql))
        return result

    created = run("create_task", lambda s: repository.create_task(s, TaskCreate(title="本を返す")))
    assert isinstance(created, Task)
    task_id = created.id
    run("list_tasks", lambda s: repository.list_tasks(s))
    run("list_tasks(DONE)", lambda s: repository.list_tasks(s, TaskStatus.DONE))
    run("get_task", lambda s: repository.get_task(s, task_id))

    def update(s: Session) -> Task:
        task = repository.get_task(s, task_id)
        assert task is not None
        return repository.update_task(s, task, TaskPatch(status=TaskStatus.DONE))

    def delete(s: Session) -> None:
        task = repository.get_task(s, task_id)
        assert task is not None
        repository.delete_task(s, task)

    run("get_task + update_task", update)
    run("get_task + delete_task", delete)
    return calls


def main() -> None:
    engine = create_demo_engine()
    print("1. 1件のタスクの一生（状態と、送られた SQL）")
    for label, sql, state in lifecycle(engine):
        print(f"{label}  [{state}]")
        for line in sql:
            print(f"    {line}")

    print("\n2. Repository の関数ごとに送られた SQL")
    for label, sql in repository_calls(engine):
        print(label)
        for line in sql:
            print(f"    {line}")
    engine.dispose()


if __name__ == "__main__":
    main()
