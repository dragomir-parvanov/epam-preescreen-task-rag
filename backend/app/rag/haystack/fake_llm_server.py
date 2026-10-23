"""An in-process HTTP server that speaks an LLM provider's streaming protocol, for adapter tests.

The `ChatModel` tests drive the real Haystack generators and provider SDKs against it, so the
fake sits at the HTTP boundary: what the SDK sends is recorded, and whether the SDK hangs up
mid-stream (Stop) is observable as the connection closing.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True, kw_only=True)
class Reply:
    """One scripted response. A chunked body, sent part by part as the client reads it.

    With `hold_open`, the server sends `parts` and then neither ends the body nor closes the
    connection, the way a provider does while the model is still generating.
    """

    status: int = 200
    content_type: str = "application/json"
    parts: Sequence[bytes] = ()
    hold_open: bool = False


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: Any


@dataclass
class FakeLlmServer:
    """Answers the n-th request with the n-th scripted `Reply`, the last one repeating."""

    replies: Sequence[Reply]
    url: str = ""
    requests: list[Request] = field(default_factory=list[Request])
    hung_up: asyncio.Event = field(default_factory=asyncio.Event)
    """Set when the client closes a connection that `hold_open` kept open."""

    async def serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            head = await reader.readuntil(b"\r\n\r\n")
        except asyncio.IncompleteReadError:
            writer.close()
            return
        request_line, *header_lines = head.decode("latin-1").split("\r\n")
        method, path, _ = request_line.split(" ", 2)
        headers = {
            name.strip().lower(): value.strip()
            for name, _, value in (line.partition(":") for line in header_lines if line)
        }
        raw = await reader.readexactly(int(headers.get("content-length", "0")))
        self.requests.append(Request(method, path, json.loads(raw) if raw else None))

        reply = self.replies[min(len(self.requests), len(self.replies)) - 1]
        writer.write(
            f"HTTP/1.1 {reply.status} Scripted\r\n"
            f"content-type: {reply.content_type}\r\n"
            "transfer-encoding: chunked\r\nconnection: close\r\n\r\n".encode("latin-1")
        )
        for part in reply.parts:
            writer.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
            await writer.drain()
        if reply.hold_open:
            await reader.read()  # returns b"" once the client closes its end
            self.hung_up.set()
        else:
            writer.write(b"0\r\n\r\n")
            await writer.drain()
        writer.close()


@asynccontextmanager
async def fake_llm_server(*replies: Reply) -> AsyncGenerator[FakeLlmServer]:
    server = FakeLlmServer(replies)
    listener = await asyncio.start_server(server.serve, "127.0.0.1", 0)
    host, port = listener.sockets[0].getsockname()[:2]
    server.url = f"http://{host}:{port}"
    try:
        yield server
    finally:
        # Drop connections a client never closed, so a broken Stop fails the test, not hangs it.
        listener.close()
        listener.close_clients()
        await listener.wait_closed()


# --- Anthropic Messages API -----------------------------------------------------------------


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def _anthropic_message(content: list[dict[str, Any]], stop_reason: str | None) -> Any:
    return {
        "id": "msg_fake",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def _anthropic_error_body(error_type: str) -> Any:
    return {"type": "error", "error": {"type": error_type, "message": "scripted failure"}}


def _anthropic_events(deltas: Sequence[str]) -> list[bytes]:
    """`message_start`, a text block's start, then one `content_block_delta` per delta."""
    message = _anthropic_message([], stop_reason=None)
    block = {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""},
    }
    return [
        _sse("message_start", {"type": "message_start", "message": message}),
        _sse("content_block_start", block),
        *(
            _sse(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": d},
                },
            )
            for d in deltas
        ),
    ]


_ANTHROPIC_STREAM_END: Final = [
    _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
    _sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": 5},
        },
    ),
    _sse("message_stop", {"type": "message_stop"}),
]


def anthropic_stream(*deltas: str, hold_open: bool = False) -> Reply:
    """A streamed reply of `deltas`; with `hold_open`, it stops after them and stalls."""
    parts = _anthropic_events(deltas)
    if not hold_open:
        parts += _ANTHROPIC_STREAM_END
    return Reply(content_type="text/event-stream", parts=parts, hold_open=hold_open)


def anthropic_stream_error(error_type: str, *deltas: str) -> Reply:
    """A stream that fails part-way with an SSE `error` event, as on mid-stream overload."""
    parts = [*_anthropic_events(deltas), _sse("error", _anthropic_error_body(error_type))]
    return Reply(content_type="text/event-stream", parts=parts)


def anthropic_message(text: str) -> Reply:
    """A non-streamed Messages API reply."""
    body = _anthropic_message([{"type": "text", "text": text}], "end_turn")
    return Reply(parts=[json.dumps(body).encode()])


def anthropic_error(status: int, error_type: str) -> Reply:
    return Reply(status=status, parts=[json.dumps(_anthropic_error_body(error_type)).encode()])


# --- Ollama /api/chat -----------------------------------------------------------------------


def _ollama_line(content: str, *, done: bool) -> bytes:
    line: dict[str, Any] = {
        "model": "qwen3.5:2b",
        "created_at": "2026-10-23T12:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": done,
    }
    if done:
        line |= {"done_reason": "stop", "prompt_eval_count": 10, "eval_count": 5}
    return json.dumps(line).encode() + b"\n"


def ollama_stream(*deltas: str, hold_open: bool = False) -> Reply:
    """A streamed NDJSON reply of `deltas`; with `hold_open`, it stops after them and stalls."""
    parts = [_ollama_line(d, done=False) for d in deltas]
    if not hold_open:
        parts.append(_ollama_line("", done=True))
    return Reply(content_type="application/x-ndjson", parts=parts, hold_open=hold_open)


def ollama_message(text: str) -> Reply:
    """A non-streamed /api/chat reply."""
    return Reply(parts=[_ollama_line(text, done=True)])


def ollama_error(status: int, message: str) -> Reply:
    return Reply(status=status, parts=[json.dumps({"error": message}).encode()])
