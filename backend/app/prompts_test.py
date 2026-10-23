import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.answer_assembly import NOT_IN_KNOWLEDGE_BASE
from app.chat_model import Message
from app.passages import ArticleRef, Passage, SectionRef
from app.prompts import (
    GAP_PHRASE,
    PROMPT_VERSION,
    UnusableRewrite,
    generation_messages,
    parse_rewrite,
    rewrite_messages,
)


def sso_passage() -> Passage:
    return Passage(
        id="nimbus-sso-saml#7",
        article=ArticleRef(id="nimbus-sso-saml", title="Nimbus SSO & SAML"),
        section=SectionRef(
            id="troubleshooting-error-auth-403",
            path=("Nimbus SSO & SAML", "Troubleshooting", "Error AUTH-403"),
        ),
        text="AUTH-403 means the user's email isn't in the assertion.",
        applies_to=("v3",),
        status="current",
        score=0.83,
    )


def v2_passage() -> Passage:
    return Passage(
        id="nimbus-v2-legacy#4",
        article=ArticleRef(id="nimbus-v2-legacy", title="Nimbus v2 Legacy Platform"),
        section=SectionRef(
            id="saml-attributes-v2",
            path=("Nimbus v2 Legacy Platform", "SAML attributes (v2)"),
        ),
        text="On v2 the email attribute is named `mail`.",
        applies_to=("v2",),
        status="deprecated",
        score=0.61,
    )


def user_text(messages: list[Message]) -> str:
    [system, user] = messages
    assert (system.role, user.role) == ("system", "user")
    return user.text


def test_passages_are_numbered_in_rank_order_with_their_section_path_and_metadata() -> None:
    messages = generation_messages("Why AUTH-403?", [sso_passage(), v2_passage()])

    assert user_text(messages).startswith(
        "<passages>\n"
        "[1] Nimbus SSO & SAML › Troubleshooting › Error AUTH-403\n"
        "Applies to: v3 · Status: current\n"
        "AUTH-403 means the user's email isn't in the assertion.\n"
        "\n"
        "[2] Nimbus v2 Legacy Platform › SAML attributes (v2)\n"
        "Applies to: v2 · Status: deprecated\n"
        "On v2 the email attribute is named `mail`.\n"
        "</passages>\n"
    )


def test_the_question_then_a_citation_reminder_follow_the_passages() -> None:
    messages = generation_messages("Why do users get AUTH-403?", [sso_passage()])

    assert user_text(messages).endswith(
        "</passages>\n"
        "\n"
        "Question: Why do users get AUTH-403?\n"
        "\n"
        "Answer from the Passages only, and end each sentence that uses one with its marker, "
        "like [1]."
    )


def test_the_system_message_holds_the_shared_sentinel_and_gap_phrase() -> None:
    [system, _] = generation_messages("Why AUTH-403?", [sso_passage()])

    assert f"reply with exactly {NOT_IN_KNOWLEDGE_BASE} and nothing else" in system.text
    assert f'starts with "{GAP_PHRASE}"' in system.text
    assert f"{GAP_PHRASE} sending exports to Slack." in system.text  # the worked example


def test_neither_the_score_nor_the_article_id_reaches_the_model() -> None:
    text = user_text(generation_messages("Why AUTH-403?", [sso_passage()]))

    assert "0.83" not in text
    assert "nimbus-sso-saml" not in text


@dataclass(frozen=True)
class PastTurn:
    question: str
    answer: str


def test_the_rewrite_sees_the_last_three_turns_then_the_follow_up() -> None:
    history = [PastTurn(f"Question {n}?", f"Answer {n}.") for n in range(1, 6)]

    [system, user] = rewrite_messages(history, "and on v2?")

    assert system.role == "system"
    assert user == Message(
        "user",
        "CSM: Question 3?\n"
        "Assistant: Answer 3.\n"
        "\n"
        "CSM: Question 4?\n"
        "Assistant: Answer 4.\n"
        "\n"
        "CSM: Question 5?\n"
        "Assistant: Answer 5.\n"
        "\n"
        "Follow-up: and on v2?",
    )


