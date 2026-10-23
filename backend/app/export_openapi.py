"""Write the app's OpenAPI schema to a file: `python -m app.export_openapi <path>`."""

import json
import sys
from pathlib import Path

from app.config import Settings
from app.main import create_app


def main() -> None:
    # Default settings, so the schema (and the committed TS types) don't depend on a local .env.
    app = create_app(Settings.model_construct())
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main()
