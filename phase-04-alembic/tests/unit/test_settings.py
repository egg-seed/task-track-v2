"""Settings: sources, precedence, validation, and keeping secrets out of output (Chapter 24)."""

import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import DEFAULT_DATABASE_URL, Settings

NEON_URL = "postgresql://neondb_owner:hunter2@ep-example.neon.tech/neondb?sslmode=require"
PHASE_DIR = Path(__file__).parents[2]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None]:
    # Start every test without TASKS_* / DATABASE_URL and without a developer's .env file.
    for name in (
        "TASKS_ENV",
        "TASKS_DATABASE_URL",
        "DATABASE_URL",
        "TASKS_LOG_LEVEL",
        "TASKS_CORS_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    yield


def test_defaults_for_local_development() -> None:
    settings = Settings()
    assert settings.env == "development"
    assert settings.log_level == "INFO"
    assert settings.resolved_database_url() == DEFAULT_DATABASE_URL


def test_password_is_hidden_in_repr_and_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", NEON_URL)
    settings = Settings()
    assert "hunter2" not in repr(settings)
    assert "hunter2" not in str(settings)
    assert settings.resolved_database_url() == NEON_URL


def test_empty_tasks_database_url_falls_back_to_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TASKS_DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL", NEON_URL)
    assert Settings().resolved_database_url() == NEON_URL


def test_dotenv_file_is_read_and_environment_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("TASKS_LOG_LEVEL=DEBUG\nTASKS_DATABASE_URL=sqlite:///./dev.db\n")
    assert Settings().log_level == "DEBUG"
    monkeypatch.setenv("TASKS_LOG_LEVEL", "WARNING")
    settings = Settings()
    assert settings.log_level == "WARNING"
    assert settings.resolved_database_url() == "sqlite:///./dev.db"


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKS_LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError, match="log_level"):
        Settings()


def test_production_requires_a_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKS_ENV", "production")
    with pytest.raises(ValidationError, match="required in production"):
        Settings()


def test_production_rejects_sqlite_without_echoing_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TASKS_ENV", "production")
    monkeypatch.setenv("TASKS_DATABASE_URL", "sqlite:///./hunter2.db")
    with pytest.raises(ValidationError, match="SQLite is for local development") as error:
        Settings()
    assert "hunter2" not in str(error.value)


def test_production_accepts_a_server_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKS_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", NEON_URL)
    assert Settings().resolved_database_url() == NEON_URL


def test_app_refuses_to_start_in_production_without_database(tmp_path: Path) -> None:
    # Import the app in a fresh process, as `fastapi run` would.
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=PHASE_DIR,
        env={"PATH": "", "TASKS_ENV": "production"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "required in production" in result.stderr


def test_cors_origins_default_and_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings().cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    monkeypatch.setenv("TASKS_CORS_ORIGINS", '["https://kanban.example.com"]')
    assert Settings().cors_origins == ["https://kanban.example.com"]