def test_the_rewrite_sees_answers_without_their_citation_markers() -> None:
    history = [PastTurn("How?", "Open Settings [1]. Click Rotate [2][3], then Save [1, 4].")]

    [_, user] = rewrite_messages(history, "and on v2?")

    assert "Assistant: Open Settings. Click Rotate, then Save.\n" in user.text


def test_the_rewrite_sees_long_answers_cut_to_500_characters() -> None:
    history = [PastTurn("How?", "a" * 499 + " [1]" + "b" * 600)]

    [_, user] = rewrite_messages(history, "and on v2?")

    assert f"Assistant: {'a' * 499 + 'b'}…\n" in user.text


@pytest.mark.parametrize(
    "reply",
    [
        "How is SCIM set up on v2?",
        "\n  How is SCIM set up on v2?  \nIt names the version the CSM meant.",
        '"How is SCIM set up on v2?"',
        "“How is SCIM set up on v2?”",
        "Standalone question: How is SCIM set up on v2?",
        'standalone question: "How is SCIM set up on v2?"',
    ],
)
def test_the_rewrite_reply_is_its_first_line_without_quotes_or_label(reply: str) -> None:
    assert parse_rewrite(reply, max_len=100) == "How is SCIM set up on v2?"


@pytest.mark.parametrize("reply", ["", "  \n\n ", '""', "Standalone question:"])
def test_an_empty_rewrite_is_unusable(reply: str) -> None:
    with pytest.raises(UnusableRewrite) as failure:
        parse_rewrite(reply, max_len=100)

    assert failure.value.reason == "empty"


def test_a_rewrite_longer_than_the_question_cap_is_unusable() -> None:
    assert parse_rewrite("x" * 100, max_len=100) == "x" * 100

    with pytest.raises(UnusableRewrite) as failure:
        parse_rewrite("x" * 101, max_len=100)

    assert failure.value.reason == "too_long"


# --- snapshots: any wording change shows up as a diff of these files ---

SNAPSHOTS = Path(__file__).parent / "prompts_snapshots"


def assert_matches_snapshot(name: str, messages: list[Message]) -> None:
    """Compare the fully rendered prompt with `prompts_snapshots/<name>.txt`.

    After a deliberate wording change (and a `PROMPT_VERSION` bump), rewrite the files with
    `UPDATE_SNAPSHOTS=1 pixi run test-backend` and review their diff.
    """
    rendered = f"PROMPT_VERSION: {PROMPT_VERSION}\nGAP_PHRASE: {GAP_PHRASE}\n" + "".join(
        f"\n===== {message.role} =====\n{message.text}\n" for message in messages
    )
    snapshot = SNAPSHOTS / f"{name}.txt"
    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshot.write_text(rendered, encoding="utf-8")
    assert snapshot.exists(), f"No snapshot {snapshot}; write it with UPDATE_SNAPSHOTS=1."
    assert rendered == snapshot.read_text(encoding="utf-8")


def test_the_generation_prompt_matches_its_snapshot() -> None:
    messages = generation_messages(
        "Why do users get AUTH-403 after signing in with Okta?", [sso_passage(), v2_passage()]
    )

    assert_matches_snapshot("generation", messages)


def test_the_rewrite_prompt_matches_its_snapshot() -> None:
    history = [
        PastTurn("What does Starter include?", "Starter includes up to 10 users [1]."),
        PastTurn(
            "Which Plan Tiers include SCIM provisioning?",
            "SCIM provisioning is included on the Enterprise tier only [1]. "
            "SAML SSO must be configured first [2][3].",
        ),
        PastTurn("How do I set up SCIM with Okta?", "Steps: " + "Open Okta and click on. " * 30),
        PastTurn("Does it support LDAP?", "The Knowledge Base doesn't cover this question."),
    ]

    assert_matches_snapshot("rewrite", rewrite_messages(history, "and on Entra ID?"))
