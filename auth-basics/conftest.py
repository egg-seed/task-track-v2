from collections.abc import Iterator

import pytest

import oauth2_app
from tasks import reset_tasks

ALICE_KEY = "alice-test-key-0123456789abcdef"
BOB_KEY = "bob-test-key-0123456789abcdef"
ALICE_PASSWORD = "alice-test-password"
BOB_PASSWORD = "bob-test-password"


@pytest.fixture(autouse=True)
def demo_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """テストごとに、環境変数・タスク・発行済みトークンを初期状態にする。"""
    monkeypatch.setenv("API_KEYS", f"alice={ALICE_KEY},bob={BOB_KEY}")
    monkeypatch.setenv("DEMO_PASSWORDS", f"alice={ALICE_PASSWORD},bob={BOB_PASSWORD}")
    oauth2_app.user_db.cache_clear()
    oauth2_app.TOKENS.clear()
    reset_tasks()
    yield
    oauth2_app.user_db.cache_clear()
    oauth2_app.TOKENS.clear()
    reset_tasks()
