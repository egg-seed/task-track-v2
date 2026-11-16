"""Send N concurrent requests to /wait and print the elapsed time (Chapter 12 column).

uv run python bench/load.py 100
uv run python bench/load.py 100 --probe   # also time GET /health while /wait is busy
uv run python bench/load.py 100 --dep     # use /wait-dep (sync mode only)
"""

import asyncio
import sys
import time
from collections import Counter

import httpx

BASE_URL = "http://127.0.0.1:8766"


async def probe_health(client: httpx.AsyncClient) -> float:
    await asyncio.sleep(0.2)  # let the /wait requests arrive first
    started = time.perf_counter()
    await client.get("/health")
    return time.perf_counter() - started


async def main(n: int, path: str, probe: bool) -> None:
    limits = httpx.Limits(max_connections=None)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120, limits=limits) as client:
        await client.get(path)  # open the first DB connection before measuring
        started = time.perf_counter()
        waits = asyncio.gather(*(client.get(path) for _ in range(n)))
        health = asyncio.create_task(probe_health(client)) if probe else None
        responses = await waits
        elapsed = time.perf_counter() - started
        health_elapsed = await health if health else None
    statuses = Counter(response.status_code for response in responses)
    print(f"{n} requests: {elapsed:.2f}s {dict(statuses)}")
    if health_elapsed is not None:
        print(f"/health during the load: {health_elapsed:.2f}s")


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    path = "/wait-dep" if "--dep" in sys.argv else "/wait"
    asyncio.run(main(int(args[0]) if args else 100, path, "--probe" in sys.argv))
