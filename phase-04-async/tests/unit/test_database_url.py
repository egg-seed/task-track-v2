"""Which environment variable decides the database URL."""

import pytest

from app.db.session import DEFAULT_DATABASE_URL, async_database_url, database_url


def test_defaults_to_local_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TASKS_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == DEFAULT_DATABASE_URL


def test_uses_database_url_from_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TASKS_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/neondb")
    assert database_url() == "postgresql://u:p@db.example/neondb"


def test_tasks_database_url_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKS_DATABASE_URL", "sqlite:///./other.db")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/neondb")
    assert database_url() == "sqlite:///./other.db"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite:///./tasks.db", "sqlite+aiosqlite:///./tasks.db"),
        (
            "postgresql://u:p@db.example/neondb?sslmode=require&channel_binding=require",
            "postgresql+psycopg://u:p@db.example/neondb?channel_binding=require&sslmode=require",
        ),
        ("postgresql+psycopg://u:p@db.example/app", "postgresql+psycopg://u:p@db.example/app"),
        ("postgresql://u:p%40ss@db.example/app", "postgresql+psycopg://u:p%40ss@db.example/app"),
    ],
)
def test_async_database_url_selects_async_driver(url: str, expected: str) -> None:
    assert async_database_url(url) == expected


def test_async_database_url_rejects_unknown_database() -> None:
    with pytest.raises(ValueError, match="unsupported database"):
        async_database_url("mysql://u:p@db.example/app")
