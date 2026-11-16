"""Run the Alembic revisions and the async API against a real PostgreSQL database.

These tests run only when TASKS_TEST_POSTGRES_URL is set, for example:

    TASKS_TEST_POSTGRES_URL=postgresql://tasks:devpass@localhost:5432/tasks_test

The database is emptied (downgrade to base) before and after each test, so the
database name must end with "_test" to avoid wiping a real database by mistake.
"""

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import anyio
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import build_engine
from app.main import create_app

POSTGRES_URL = os.environ.get("TASKS_TEST_POSTGRES_URL", "")

pytestmark = [
    pytest.mark.skipif(not POSTGRES_URL, reason="TASKS_TEST_POSTGRES_URL is not set"),
    pytest.mark.anyio,
]


@pytest.fixture
def pg_config(monkeypatch: pytest.MonkeyPatch) -> Generator[Config]:
    database = make_url(POSTGRES_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"refusing to reset database {database!r}: name must end with '_test'")
    monkeypatch.setenv("TASKS_DATABASE_URL", POSTGRES_URL)
    cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield cfg
    command.downgrade(cfg, "base")


@pytest.fixture
async def pg_engine(pg_config: Config) -> AsyncGenerator[AsyncEngine]:
    # The same postgresql:// URL serves Alembic (sync psycopg) and the app (async psycopg).
    engine = build_engine(POSTGRES_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def pg_client(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=create_app(pg_engine))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_async_engine_uses_psycopg(pg_engine: AsyncEngine) -> None:
    assert pg_engine.dialect.driver == "psycopg"
    assert pg_engine.dialect.is_async
    async with pg_engine.connect() as conn:
        assert (await conn.execute(text("SELECT 1"))).scalar_one() == 1


async def test_api_reads_and_writes_postgresql(pg_client: AsyncClient) -> None:
    created = await pg_client.post("/tasks", json={"title": "本番DBの確認", "priority": 3})
    assert created.status_code == 201
    task_id = created.json()["id"]

    fetched = await pg_client.get(f"/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["priority"] == 3
    assert fetched.json()["status"] == "TODO"


async def test_concurrent_requests_share_the_pool(pg_client: AsyncClient) -> None:
    # 30 requests at once exceed the default pool (5 + 10 overflow); they wait for a
    # connection instead of failing, because the pool timeout (30s) is not reached.
    statuses: list[int] = []

    async def create(n: int) -> None:
        response = await pg_client.post("/tasks", json={"title": f"task {n}"})
        statuses.append(response.status_code)

    async with anyio.create_task_group() as tg:
        for n in range(30):
            tg.start_soon(create, n)

    assert statuses == [201] * 30
    assert len((await pg_client.get("/tasks")).json()) == 30
