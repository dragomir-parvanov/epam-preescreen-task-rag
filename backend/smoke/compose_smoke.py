"""The Compose smoke test: `pixi run smoke`, which CI's `smoke` job runs too.

Starts the real stack with `pixi run up` under the keyless `fake` LLM provider (the real image,
Knowledge Base mount, embedder, index and `ChatService`; only the LLM is canned), then checks it
through nginx, as the browser sees it:

- `GET /api/ready` is 200;
- `GET /api/articles` lists every Article in `knowledge-base/`;
- `POST /api/chat` streams `passages` before `done`, frame by frame rather than in one buffered
  flush, and ends in an Answer citing the top-ranked Passage;
- a Follow-up is rewritten first, and the fake's Refusal sentinel ends in a Refusal with no
  `token` streamed.

It runs as its own Compose project on its own ports, from a fresh database volume, so it never
touches a dev stack; it dumps the logs on failure and always removes the stack and its volume.
"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

import httpx

from app.fake_chat_model import FAKE_REFUSAL_TRIGGER
from app.knowledge_base import KNOWLEDGE_BASE_DIR, load_articles

REPO_ROOT: Final = Path(__file__).resolve().parents[2]

SMOKE_ENV: Final = {
    "COMPOSE_PROJECT_NAME": "rag-smoke",
    "FRONTEND_HOST_PORT": "18080",
    "BACKEND_HOST_PORT": "18000",
    "POSTGRES_HOST_PORT": "15432",
}
"""Defaults, so a smoke run never clashes with a dev stack; the environment can override them."""

MIN_STREAM_SPREAD_S: Final = 0.2
"""The fake spaces its deltas 0.15 s apart, so its `token`s span about 0.45 s. One buffered flush
delivers them all at once. The client asks for gzip, as browsers do, so compressing the stream
(which buffers it) fails this too."""

QUESTION: Final = "How do I configure SAML single sign-on for a client?"
FOLLOW_UP: Final = "and on v2?"


class SmokeFailure(Exception):
    pass


@dataclass(frozen=True)
class Frame:
    """One Server-Sent Event, and when the chunk that completed it arrived."""

    event: str
    data: Any
    arrived_s: float


def parse_sse(chunks: Iterable[tuple[float, bytes]]) -> list[Frame]:
    """The events in a stream of `(arrival time, bytes)` chunks; comments (pings) are skipped."""
    frames: list[Frame] = []
    pending = ""
    for arrived_s, chunk in chunks:
        pending += chunk.decode().replace("\r\n", "\n")
        *complete, pending = pending.split("\n\n")
        for block in complete:
            event, data = "message", list[str]()
            for line in block.split("\n"):
                field, _, value = line.partition(":")
                value = value.removeprefix(" ")
                if field == "event":
                    event = value
                elif field == "data":
                    data.append(value)
            if data:
                frames.append(Frame(event, json.loads("\n".join(data)), arrived_s))
    return frames


def check_turn(
    frames: list[Frame],
    *,
    expect: Literal["answer", "refusal"],
    standalone_question: str | None = None,
) -> None:
    """Raise `SmokeFailure` unless `frames` are one well-formed Turn ending in `expect`."""
    events = [f.event for f in frames]
    if "error" in events:
        error = frames[events.index("error")].data["error"]
        raise SmokeFailure(f"the Turn failed: {error['code']}: {error['message']}")
    if standalone_question is not None:
        if events[:1] != ["rewritten"]:
            raise SmokeFailure(f"a Follow-up must open with `rewritten`, got {events}")
        if (got := frames[0].data["standalone_question"]) != standalone_question:
            raise SmokeFailure(f"rewritten to {got!r}, expected {standalone_question!r}")
        frames, events = frames[1:], events[1:]
    if events[:1] != ["passages"] or events[-1:] != ["done"]:
        raise SmokeFailure(f"expected `passages` first and `done` last, got {events}")
    tokens = [f for f in frames if f.event == "token"]
    result = frames[-1].data["result"]

    if expect == "refusal":
        if tokens:
            raise SmokeFailure("a Refusal must stream no `token`: the sentinel is held back")
        if (result["type"], result.get("reason")) != ("refusal", "not_in_context"):
            raise SmokeFailure(f"expected a not_in_context Refusal, got {result}")
        return

    if len(tokens) < 2:
        raise SmokeFailure(f"expected several `token`s, got {len(tokens)}")
    if (spread := tokens[-1].arrived_s - tokens[0].arrived_s) < MIN_STREAM_SPREAD_S:
        raise SmokeFailure(
            f"the `token`s arrived within {spread:.3f} s of each other: something between the "
            "backend and the client is buffering the stream (nginx's proxy_buffering or gzip?)"
        )
    if result["type"] != "answer":
        raise SmokeFailure(f"expected an Answer, got {result}")
    top_passage = frames[0].data["passages"][0]["id"]
    cited = [(c["n"], c["passage"]["id"]) for c in result["citations"]]
    if cited != [(1, top_passage)]:
        raise SmokeFailure(f"expected the Answer to cite [1] {top_passage}, got {cited}")


def stream_turn(client: httpx.Client, body: Mapping[str, Any]) -> list[Frame]:
    with client.stream("POST", "/api/chat", json=body) as response:
        if response.status_code != 200:
            response.read()
            raise SmokeFailure(f"POST /api/chat: {response.status_code} {response.text}")
        return parse_sse((time.monotonic(), chunk) for chunk in response.iter_bytes())


def wait_until_ready(client: httpx.Client, timeout_s: float = 60) -> None:
    """`up --wait` has waited for the backend's /ready already; this checks it through nginx."""
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            response = client.get("/api/ready")
            if response.status_code == 200:
                return
            problem = f"{response.status_code} {response.text}"
        except httpx.TransportError as error:
            problem = repr(error)
        if time.monotonic() > deadline:
            raise SmokeFailure(f"GET /api/ready never returned 200: {problem}")
        time.sleep(1)


