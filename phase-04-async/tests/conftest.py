"""Each test uses a freshly migrated SQLite database through the async driver."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import build_engine, session_factory
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def migrated_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    # Alembic stays synchronous: it runs once from the CLI, outside the app's event loop.
    url = f"sqlite:///{tmp_path / 'tasks.db'}"
    monkeypatch.setenv("TASKS_DATABASE_URL", url)
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    return url


@pytest.fixture
async def test_engine(migrated_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = build_engine(migrated_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    async with session_factory(test_engine)() as session:
        yield session


@pytest.fixture
async def client(test_engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=create_app(test_engine))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
