"""Send N concurrent requests to /wait and print the elapsed time (Chapter 12 column).

uv run python bench/load.py 100
"""

import asyncio
import sys
import time
from collections import Counter

import httpx

BASE_URL = "http://127.0.0.1:8766"


async def main(n: int) -> None:
    limits = httpx.Limits(max_connections=None)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120, limits=limits) as client:
        await client.get("/wait")  # open the first DB connection before measuring
        started = time.perf_counter()
        responses = await asyncio.gather(*(client.get("/wait") for _ in range(n)))
        elapsed = time.perf_counter() - started
    statuses = Counter(response.status_code for response in responses)
    print(f"{n} requests: {elapsed:.2f}s {dict(statuses)}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
