from dataclasses import replace

from app.answer_assembly import (
    Answer,
    Citation,
    Refusal,
    UncitedAnswer,
    assemble_reply,
    gate_retrieval,
)
from app.passages import ArticleRef, Passage, SectionRef


def passage(n: int) -> Passage:
    """The Passage shown to the model as `[n]`."""
    return Passage(
        id=f"passage-{n}",
        article=ArticleRef(id=f"article-{n}", title=f"Article {n}"),
        section=SectionRef(id=f"section-{n}", path=(f"Article {n}", "Troubleshooting")),
        text=f"Verbatim text of Passage {n}.",
        applies_to=("v3",),
        status="current",
        score=0.9 - n / 100,
    )


def passages(count: int) -> tuple[Passage, ...]:
    return tuple(passage(n) for n in range(1, count + 1))


def test_only_the_marked_passages_become_citations() -> None:
    retrieved = passages(3)

    reply = assemble_reply("Reset the SAML certificate [1].", retrieved)

    assert reply == Answer(
        text="Reset the SAML certificate [1].",
        citations=(Citation(n=1, passage=passage(1)),),
        retrieved_passages=retrieved,
    )


def test_cited_passages_are_renumbered_in_order_of_first_appearance() -> None:
    retrieved = passages(8)

    reply = assemble_reply("Open Settings [3]. Click Rotate [7]. Save it [3].", retrieved)

    assert reply == Answer(
        text="Open Settings [1]. Click Rotate [2]. Save it [1].",
        citations=(
            Citation(n=1, passage=passage(3)),
            Citation(n=2, passage=passage(7)),
        ),
        retrieved_passages=retrieved,
    )


def test_markers_pointing_at_passages_that_dont_exist_are_removed() -> None:
    retrieved = passages(3)

    reply = assemble_reply("Open Settings [4]. Click Rotate [2]. Save it [0].", retrieved)

    assert reply == Answer(
        text="Open Settings. Click Rotate [1]. Save it.",
        citations=(Citation(n=1, passage=passage(2)),),
        retrieved_passages=retrieved,
    )


def test_adjacent_markers_each_become_a_citation() -> None:
    retrieved = passages(6)

    reply = assemble_reply("SSO needs Enterprise [2][5].", retrieved)

    assert reply == Answer(
        text="SSO needs Enterprise [1][2].",
        citations=(
            Citation(n=1, passage=passage(2)),
            Citation(n=2, passage=passage(5)),
        ),
        retrieved_passages=retrieved,
    )


def test_a_comma_list_is_normalised_to_adjacent_markers() -> None:
    retrieved = passages(6)

    reply = assemble_reply("SSO needs Enterprise [5, 2]. Ask your admin [2,6].", retrieved)

    assert reply == Answer(
        text="SSO needs Enterprise [1][2]. Ask your admin [2][3].",
        citations=(
            Citation(n=1, passage=passage(5)),
            Citation(n=2, passage=passage(2)),
            Citation(n=3, passage=passage(6)),
        ),
        retrieved_passages=retrieved,
    )


def test_a_cluster_of_markers_drops_its_invalid_and_repeated_numbers() -> None:
    retrieved = passages(3)

    reply = assemble_reply("SSO needs Enterprise [9][2][2, 7, 2].", retrieved)

    assert reply == Answer(
        text="SSO needs Enterprise [1].",
        citations=(Citation(n=1, passage=passage(2)),),
        retrieved_passages=retrieved,
    )


def test_an_answer_without_markers_is_an_uncited_answer() -> None:
    retrieved = passages(3)

    reply = assemble_reply("SSO needs the Enterprise Plan Tier.", retrieved)

    assert reply == UncitedAnswer(
        text="SSO needs the Enterprise Plan Tier.", retrieved_passages=retrieved
    )


def test_an_answer_whose_markers_are_all_invalid_is_an_uncited_answer() -> None:
    retrieved = passages(3)

    reply = assemble_reply("SSO needs the Enterprise Plan Tier [4][7].", retrieved)

    assert reply == UncitedAnswer(
        text="SSO needs the Enterprise Plan Tier.", retrieved_passages=retrieved
    )


def test_other_bracket_styles_are_not_markers_and_stay_as_written() -> None:
    retrieved = passages(3)
    model_text = "See [doc2], steps [1-3] and note [^1]."

    reply = assemble_reply(model_text, retrieved)

    assert reply == UncitedAnswer(text=model_text, retrieved_passages=retrieved)


def test_the_sentinel_alone_is_a_refusal_with_the_fixed_message() -> None:
    retrieved = passages(3)

    reply = assemble_reply("NOT_IN_KNOWLEDGE_BASE", retrieved)

    assert reply == Refusal(reason="not_in_context", retrieved_passages=retrieved)
    assert isinstance(reply, Refusal)
    assert reply.message == "The Knowledge Base doesn't cover this question."


def test_a_reply_starting_with_the_sentinel_is_a_refusal_whatever_follows() -> None:
    retrieved = passages(3)

    reply = assemble_reply(
        "\n  NOT_IN_KNOWLEDGE_BASE. Though SSO may need Enterprise [2].", retrieved
    )

    assert reply == Refusal(reason="not_in_context", retrieved_passages=retrieved)


def test_the_sentinel_after_real_text_is_stripped_and_the_reply_is_an_answer() -> None:
    retrieved = passages(3)

    reply = assemble_reply(
        "SSO needs Enterprise [2]. NOT_IN_KNOWLEDGE_BASE Pricing is not covered.\n\n"
        "NOT_IN_KNOWLEDGE_BASE",
        retrieved,
    )

    assert reply == Answer(
        text="SSO needs Enterprise [1]. Pricing is not covered.",
        citations=(Citation(n=1, passage=passage(2)),),
        retrieved_passages=retrieved,
    )


def scored(*scores: float) -> tuple[Passage, ...]:
    return tuple(replace(passage(n), score=score) for n, score in enumerate(scores, start=1))


def test_the_gate_refuses_when_no_passage_reaches_the_minimum_score() -> None:
    retrieved = scored(0.59, 0.41)

    refusal = gate_retrieval(retrieved, min_score=0.6)

    assert refusal == Refusal(reason="no_relevant_passages", retrieved_passages=retrieved)


def test_the_gate_refuses_when_nothing_was_retrieved() -> None:
    assert gate_retrieval((), min_score=0.6) == Refusal(
        reason="no_relevant_passages", retrieved_passages=()
    )


def test_the_gate_passes_when_any_passage_reaches_the_minimum_score() -> None:
    assert gate_retrieval(scored(0.41, 0.6), min_score=0.6) is None
