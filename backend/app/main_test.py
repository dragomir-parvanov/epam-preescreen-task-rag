from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_reports_ok() -> None:
    # Default settings without validation or env: the route doesn't depend on them.
    client = TestClient(create_app(Settings.model_construct()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_an_unknown_path_gets_the_not_found_envelope() -> None:
    client = TestClient(create_app(Settings.model_construct()))

    response = client.get("/nowhere", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "There is no such endpoint.",
            "details": None,
            "request_id": "req-404",
        }
    }


def test_a_wrong_method_gets_the_method_not_allowed_envelope() -> None:
    client = TestClient(create_app(Settings.model_construct()))

    response = client.delete("/health", headers={"X-Request-ID": "req-405"})

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "This endpoint doesn't support DELETE.",
            "details": None,
            "request_id": "req-405",
        }
    }
