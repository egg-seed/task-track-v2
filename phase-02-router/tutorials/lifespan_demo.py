"""Run code when the app starts and stops, and hand values to requests (Chapter 13).

An independent example: the Phase 02 app in app/ is not changed.

    uv run fastapi dev tutorials/lifespan_demo.py

Stop the server with Ctrl+C to see the shutdown message.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict, cast

from fastapi import Depends, FastAPI, Request, status
from pydantic import BaseModel, Field


class LifespanState(TypedDict):
    titles: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[LifespanState]:
    print("アプリを開始します", flush=True)
    titles = ["設計レビューを行う"]
    try:
        # Values in this dict are copied to request.state for every request.
        yield {"titles": titles}
    finally:
        print(f"アプリを終了します（タイトル{len(titles)}件）", flush=True)


def get_titles(request: Request) -> list[str]:
    return cast(list[str], request.state.titles)


TitlesDep = Annotated[list[str], Depends(get_titles)]


class TitleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


def create_lifespan_app() -> FastAPI:
    app = FastAPI(title="Lifespan demo", lifespan=lifespan)

    @app.get("/titles")
    def list_titles(titles: TitlesDep) -> list[str]:
        return titles

    @app.post("/titles", status_code=status.HTTP_201_CREATED)
    def add_title(data: TitleCreate, titles: TitlesDep) -> list[str]:
        titles.append(data.title)
        return titles

    return app


app = create_lifespan_app()
