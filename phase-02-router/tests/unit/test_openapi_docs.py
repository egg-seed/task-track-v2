"""What the customised app puts into OpenAPI, and therefore into Swagger UI (Chapter 9)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from tutorials.openapi_docs import create_docs_app


@pytest.fixture
def openapi() -> dict[str, Any]:
    with TestClient(create_docs_app()) as client:
        return client.get("/openapi.json").json()


def test_app_metadata(openapi: dict[str, Any]) -> None:
    info = openapi["info"]
    assert info["title"] == "タスク管理API"
    assert info["summary"] == "カンバン形式でタスクを管理する"
    assert info["version"] == "0.2.0"
    assert "TODO" in info["description"]


def test_tag_descriptions(openapi: dict[str, Any]) -> None:
    assert openapi["tags"] == [
        {"name": "tasks", "description": "タスクの作成・取得・削除"},
        {"name": "health", "description": "稼働状況の確認"},
    ]


def test_operation_texts(openapi: dict[str, Any]) -> None:
    create = openapi["paths"]["/tasks"]["post"]
    assert create["summary"] == "タスクを作成する"
    # The docstring becomes the description shown under the summary.
    assert create["description"].startswith("新しいタスクを作成します。")
    assert create["responses"]["201"]["description"] == "作成したタスク"


def test_field_examples_and_descriptions(openapi: dict[str, Any]) -> None:
    title = openapi["components"]["schemas"]["TaskCreate"]["properties"]["title"]
    assert title["description"] == "タスクの名前"
    assert title["examples"] == ["設計レビューを行う"]


def test_documented_404_matches_behaviour(openapi: dict[str, Any]) -> None:
    get_task = openapi["paths"]["/tasks/{task_id}"]["get"]
    not_found = get_task["responses"]["404"]
    assert not_found["description"] == "指定したタスクが見つからない"
    assert not_found["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorMessage"
    }
    with TestClient(create_docs_app()) as client:
        response = client.get("/tasks/00000000-0000-4000-8000-000000000000")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_deprecated_operation(openapi: dict[str, Any]) -> None:
    assert openapi["paths"]["/todos"]["get"]["deprecated"] is True


def test_docs_can_be_disabled() -> None:
    with TestClient(create_docs_app(show_docs=False)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        # The API itself keeps working.
        assert client.get("/health").json() == {"status": "ok"}
