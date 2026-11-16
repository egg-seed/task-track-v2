"""How FastAPI resolves dependencies: order, sharing, yield and OpenAPI (Chapter 12).

An independent example: the Phase 02 app in app/ is not changed.

    uv run fastapi dev tutorials/dependency_flow.py

Each dependency prints a line, so the terminal shows the order in which FastAPI calls them.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Query, Request

Store = dict[int, str]


def record(request: Request, message: str) -> None:
    """Print a step and keep it in app.state.events so that tests can read the order."""
    print(message, flush=True)
    request.app.state.events.append(message)


def open_store(request: Request) -> Iterator[Store]:
    record(request, "open_store: 準備")
    try:
        yield request.app.state.store
    finally:
        record(request, "open_store: 後始末")


StoreDep = Annotated[Store, Depends(open_store)]


def get_request_id(
    request: Request,
    x_request_id: Annotated[str | None, Header(description="リクエストを識別するID")] = None,
) -> str:
    record(request, "get_request_id")
    return x_request_id or "-"


RequestIdDep = Annotated[str, Depends(get_request_id)]


def get_limit(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100, description="返す件数の上限")] = 20,
) -> int:
    record(request, "get_limit")
    return limit


LimitDep = Annotated[int, Depends(get_limit)]


@dataclass(frozen=True)
class TitleService:
    store: Store
    request_id: str

    def titles(self, limit: int) -> list[str]:
        return list(self.store.values())[:limit]


def get_service(request: Request, store: StoreDep, request_id: RequestIdDep) -> TitleService:
    record(request, "get_service")
    return TitleService(store=store, request_id=request_id)


ServiceDep = Annotated[TitleService, Depends(get_service)]


def create_flow_app() -> FastAPI:
    app = FastAPI(title="Dependency flow")
    app.state.events = []
    app.state.store = {1: "設計レビューを行う", 2: "テストを書く", 3: "デプロイする"}

    @app.get("/titles")
    def list_titles(
        request: Request,
        service: ServiceDep,
        store: StoreDep,
        limit: LimitDep,
    ) -> dict[str, object]:
        record(request, "list_titles")
        return {
            "request_id": service.request_id,
            "titles": service.titles(limit),
            "same_store": service.store is store,
        }

    return app


app = create_flow_app()
