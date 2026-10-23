"""The Postgres connection the Passage index lives in (ADR-0004): its timeouts, and the readiness
`database` check."""

from typing import Final

import psycopg
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr

# From operational readiness (#15): fail fast rather than hang; no retries.
CONNECT_TIMEOUT_S: Final = 5
STATEMENT_TIMEOUT_MS: Final = 10_000


def conninfo(database_url: SecretStr) -> str:
    """The connection string, with the connect and statement timeouts applied."""
    return make_conninfo(
        database_url.get_secret_value(),
        connect_timeout=CONNECT_TIMEOUT_S,
        options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
    )


class PostgresPing:
    """The readiness `database` check: `SELECT 1` on a fresh connection."""

    def __init__(self, database_url: SecretStr) -> None:
        self._conninfo = conninfo(database_url)

    async def ping(self) -> None:
        """Returns once Postgres answers; raises `psycopg.Error` when it doesn't."""
        async with await psycopg.AsyncConnection.connect(self._conninfo) as connection:
            await connection.execute("SELECT 1")
