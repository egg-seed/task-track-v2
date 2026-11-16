import pytest
from fastapi.testclient import TestClient

import oauth2_app
from conftest import ALICE_PASSWORD, BOB_PASSWORD
from oauth2_app import app

client = TestClient(app)


def login(username: str, password: str) -> str:
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    return str(body["access_token"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_bearer_token() -> None:
    token = login("alice", ALICE_PASSWORD)

    assert client.get("/me", headers=bearer(token)).json() == {"user": "alice"}


@pytest.mark.parametrize(
    ("username", "password"),
    [("alice", "wrong-password"), ("nobody", ALICE_PASSWORD), ("alice", BOB_PASSWORD)],
)
def test_wrong_credentials_return_401(username: str, password: str) -> None:
    response = client.post("/token", data={"username": username, "password": password})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_token_endpoint_requires_form_fields() -> None:
    assert client.post("/token", data={"username": "alice"}).status_code == 422


def test_password_is_not_stored_in_plain_text() -> None:
    user = oauth2_app.user_db()["alice"]

    assert ALICE_PASSWORD.encode() not in user.password_hash
    assert user.password_hash == oauth2_app.hash_password(ALICE_PASSWORD, user.salt)


def test_missing_token_returns_401() -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_token_returns_401() -> None:
    response = client.get("/me", headers=bearer("not-issued"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_expired_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    token = login("alice", ALICE_PASSWORD)
    issued_at = oauth2_app.time.monotonic()
    monkeypatch.setattr(
        oauth2_app.time, "monotonic", lambda: issued_at + oauth2_app.TOKEN_TTL_SECONDS + 1
    )

    assert client.get("/me", headers=bearer(token)).status_code == 401
    assert token not in oauth2_app.TOKENS


def test_task_list_contains_only_own_tasks() -> None:
    token = login("bob", BOB_PASSWORD)

    assert [task["owner"] for task in client.get("/tasks", headers=bearer(token)).json()] == ["bob"]


def test_created_task_belongs_to_authenticated_user() -> None:
    token = login("alice", ALICE_PASSWORD)

    response = client.post("/tasks", json={"title": "新しいタスク"}, headers=bearer(token))

    assert response.status_code == 201
    assert response.json()["owner"] == "alice"


def test_other_users_task_returns_403() -> None:
    token = login("alice", ALICE_PASSWORD)

    assert client.get("/tasks/1", headers=bearer(token)).status_code == 200
    assert client.get("/tasks/2", headers=bearer(token)).status_code == 403


def test_openapi_declares_password_flow() -> None:
    """Swagger UIは tokenUrl を使って、ユーザー名とパスワードの入力欄を表示する。"""
    schemes = app.openapi()["components"]["securitySchemes"]

    assert schemes["OAuth2PasswordBearer"] == {
        "type": "oauth2",
        "flows": {"password": {"scopes": {}, "tokenUrl": "token"}},
    }
