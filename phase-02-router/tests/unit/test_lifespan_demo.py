"""Lifespan runs around the whole app, not around each request (Chapter 13)."""

import pytest
from fastapi.testclient import TestClient
from tutorials.lifespan_demo import create_lifespan_app


def test_lifespan_runs_once_around_requests(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_lifespan_app()) as client:
        assert capsys.readouterr().out == "アプリを開始します\n"
        assert client.get("/titles").json() == ["設計レビューを行う"]
        assert client.post("/titles", json={"title": "テストを書く"}).status_code == 201
        # The list made in lifespan is shared by later requests.
        assert client.get("/titles").json() == ["設計レビューを行う", "テストを書く"]
        assert capsys.readouterr().out == ""
    assert capsys.readouterr().out == "アプリを終了します（タイトル2件）\n"


def test_without_with_lifespan_does_not_run() -> None:
    client = TestClient(create_lifespan_app())
    with pytest.raises(AttributeError, match="titles"):
        client.get("/titles")
