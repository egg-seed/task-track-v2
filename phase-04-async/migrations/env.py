"""Alembic environment with the same DB URL as the FastAPI app.

Migrations stay synchronous even though the app is async: psycopg (v3) has both APIs,
so the same postgresql:// URL works here, and sqlite:// uses the built-in sqlite3.
"""

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.db.session import database_url
from app.models.task import Task  # noqa: F401

config = context.config
# ConfigParser treats "%" as interpolation, so escape it (e.g. URL-encoded passwords).
config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
