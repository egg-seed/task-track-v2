"""Why call external APIs asynchronously: measure it (Chapter 22).

An independent example: the Phase 02 app in app/ is not changed.

    uv run python -m tutorials.external_wait

The script starts two servers on 127.0.0.1 in background threads:

- a slow "external API" that answers GET /tasks/{id} after WAIT_SECONDS
- our app, which calls that API in different ways

Nothing is sent to the internet.
"""

import asyncio
import socket
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from tutorials.httpx_client import RemoteTask, fetch_task

WAIT_SECONDS = 1.0
TASK_IDS = (1, 2, 3)
PROBE_DELAY = 0.1
MANY_REQUESTS = 50  # More than the 40 worker threads FastAPI uses for def endpoints.


def create_upstream_app(wait_seconds: float = WAIT_SECONDS) -> FastAPI:
    """A stand-in for a slow external service."""
    upstream = FastAPI(title="Slow external API")

    @upstream.get("/tasks/{task_id}")
    async def read_task(task_id: int) -> dict[str, int | str]:
        await asyncio.sleep(wait_seconds)
        return {"id": task_id, "title": f"task {task_id}"}

    return upstream


def create_app(upstream_url: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # One AsyncClient for the whole app, closed when the app stops (Chapter 13).
        async with httpx.AsyncClient(base_url=upstream_url, timeout=10.0) as client:
            app.state.client = client
            yield

    app = FastAPI(title="External wait demo", lifespan=lifespan)

    # 1. One request that needs three external calls --------------------------------

    @app.get("/summary/one-by-one")
    async def summary_one_by_one() -> list[RemoteTask]:
        # Each await finishes before the next call starts.
        return [await fetch_task(app.state.client, task_id) for task_id in TASK_IDS]

    @app.get("/summary/gather")
    async def summary_gather() -> list[RemoteTask]:
        # Start all three calls, then wait for them together.
        calls = [fetch_task(app.state.client, task_id) for task_id in TASK_IDS]
        return list(await asyncio.gather(*calls))

    # 2. Many requests, each with one external call ---------------------------------

    @app.get("/blocking/{task_id}")
    async def blocking(task_id: int) -> RemoteTask:
        # Wrong: a synchronous client inside async def stops the event loop while it waits.
        with httpx.Client(base_url=upstream_url, timeout=10.0) as client:
            response = client.get(f"/tasks/{task_id}")
        return RemoteTask.model_validate(response.json())

    @app.get("/threaded/{task_id}")
    def threaded(task_id: int) -> RemoteTask:
        # A def endpoint runs in a worker thread, so the synchronous wait is acceptable.
        with httpx.Client(base_url=upstream_url, timeout=10.0) as client:
            response = client.get(f"/tasks/{task_id}")
        return RemoteTask.model_validate(response.json())

    @app.get("/awaiting/{task_id}")
    async def awaiting(task_id: int) -> RemoteTask:
        # The event loop serves other requests while this one waits.
        return await fetch_task(app.state.client, task_id)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Running the servers and measuring ---------------------------------------------------


def start_server(app: FastAPI) -> tuple[uvicorn.Server, threading.Thread, str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    return server, thread, f"http://127.0.0.1:{port}"


def stop_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    server.should_exit = True
    thread.join()


async def timed_get(client: httpx.AsyncClient, path: str, origin: float) -> tuple[float, float]:
    started = time.perf_counter() - origin
    response = await client.get(path)
    response.raise_for_status()
    return started, time.perf_counter() - origin


async def probe(client: httpx.AsyncClient, origin: float) -> tuple[float, float]:
    """Call /health shortly after the slow requests, to see whether our app still answers."""
    await asyncio.sleep(PROBE_DELAY)
    return await timed_get(client, "/health", origin)


async def one_request(client: httpx.AsyncClient, path: str) -> float:
    origin = time.perf_counter()
    _, ended = await timed_get(client, path, origin)
    return ended


async def three_requests(
    client: httpx.AsyncClient, prefix: str
) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    origin = time.perf_counter()
    slow = [timed_get(client, f"{prefix}/{task_id}", origin) for task_id in TASK_IDS]
    *results, health = await asyncio.gather(*slow, probe(client, origin))
    return results, health


async def many_requests(client: httpx.AsyncClient, prefix: str) -> list[float]:
    """Return when each request finished, earliest first."""
    origin = time.perf_counter()
    calls = [timed_get(client, f"{prefix}/{number}", origin) for number in range(MANY_REQUESTS)]
    results = await asyncio.gather(*calls)
    return sorted(end for _, end in results)


async def measure(base_url: str) -> None:
    async with httpx.AsyncClient(
        base_url=base_url, timeout=30.0, limits=httpx.Limits(max_connections=MANY_REQUESTS)
    ) as client:
        await client.get("/health")  # Warm up the connection pool.

        print(f"1. 1件のリクエストで、{WAIT_SECONDS:.0f}秒かかる外部APIを3回呼ぶ")
        for path in ("/summary/one-by-one", "/summary/gather"):
            print(f"   {path:<20} {await one_request(client, path):.2f}s")

        print(f"\n2. 外部APIを1回呼ぶリクエストを3件同時に送り、{PROBE_DELAY}秒後に /health も呼ぶ")
        for prefix in ("/blocking", "/threaded", "/awaiting"):
            results, health = await three_requests(client, prefix)
            print(f"   {prefix}  total {max(end for _, end in results):.2f}s")
            for number, (started, ended) in enumerate(results, start=1):
                print(f"     request {number}: {started:.2f}s -> {ended:.2f}s")
            print(f"     /health   : {health[0]:.2f}s -> {health[1]:.2f}s")

        print(f"\n3. 外部APIを1回呼ぶリクエストを{MANY_REQUESTS}件同時に送る")
        limit = WAIT_SECONDS * 1.5
        for prefix in ("/threaded", "/awaiting"):
            ends = await many_requests(client, prefix)
            early = sum(end < limit for end in ends)
            print(
                f"   {prefix:<10} total {ends[-1]:.2f}s"
                f"（{limit:.1f}秒までに終わった件数: {early}件）"
            )


def main() -> None:
    upstream, upstream_thread, upstream_url = start_server(create_upstream_app())
    app, app_thread, app_url = start_server(create_app(upstream_url))
    try:
        asyncio.run(measure(app_url))
    finally:
        stop_server(app, app_thread)
        stop_server(upstream, upstream_thread)


if __name__ == "__main__":
    main()
