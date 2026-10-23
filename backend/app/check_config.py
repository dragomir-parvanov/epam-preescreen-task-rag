"""Validate the backend config on the host: `pixi run check-config`, which `pixi run up` runs first.

The same `load_settings` the server starts with, so an invalid config prints its fix in the
terminal before any Docker build, instead of being buried in `docker compose logs`.
"""

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    print(f"Config OK: LLM provider {settings.llm_provider}, model {settings.llm_model}")


if __name__ == "__main__":
    main()