def run_checks(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        wait_until_ready(client)
        _passed("GET /api/ready is 200")

        listed = sorted(a["id"] for a in client.get("/api/articles").raise_for_status().json())
        on_disk = sorted(a.id for a in load_articles(KNOWLEDGE_BASE_DIR))
        if listed != on_disk:
            raise SmokeFailure(f"GET /api/articles listed {listed}, knowledge-base/ has {on_disk}")
        _passed(f"GET /api/articles lists all {len(on_disk)} Articles")

        check_turn(stream_turn(client, {"question": QUESTION}), expect="answer")
        _passed("a question streams `passages`, then `token`s one by one, then a cited Answer")

        history = [{"question": QUESTION, "answer": "Like this [1]."}]
        check_turn(
            stream_turn(client, {"question": FOLLOW_UP, "history": history}),
            expect="answer",
            standalone_question=FOLLOW_UP,
        )
        _passed("a Follow-up is rewritten, then answered")

        refused = stream_turn(client, {"question": f"{QUESTION} {FAKE_REFUSAL_TRIGGER}"})
        check_turn(refused, expect="refusal")
        _passed("the Refusal sentinel ends in a Refusal, with nothing streamed")


def _passed(check: str) -> None:
    print(f"smoke: ok: {check}", flush=True)


def main() -> int:
    env = {**SMOKE_ENV, **os.environ, "BACKEND_LLM_PROVIDER": "fake", "COMPOSE_PROFILES": ""}

    def run(*command: str) -> int:
        print(f"smoke: $ {' '.join(command)}", flush=True)
        return subprocess.run(command, cwd=REPO_ROOT, env=env, check=False).returncode

    def down() -> None:
        run("docker", "compose", "down", "--volumes", "--remove-orphans")

    down()  # a fresh volume, so startup runs a first ingestion
    try:
        if run("pixi", "run", "up") != 0:
            raise SmokeFailure("`pixi run up` failed")
        run_checks(f"http://localhost:{env['FRONTEND_HOST_PORT']}")
    except SmokeFailure as failure:
        run("docker", "compose", "logs", "--no-color", "--timestamps")
        print(f"smoke: FAILED: {failure}", file=sys.stderr, flush=True)
        return 1
    finally:
        down()
    print("smoke: all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
