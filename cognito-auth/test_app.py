"""Offline contract tests: generated keys, no AWS account or credentials required."""

import time
from collections.abc import Callable
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientError

import app as module

ISSUER = "https://cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_demo"

Signer = Callable[..., str]


@pytest.fixture(autouse=True)
def cognito_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITO_REGION", "ap-northeast-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-northeast-1_demo")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "demo-client")


@pytest.fixture
def client() -> TestClient:
    return TestClient(module.app)


@pytest.fixture
def signer(monkeypatch: pytest.MonkeyPatch) -> Signer:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeKey:
        key = private_key.public_key()

    class LocalJwks:
        def get_signing_key_from_jwt(self, _token: str) -> FakeKey:
            return FakeKey()

    monkeypatch.setattr(module, "jwks_client", lambda _issuer: LocalJwks())

    def sign(**changes: Any) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "sub": "alice",
            "client_id": "demo-client",
            "token_use": "access",
            "iat": now,
            "exp": now + 3600,
        }
        claims.update(changes)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "local-test"})

    return sign


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_no_token(client: TestClient) -> None:
    response = client.get("/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_access_token(client: TestClient, signer: Signer) -> None:
    response = client.get("/me", headers=bearer(signer()))
    assert response.status_code == 200
    assert response.json() == {"sub": "alice"}


@pytest.mark.parametrize(
    "changes",
    [
        {"token_use": "id"},
        {"client_id": "other-client"},
        {"iss": "https://attacker.invalid"},
        {"exp": 1},
        {"sub": None},
    ],
)
def test_rejected_claims(client: TestClient, signer: Signer, changes: dict[str, Any]) -> None:
    response = client.get("/me", headers=bearer(signer(**changes)))
    assert response.status_code == 401


def test_invalid_signature(client: TestClient, signer: Signer) -> None:
    header, payload, signature = signer().split(".")
    altered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    altered = ".".join([header, payload, altered_signature])
    response = client.get("/me", headers=bearer(altered))
    assert response.status_code == 401


def test_symmetric_algorithm_is_rejected(client: TestClient, signer: Signer) -> None:
    # A token signed with HS256 must not be accepted even if every claim looks valid.
    now = int(time.time())
    forged = jwt.encode(
        {
            "iss": ISSUER,
            "sub": "alice",
            "client_id": "demo-client",
            "token_use": "access",
            "iat": now,
            "exp": now + 3600,
        },
        "attacker-chosen-secret-with-enough-length",
        algorithm="HS256",
    )
    response = client.get("/me", headers=bearer(forged))
    assert response.status_code == 401


def test_jwks_failure_returns_401(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenJwks:
        def get_signing_key_from_jwt(self, _token: str) -> None:
            raise PyJWKClientError("JWKS endpoint unreachable")

    monkeypatch.setattr(module, "jwks_client", lambda _issuer: BrokenJwks())
    response = client.get("/me", headers=bearer("header.payload.signature"))
    assert response.status_code == 401


def test_owner_access_and_cross_user_denial(client: TestClient, signer: Signer) -> None:
    headers = bearer(signer())
    assert client.get("/users/alice/tasks", headers=headers).status_code == 200
    assert client.get("/users/bob/tasks", headers=headers).status_code == 403


def test_jwks_client_uses_issuer_endpoint() -> None:
    module.jwks_client.cache_clear()
    jwks = module.jwks_client(ISSUER)
    assert jwks.uri == f"{ISSUER}/.well-known/jwks.json"
    assert module.jwks_client(ISSUER) is jwks
