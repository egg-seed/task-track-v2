import pytest
from fastapi.testclient import TestClient

from api_key_app import app
from conftest import ALICE_KEY, BOB_KEY

client = TestClient(app)


def auth(key: str) -> dict[str, str]:
    return {"X-API-Key": key}


def test_missing_api_key_returns_401() -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "APIKey"


@pytest.mark.parametrize("key", ["wrong", ""])
def test_invalid_api_key_returns_401(key: str) -> None:
    response = client.get("/me", headers=auth(key))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "APIKey"


def test_non_ascii_api_key_returns_401_not_500() -> None:
    """compare_digest に文字列のまま渡すと、ASCII以外の文字で TypeError（500）になる。"""
    response = client.get("/me", headers=[(b"X-API-Key", "キー".encode())])

    assert response.status_code == 401


def test_no_keys_configured_rejects_every_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEYS")

    assert client.get("/me", headers=auth(ALICE_KEY)).status_code == 401


def test_valid_api_key_identifies_client() -> None:
    assert client.get("/me", headers=auth(ALICE_KEY)).json() == {"client": "alice"}
    assert client.get("/me", headers=auth(BOB_KEY)).json() == {"client": "bob"}


def test_task_list_contains_only_own_tasks() -> None:
    response = client.get("/tasks", headers=auth(ALICE_KEY))

    assert response.status_code == 200
    assert [task["owner"] for task in response.json()] == ["alice"]


def test_created_task_belongs_to_authenticated_client() -> None:
    response = client.post("/tasks", json={"title": "新しいタスク"}, headers=auth(BOB_KEY))

    assert response.status_code == 201
    assert response.json() == {"id": 3, "title": "新しいタスク", "owner": "bob"}


def test_owner_can_read_own_task() -> None:
    response = client.get("/tasks/1", headers=auth(ALICE_KEY))

    assert response.status_code == 200
    assert response.json()["owner"] == "alice"


def test_other_clients_task_returns_403() -> None:
    """認証には成功しているが、他人のタスクを操作する権限はない（認可の失敗）。"""
    response = client.get("/tasks/2", headers=auth(ALICE_KEY))

    assert response.status_code == 403


def test_missing_task_returns_404() -> None:
    assert client.get("/tasks/999", headers=auth(ALICE_KEY)).status_code == 404


def test_openapi_declares_api_key_security_scheme() -> None:
    """Swagger UIの Authorize ボタンは、この宣言をもとに表示される。"""
    schema = app.openapi()

    assert schema["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "発行済みのAPIキー",
    }
    assert schema["paths"]["/tasks"]["get"]["security"] == [{"APIKeyHeader": []}]
    # 401/403/404 を宣言しているので、Swagger UI で Undocumented と表示されない
    assert {"401", "403", "404"} <= set(schema["paths"]["/tasks/{task_id}"]["get"]["responses"])
