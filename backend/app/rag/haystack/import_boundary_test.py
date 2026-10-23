import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
ADAPTER = Path(__file__).resolve().parent

_HAYSTACK_IMPORT = re.compile(r"^\s*(?:from|import)\s+haystack(?:_integrations)?\b", re.MULTILINE)


def test_nothing_outside_the_adapter_package_imports_haystack() -> None:
    importers = [
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if not path.is_relative_to(ADAPTER) and _HAYSTACK_IMPORT.search(path.read_text())
    ]

    assert importers == []
