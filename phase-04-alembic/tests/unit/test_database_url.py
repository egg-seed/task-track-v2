"""Which environment variable decides the database URL."""

import pytest

from app.db.session import DEFAULT_DATABASE_URL, database_url


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
