"""SQLite is isolated per test; requests use the same test Session."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.main import create_app
from app.models.task import Task  # noqa: F401


@pytest.fixture
def test_engine() -> Generator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine: Engine) -> Generator[Session]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine: Engine) -> Generator[TestClient]:
    app = create_app(test_engine)
    # No dependency override: exercise the actual engine selection.
    with TestClient(app) as client:
        yield client
