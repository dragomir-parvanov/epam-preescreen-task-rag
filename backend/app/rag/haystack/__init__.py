"""The Haystack adapter: the only package that imports Haystack (ADR-0003).

Haystack 3.x only. It reads HAYSTACK_TELEMETRY_ENABLED once, when it is first imported, so the
opt-out is set here, before any submodule imports it. An explicit value in the environment wins.
"""

import os

os.environ.setdefault("HAYSTACK_TELEMETRY_ENABLED", "False")
