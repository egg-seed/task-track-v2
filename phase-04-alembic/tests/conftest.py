"""Each test uses a freshly migrated SQLite database."""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.main import create_app


@pytest.fixture
def test_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Engine]:
    db_path = tmp_path / "tasks.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("TASKS_DATABASE_URL", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine: Engine) -> Generator[Session]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client(test_engine: Engine) -> Generator[TestClient]:
    app = create_app(test_engine)
    with TestClient(app) as test_client:
        yield test_client
