"""Send 3 requests at once to each endpoint of blocking_demo.py and print a timeline (Chapter 14).

Start the demo first:

    uv run fastapi run tutorials/blocking_demo.py

Then, in another terminal:

    uv run python -m tutorials.blocking_load
"""

import asyncio
import os
import time

import httpx

BASE_URL = os.environ.get("BLOCKING_DEMO_URL", "http://127.0.0.1:8000")
PATHS = ["/sync-sleep", "/async-blocking", "/async-sleep"]
REQUESTS = 3
PROBE_DELAY = 0.1


async def timed_get(client: httpx.AsyncClient, path: str, origin: float) -> tuple[float, float]:
    started = time.perf_counter() - origin
    response = await client.get(path)
    response.raise_for_status()
    return started, time.perf_counter() - origin


async def probe(client: httpx.AsyncClient, origin: float) -> tuple[float, float]:
    """Call /health shortly after the slow requests, to see whether the server still answers."""
    await asyncio.sleep(PROBE_DELAY)
    return await timed_get(client, "/health", origin)


async def measure(client: httpx.AsyncClient, path: str) -> None:
    origin = time.perf_counter()
    slow = [timed_get(client, path, origin) for _ in range(REQUESTS)]
    *results, health = await asyncio.gather(*slow, probe(client, origin))
    print(f"{path}  total {max(end for _, end in results):.2f}s")
    for number, (started, ended) in enumerate(results, start=1):
        print(f"  request {number}: {started:.2f}s -> {ended:.2f}s")
    print(f"  /health   : {health[0]:.2f}s -> {health[1]:.2f}s")


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        await client.get("/health")  # Warm up the connection pool.
        for path in PATHS:
            await measure(client, path)


if __name__ == "__main__":
    asyncio.run(main())
