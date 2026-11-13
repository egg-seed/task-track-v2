"""SQLite database configuration for Phase 03 only."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


def build_engine(url: str = "sqlite:///./tasks.db") -> Engine:
    return create_engine(url, connect_args={"check_same_thread": False})


engine = build_engine()


def create_db_and_tables(db_engine: Engine) -> None:
    # Import registers the table with SQLModel's metadata.
    from app.models.task import Task  # noqa: F401

    SQLModel.metadata.create_all(db_engine)


def get_session(request: Request) -> Generator[Session]:
    # Use the same engine selected by create_app(), including in tests.
    db_engine: Engine = request.app.state.db_engine
    with Session(db_engine) as session:
        yield session
