import json
from typing import Any

import pytest

from smoke.compose_smoke import Frame, SmokeFailure, check_turn, parse_sse

PASSAGE = {"id": "nimbus-sso-saml#prerequisites", "score": 0.71}
OTHER = {"id": "nimbus-plan-tiers#enterprise", "score": 0.62}


def sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def frame(event: str, arrived_s: float, **data: Any) -> Frame:
    return Frame(event=event, data={"type": event, **data}, arrived_s=arrived_s)


def answer(*, citing: dict[str, Any] = PASSAGE) -> dict[str, Any]:
    return {"type": "answer", "citations": [{"n": 1, "passage": citing}]}


REFUSAL = {"type": "refusal", "reason": "not_in_context"}


def test_frames_are_parsed_with_the_arrival_of_the_chunk_that_completed_them() -> None:
    passages, token = sse("passages", {"passages": [PASSAGE]}), sse("token", {"text": "Hi"})
    chunks = [(1.0, passages + token[:10]), (1.5, token[10:]), (2.0, b": ping\r\n\r\n")]

    frames = parse_sse(chunks)

    assert frames == [
        Frame("passages", {"passages": [PASSAGE]}, arrived_s=1.0),
        Frame("token", {"text": "Hi"}, arrived_s=1.5),
    ]


def test_an_incremental_answer_citing_the_top_passage_passes() -> None:
    check_turn(
        [
            frame("passages", 0.0, passages=[PASSAGE, OTHER]),
            frame("token", 0.0, text="A "),
            frame("token", 0.3, text="B [1]."),
            frame("done", 0.3, result=answer()),
        ],
        expect="answer",
    )


def test_a_stream_flushed_in_one_burst_fails_as_buffered() -> None:
    with pytest.raises(SmokeFailure, match="buffer"):
        check_turn(
            [
                frame("passages", 2.0, passages=[PASSAGE]),
                frame("token", 2.0, text="A "),
                frame("token", 2.0, text="B [1]."),
                frame("done", 2.0, result=answer()),
            ],
            expect="answer",
        )


def test_done_before_passages_fails() -> None:
    with pytest.raises(SmokeFailure, match="passages"):
        check_turn([frame("done", 0.0, result=REFUSAL)], expect="refusal")


def test_an_answer_citing_another_passage_than_the_top_one_fails() -> None:
    with pytest.raises(SmokeFailure, match="cite"):
        check_turn(
            [
                frame("passages", 0.0, passages=[PASSAGE, OTHER]),
                frame("token", 0.0, text="A "),
                frame("token", 0.3, text="B [1]."),
                frame("done", 0.3, result=answer(citing=OTHER)),
            ],
            expect="answer",
        )


def test_a_sentinel_refusal_streams_no_tokens() -> None:
    check_turn(
        [frame("passages", 0.0, passages=[PASSAGE]), frame("done", 0.1, result=REFUSAL)],
        expect="refusal",
    )

    with pytest.raises(SmokeFailure, match="token"):
        check_turn(
            [
                frame("passages", 0.0, passages=[PASSAGE]),
                frame("token", 0.0, text="NOT_IN_"),
                frame("done", 0.1, result=REFUSAL),
            ],
            expect="refusal",
        )


def test_an_error_event_fails_with_its_message() -> None:
    error = {"code": "llm_unavailable", "message": "The language model is unavailable."}

    with pytest.raises(SmokeFailure, match="llm_unavailable"):
        check_turn(
            [frame("passages", 0.0, passages=[PASSAGE]), frame("error", 0.1, error=error)],
            expect="answer",
        )


def test_a_follow_up_must_be_rewritten_first() -> None:
    frames = [
        frame("passages", 0.0, passages=[PASSAGE]),
        frame("done", 0.1, result=REFUSAL),
    ]

    with pytest.raises(SmokeFailure, match="rewritten"):
        check_turn(frames, expect="refusal", standalone_question="and on v2?")

    check_turn(
        [frame("rewritten", 0.0, standalone_question="and on v2?"), *frames],
        expect="refusal",
        standalone_question="and on v2?",
    )
