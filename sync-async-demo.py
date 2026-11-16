"""Simple standalone async concurrency demo. Run with Python 3.14."""

import asyncio
import time

WAIT_SECONDS = 0.5


async def wait_for_data(item: str) -> str:
    await asyncio.sleep(WAIT_SECONDS)  # Pretend to wait for I/O, such as a network response.
    return item


async def sequential() -> list[str]:
    return [await wait_for_data("A"), await wait_for_data("B")]


async def concurrent() -> list[str]:
    return list(await asyncio.gather(wait_for_data("A"), wait_for_data("B")))


async def main() -> None:
    started = time.perf_counter()
    first = await sequential()
    middle = time.perf_counter()
    second = await concurrent()
    finished = time.perf_counter()
    assert first == ["A", "B"]
    assert second == ["A", "B"]
    print(f"sequential: {first} {middle - started:.2f}s")
    print(f"concurrent: {second} {finished - middle:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
