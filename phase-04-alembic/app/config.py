"""Typed settings read from environment variables and an optional .env file (Chapter 24)."""

from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"
# Where the Kanban frontend (frontend/, Chapter 1) runs during local development.
DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TASKS_",
        env_file=".env",
        # TASKS_DATABASE_URL="" counts as "not set", not as an empty URL.
        env_ignore_empty=True,
        extra="ignore",
        # Validation errors would otherwise echo the input, including the DB password.
        hide_input_in_errors=True,
    )

    env: Literal["development", "test", "production"] = "development"
    # TASKS_DATABASE_URL first, then DATABASE_URL (set by FastAPI Cloud's Neon integration).
    # SecretStr hides the value in repr() and logs: the URL contains the password.
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("TASKS_DATABASE_URL", "DATABASE_URL"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    # Origins whose browser JavaScript may call this API (Chapter 18). JSON list in the env var:
    # TASKS_CORS_ORIGINS='["https://kanban.example.com"]'
    cors_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))

    @model_validator(mode="after")
    def check_production_database(self) -> Self:
        # Fail at startup instead of silently writing to a throwaway SQLite file.
        if self.env != "production":
            return self
        if self.database_url is None:
            raise ValueError("TASKS_DATABASE_URL (or DATABASE_URL) is required in production")
        if self.database_url.get_secret_value().startswith("sqlite"):
            raise ValueError("SQLite is for local development; use a server database in production")
        return self

    def resolved_database_url(self) -> str:
        if self.database_url is None:
            return DEFAULT_DATABASE_URL
        return self.database_url.get_secret_value()


def load_settings() -> Settings:
    # Not cached: Alembic and the tests change environment variables between calls.
    return Settings()
