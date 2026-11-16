# Phase 04 production image (Chapter 27): multi-stage build, non-root user.

# --- Stage 1: build the virtual environment with uv -------------------------
FROM python:3.14-slim AS builder

# Pin uv to keep the build tool reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv

# Compile .pyc at build time; copy files instead of linking from uv's cache;
# use the image's Python instead of downloading one.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Only the dependencies are built here; the app code is copied in the runtime stage.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

# --- Stage 2: runtime image without uv or build caches ----------------------
# Must be the same base image as the builder: .venv points to its Python.
FROM python:3.14-slim

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /app
# The virtual environment and the code are separate layers: a code change
# rebuilds only the small code layers, not the ~140 MB environment.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app pyproject.toml alembic.ini ./
COPY --chown=app:app migrations/ ./migrations/
COPY --chown=app:app app/ ./app/
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

USER app
EXPOSE 8000

# Liveness only: /health does not touch the database (Chapter 31).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Exec form: fastapi is PID 1 and receives SIGTERM from `docker stop` directly.
CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
