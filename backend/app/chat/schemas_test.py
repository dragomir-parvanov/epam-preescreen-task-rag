from app import answer_assembly, passages
from app.chat.schemas import chat_result

PASSAGE = passages.Passage(
    id="sso-setup#0",
    article=passages.ArticleRef(id="sso-setup", title="Setting up SSO"),
    section=passages.SectionRef(id="error-auth-403", path=("Setting up SSO", "Error AUTH-403")),
    text="AUTH-403 means the IdP certificate has expired.",
    applies_to=("v2", "v3"),
    status="deprecated",
    score=0.82,
)

PASSAGE_JSON = {
    "id": "sso-setup#0",
    "article": {"id": "sso-setup", "title": "Setting up SSO"},
    "section": {"id": "error-auth-403", "path": ["Setting up SSO", "Error AUTH-403"]},
    "text": "AUTH-403 means the IdP certificate has expired.",
    "applies_to": ["v2", "v3"],
    "status": "deprecated",
    "score": 0.82,
}


def test_an_answer_maps_with_its_citations_and_the_standalone_question() -> None:
    reply = answer_assembly.Answer(
        text="It has expired [1].",
        citations=(answer_assembly.Citation(n=1, passage=PASSAGE),),
        retrieved_passages=(PASSAGE,),
    )

    result = chat_result(reply, standalone_question="How do I fix AUTH-403 on v3?")

    assert result.model_dump(mode="json") == {
        "type": "answer",
        "text": "It has expired [1].",
        "citations": [{"n": 1, "passage": PASSAGE_JSON}],
        "retrieved_passages": [PASSAGE_JSON],
        "standalone_question": "How do I fix AUTH-403 on v3?",
    }


def test_an_uncited_answer_maps_without_citations() -> None:
    reply = answer_assembly.UncitedAnswer(text="Probably expired.", retrieved_passages=(PASSAGE,))

    result = chat_result(reply, standalone_question=None)

    assert result.model_dump(mode="json") == {
        "type": "uncited_answer",
        "text": "Probably expired.",
        "retrieved_passages": [PASSAGE_JSON],
        "standalone_question": None,
    }


def test_a_refusal_maps_with_the_fixed_message_and_its_reason() -> None:
    reply = answer_assembly.Refusal(reason="not_in_context", retrieved_passages=(PASSAGE,))

    result = chat_result(reply, standalone_question=None)

    assert result.model_dump(mode="json") == {
        "type": "refusal",
        "message": "The Knowledge Base doesn't cover this question.",
        "reason": "not_in_context",
        "retrieved_passages": [PASSAGE_JSON],
        "standalone_question": None,
    }
