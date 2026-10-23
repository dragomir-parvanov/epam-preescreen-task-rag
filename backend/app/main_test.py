from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_reports_ok() -> None:
    # Default settings without validation or env: the route doesn't depend on them.
    client = TestClient(create_app(Settings.model_construct()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
