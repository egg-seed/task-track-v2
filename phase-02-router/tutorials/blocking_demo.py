"""What blocks the event loop and what does not (Chapter 14).

An independent example: the Phase 02 app in app/ is not changed.

    uv run fastapi run tutorials/blocking_demo.py
    # in another terminal
    uv run python -m tutorials.blocking_load

Each endpoint waits for WAIT_SECONDS in a different way.
"""

import asyncio
import time

from fastapi import FastAPI

WAIT_SECONDS = 1.0


def create_blocking_app(wait_seconds: float = WAIT_SECONDS) -> FastAPI:
    app = FastAPI(title="Blocking demo")

    @app.get("/sync-sleep")
    def sync_sleep() -> dict[str, str]:
        # FastAPI runs a def endpoint in a worker thread, so the event loop stays free.
        time.sleep(wait_seconds)
        return {"mode": "def + time.sleep"}

    @app.get("/async-blocking")
    async def async_blocking() -> dict[str, str]:
        # Wrong: a synchronous wait inside async def stops the event loop itself.
        time.sleep(wait_seconds)
        return {"mode": "async def + time.sleep"}

    @app.get("/async-sleep")
    async def async_sleep() -> dict[str, str]:
        # The event loop runs other requests while this one waits.
        await asyncio.sleep(wait_seconds)
        return {"mode": "async def + await asyncio.sleep"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_blocking_app()
