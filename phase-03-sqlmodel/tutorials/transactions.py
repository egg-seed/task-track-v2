"""Experiments on transaction boundaries, rollback and concurrent updates (Chapter 17).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.transactions

Every database here is in memory, so tasks.db is not touched.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import CheckConstraint, CursorResult, func, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.models.task import Task
from app.repositories import task as repository
from app.schemas.task import TaskCreate


class TaskLog(SQLModel, table=True):
    """Tutorial-only table: a record written together with a task. Empty messages are rejected."""

    __tablename__ = "demo_task_log"
    __table_args__ = (CheckConstraint("length(message) > 0", name="message_not_empty"),)

    id: int | None = Field(default=None, primary_key=True)
    task_id: UUID
    message: str


class Note(SQLModel, table=True):
    """Tutorial-only table with a version column for optimistic locking."""

    __tablename__ = "demo_note"

    id: int | None = Field(default=None, primary_key=True)
    body: str
    version: int = Field(default=1)


def create_demo_engine() -> Engine:
    # StaticPool keeps one connection, so every Session sees the same in-memory DB.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def count_tasks(engine: Engine) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(Task)).one()


# 1. Transaction boundaries -------------------------------------------------------


def commit_each_step(engine: Engine) -> tuple[str, int]:
    """Create a task, then its log. Each step commits on its own; the log is invalid."""
    with Session(engine) as session:
        task = repository.create_task(session, TaskCreate(title="牛乳を買う"))  # commits
        try:
            session.add(TaskLog(task_id=task.id, message=""))
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            return type(exc).__name__, count_tasks(engine)
    return "no error", count_tasks(engine)


def commit_once(engine: Engine) -> tuple[str, int]:
    """The same two steps, but committed once at the end."""
    with Session(engine) as session:
        try:
            task = Task.model_validate({"title": "牛乳を買う"})
            session.add(task)
            session.add(TaskLog(task_id=task.id, message=""))
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            return type(exc).__name__, count_tasks(engine)
    return "no error", count_tasks(engine)


# 2. Why rollback() is needed -----------------------------------------------------


def use_after_failed_commit(engine: Engine, *, rollback: bool) -> str:
    """After a failed commit, run one more query with or without rollback()."""
    with Session(engine) as session:
        repository.create_task(session, TaskCreate(title="牛乳を買う"))
        session.add(TaskLog(task_id=UUID(int=0), message=""))
        try:
            session.commit()
        except IntegrityError:
            if rollback:
                session.rollback()
        try:
            total = session.exec(select(func.count()).select_from(Task)).one()
        except PendingRollbackError as exc:
            return type(exc).__name__
        return f"タスク{total}件"


# 3. Lost update and optimistic locking -------------------------------------------


def lost_update(engine: Engine) -> str:
    """Two sessions read the same task, then both append to its title."""
    with Session(engine) as session:
        task = repository.create_task(session, TaskCreate(title="牛乳を買う"))
        task_id = task.id
    with Session(engine) as a, Session(engine) as b:
        task_a = a.get(Task, task_id)
        task_b = b.get(Task, task_id)
        assert task_a is not None and task_b is not None
        task_a.title = task_a.title + "（2本）"
        a.commit()
        task_b.title = task_b.title + "（急ぎ）"
        b.commit()
    with Session(engine) as session:
        final = session.get(Task, task_id)
        assert final is not None
        return final.title


def update_note(session: Session, note_id: int, body: str, read_version: int) -> bool:
    """UPDATE only if nobody changed the row since we read it. False means a conflict."""
    statement = (
        update(Note)
        .where(Note.id == note_id, Note.version == read_version)  # type: ignore[arg-type]
        .values(body=body, version=read_version + 1)
    )
    result: CursorResult[tuple[()]] = session.execute(statement)  # type: ignore[assignment]
    session.commit()
    return result.rowcount == 1


def optimistic_lock(engine: Engine) -> tuple[bool, bool, str, int]:
    """Both sessions read version 1; only the first UPDATE succeeds."""
    with Session(engine) as session:
        note = Note(body="牛乳を買う")
        session.add(note)
        session.commit()
        assert note.id is not None
        note_id, read_version = note.id, note.version
    with Session(engine) as a:
        first = update_note(a, note_id, "牛乳を買う（2本）", read_version)
    with Session(engine) as b:
        second = update_note(b, note_id, "牛乳を買う（急ぎ）", read_version)
    with Session(engine) as session:
        final = session.get(Note, note_id)
        assert final is not None
        return first, second, final.body, final.version


# 4. Turning the conflict into an HTTP response ----------------------------------


class NoteUpdate(BaseModel):
    body: str
    version: int


def create_notes_app(engine: Engine) -> FastAPI:
    app = FastAPI()

    @app.patch("/notes/{note_id}")
    def patch_note(note_id: int, data: NoteUpdate) -> dict[str, object]:
        with Session(engine) as session:
            if session.get(Note, note_id) is None:
                raise HTTPException(status_code=404, detail="Note not found")
            if not update_note(session, note_id, data.body, data.version):
                raise HTTPException(status_code=409, detail="Note was changed by someone else")
            note = session.get(Note, note_id)
            assert note is not None
            return {"body": note.body, "version": note.version}

    return app


def http_conflict(engine: Engine) -> list[tuple[int, object]]:
    with Session(engine) as session:
        note = Note(body="原稿を書く")
        session.add(note)
        session.commit()
        note_id = note.id
    client = TestClient(create_notes_app(engine))
    responses = [
        client.patch(f"/notes/{note_id}", json={"body": "原稿を書く（下書き）", "version": 1}),
        client.patch(f"/notes/{note_id}", json={"body": "原稿を書く（清書）", "version": 1}),
    ]
    return [(r.status_code, r.json()) for r in responses]


def run(label: str, action: Callable[[Engine], object]) -> None:
    engine = create_demo_engine()
    print(f"{label}: {action(engine)}")
    engine.dispose()


def main() -> None:
    print("1. タスクを作り、続けて作成記録を作る（作成記録は CHECK 制約で失敗する）")
    run("処理ごとに commit（エラー, 残ったタスク数）", commit_each_step)
    run("最後にまとめて commit（エラー, 残ったタスク数）", commit_once)

    print("\n2. commit に失敗した Session で、もう一度問い合わせる")
    run("rollback しない", lambda e: use_after_failed_commit(e, rollback=False))
    run("rollback する", lambda e: use_after_failed_commit(e, rollback=True))

    print("\n3. 2つの Session が同じタスクを読んでから、それぞれ更新する")
    run("そのまま更新した結果", lost_update)
    run("version 列で確かめる（1つ目, 2つ目, 本文, version）", optimistic_lock)

    print("\n4. 同じ version で2回 PATCH する")
    run("応答", http_conflict)


if __name__ == "__main__":
    main()
