# Phase 01 learning image. Production hardening comes in a later chapter.
FROM python:3.14-slim

# Pin uv to keep the build tool reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /code

# Install locked runtime dependencies before copying frequently edited code.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY app/ ./app/
EXPOSE 8000

CMD ["/code/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
