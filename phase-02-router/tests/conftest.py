"""Shared fixtures for HTTP request tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient]:
    # Isolate application state in every test.
    with TestClient(create_app()) as test_client:
        yield test_client
