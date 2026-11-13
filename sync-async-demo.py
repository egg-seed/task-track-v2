"""Simple standalone async concurrency demo. Run with Python 3.14."""
import asyncio


async def wait_for_data(item: str) -> str:
    await asyncio.sleep(0.01)
    return item


async def sequential() -> list[str]:
    return [await wait_for_data("A"), await wait_for_data("B")]


async def concurrent() -> list[str]:
    return list(await asyncio.gather(wait_for_data("A"), wait_for_data("B")))


async def main() -> None:
    first = await sequential()
    second = await concurrent()
    assert first == ["A", "B"]
    assert second == ["A", "B"]
    print("sequential:", first)
    print("concurrent:", second)


if __name__ == "__main__":
    asyncio.run(main())
