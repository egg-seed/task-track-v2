"""Which error wins when a request has more than one problem (Chapter 25).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.error_order

The requests go through TestClient to an in-memory SQLite database,
so tasks.db is not touched.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.main import create_app
from app.models.task import Task  # noqa: F401

MISSING_ID = uuid4()


def describe(response_json: object) -> str:
    """Summarise a 422 body as the locations FastAPI rejected."""
    if isinstance(response_json, dict) and isinstance(response_json.get("detail"), list):
        return "検証エラー: " + ", ".join(
            ".".join(str(part) for part in error["loc"]) for error in response_json["detail"]
        )
    return str(response_json)


def main() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with TestClient(create_app(engine)) as client:
        task = client.post("/tasks", json={"title": "keep"}).json()
        cases = [
            ("ない ID ＋ 正しい本文", f"/tasks/{MISSING_ID}", {"title": "new"}),
            ("ない ID ＋ 空のタイトル", f"/tasks/{MISSING_ID}", {"title": ""}),
            ("UUID でない ID ＋ 正しい本文", "/tasks/not-a-uuid", {"title": "new"}),
            ("ある ID ＋ 空のタイトル", f"/tasks/{task['id']}", {"title": ""}),
        ]
        for label, path, body in cases:
            response = client.patch(path, json=body)
            print(label)
            print(f"  -> {response.status_code} {describe(response.json())}")
        after = client.get(f"/tasks/{task['id']}").json()
        print(f"\n422 の後のタスク: title={after['title']!r}（作成時と同じ: {after == task}）")
    engine.dispose()


if __name__ == "__main__":
    main()
