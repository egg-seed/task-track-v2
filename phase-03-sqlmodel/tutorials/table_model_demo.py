"""Show what a SQLModel table model does, and what it does not do (Chapter 15).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.table_model_demo

Every database here lives in a temporary directory or in memory, so tasks.db is not touched.
"""

import tempfile
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.task import Task


def create_table_sql(engine: Engine) -> str:
    """The CREATE TABLE statement that create_all() sends for the Task model."""
    return str(CreateTable(Task.__table__).compile(engine)).strip()  # type: ignore[attr-defined]


def constructor_skips_validation() -> Task:
    """A table model built with its constructor is not validated."""
    return Task(title="")


def model_validate_rejects(data: dict[str, object]) -> list[str]:
    """model_validate() runs the Field rules and returns the error types."""
    try:
        Task.model_validate(data)
    except ValidationError as exc:
        return [str(error["type"]) for error in exc.errors()]
    return []


def database_accepts_invalid_titles(engine: Engine) -> list[int]:
    """SQLite stores an empty title and a 101-character title; it returns their lengths."""
    with Session(engine) as session:
        session.add_all([Task(title=""), Task(title="x" * 101)])
        session.commit()
        return sorted(len(task.title) for task in session.exec(select(Task)).all())


def survives_restart(db_path: Path) -> list[str]:
    """Write with one engine, dispose it, then read with a new engine (like a restart)."""
    url = f"sqlite:///{db_path}"
    first = create_engine(url)
    SQLModel.metadata.create_all(first)
    with Session(first) as session:
        session.add(Task(title="牛乳を買う"))
        session.commit()
    first.dispose()

    second = create_engine(url)
    with Session(second) as session:
        titles = [task.title for task in session.exec(select(Task)).all()]
    second.dispose()
    return titles


def create_all_keeps_old_columns(engine: Engine) -> list[str]:
    """create_all() skips a table that already exists, even if its columns differ."""
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE task (id CHAR(32) PRIMARY KEY, title VARCHAR)"))
    SQLModel.metadata.create_all(engine)
    return [column["name"] for column in inspect(engine).get_columns("task")]


def main() -> None:
    memory = create_engine("sqlite://")
    SQLModel.metadata.create_all(memory)

    print("1. create_all() が送る CREATE TABLE")
    print(create_table_sql(memory))

    print("\n2. コンストラクタと model_validate()")
    task = constructor_skips_validation()
    print(f"Task(title='') -> 作れた: title={task.title!r}")
    print(f"Task.model_validate({{'title': ''}}) -> {model_validate_rejects({'title': ''})}")

    print("\n3. SQLite は 0文字と101文字のタイトルも保存する")
    print(f"保存されたタイトルの文字数: {database_accepts_invalid_titles(memory)}")
    memory.dispose()

    with tempfile.TemporaryDirectory() as tmp:
        print("\n4. ファイルの DB は Engine を作り直しても残る")
        print(f"読み直したタイトル: {survives_restart(Path(tmp) / 'demo.db')}")

    print("\n5. create_all() は既存のテーブルを変更しない")
    old = create_engine("sqlite://")
    print(f"create_all() 後の列: {create_all_keeps_old_columns(old)}")
    print(f"Task モデルの列: {[column.name for column in Task.__table__.columns]}")  # type: ignore[attr-defined]
    old.dispose()


if __name__ == "__main__":
    main()
