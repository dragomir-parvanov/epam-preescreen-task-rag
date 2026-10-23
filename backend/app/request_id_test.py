import re
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

type LogLines = Callable[[], list[dict[str, Any]]]

NGINX_ID = "0f8b3c6a9d2e4f1a8b7c6d5e4f3a2b1c"  # what nginx's $request_id looks like


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings.model_construct()), raise_server_exceptions=False)


def test_the_proxys_request_id_is_echoed_and_logged(
    client: TestClient, captured_logs: LogLines
) -> None:
    response = client.get("/articles/nope", headers={"X-Request-ID": NGINX_ID})

    assert response.headers["x-request-id"] == NGINX_ID
    [access] = [line for line in captured_logs() if line["event"] == "request_completed"]
    assert access["request_id"] == NGINX_ID


def test_a_direct_call_gets_a_fresh_id(client: TestClient) -> None:
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]

    assert re.fullmatch(r"[0-9a-f]{32}", first)
    assert first != second


@pytest.mark.parametrize(
    "bad_id", ["", "x" * 129, "<script>", 'a"b', "a b"], ids=["empty", "long", "tag", "q", "sp"]
)
def test_an_implausible_incoming_id_is_replaced_rather_than_trusted(
    client: TestClient, bad_id: str
) -> None:
    response = client.get("/health", headers={"X-Request-ID": bad_id})

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_each_request_gets_one_access_line(client: TestClient, captured_logs: LogLines) -> None:
    client.post("/chat", json={"question": ""}, headers={"X-Request-ID": NGINX_ID})

    [access] = [line for line in captured_logs() if line["event"] == "request_completed"]
    assert access["level"] == "info"
    assert access["method"] == "POST"
    assert access["path"] == "/chat"
    assert access["status"] == 422
    assert isinstance(access["duration_ms"], float)
    assert access["duration_ms"] >= 0


def test_a_successful_probe_is_not_logged_at_info(
    client: TestClient, captured_logs: LogLines
) -> None:
    # The Compose healthcheck polls every few seconds; a failing probe is still logged.
    client.get("/health")

    assert [line for line in captured_logs() if line["event"] == "request_completed"] == []


def test_an_unexpected_500_still_carries_the_id(captured_logs: LogLines) -> None:
    app = create_app(Settings.model_construct())

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    response = TestClient(app, raise_server_exceptions=False).get(
        "/boom", headers={"X-Request-ID": NGINX_ID}
    )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == NGINX_ID
    assert response.json()["error"]["request_id"] == NGINX_ID
    [access] = [line for line in captured_logs() if line["event"] == "request_completed"]
    assert access["status"] == 500
    assert access["request_id"] == NGINX_ID
