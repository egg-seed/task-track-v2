"""The order, sharing and OpenAPI output of dependencies (Chapter 12)."""

from fastapi.testclient import TestClient
from tutorials.dependency_flow import create_flow_app, open_store


def test_dependencies_run_in_order_and_cleanup_last() -> None:
    app = create_flow_app()
    with TestClient(app) as client:
        response = client.get("/titles", params={"limit": 2}, headers={"X-Request-ID": "req-1"})
    assert response.status_code == 200
    assert response.json() == {
        "request_id": "req-1",
        "titles": ["設計レビューを行う", "テストを書く"],
        "same_store": True,
    }
    assert app.state.events == [
        "open_store: 準備",
        "get_request_id",
        "get_service",
        "get_limit",
        "list_titles",
        "open_store: 後始末",
    ]


def test_shared_dependency_is_called_once_per_request() -> None:
    app = create_flow_app()
    with TestClient(app) as client:
        client.get("/titles")
        client.get("/titles")
    # open_store is used by get_service and by the route, but runs once per request.
    assert app.state.events.count("open_store: 準備") == 2
    assert app.state.events.count("open_store: 後始末") == 2


def test_dependency_parameters_are_validated() -> None:
    with TestClient(create_flow_app()) as client:
        response = client.get("/titles", params={"limit": 0})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "limit"]


def test_dependency_parameters_appear_in_openapi() -> None:
    with TestClient(create_flow_app()) as client:
        operation = client.get("/openapi.json").json()["paths"]["/titles"]["get"]
    parameters = {p["name"]: p for p in operation["parameters"]}
    assert set(parameters) == {"x-request-id", "limit"}
    assert parameters["x-request-id"]["in"] == "header"
    assert parameters["limit"]["in"] == "query"
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100


def test_override_replaces_the_whole_store() -> None:
    app = create_flow_app()
    app.dependency_overrides[open_store] = lambda: {9: "差し替えたタスク"}
    with TestClient(app) as client:
        response = client.get("/titles")
    app.dependency_overrides.clear()
    assert response.json()["titles"] == ["差し替えたタスク"]
    assert "open_store: 準備" not in app.state.events
