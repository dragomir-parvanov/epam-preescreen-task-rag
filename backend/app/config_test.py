import pytest

from app.config import Settings

DATABASE_URL = "postgresql://rag:hunter2@db.internal:5432/rag"


def test_database_url_comes_from_the_environment_and_is_never_printed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_DATABASE_URL", DATABASE_URL)

    settings = Settings()

    assert settings.database_url.get_secret_value() == DATABASE_URL
    assert "hunter2" not in repr(settings)
