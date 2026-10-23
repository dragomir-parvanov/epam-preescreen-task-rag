# OmniCorp Knowledge Base Assistant

A chat assistant that lets OmniCorp Customer Success Managers ask questions about the OmniCorp Nimbus product and get answers drawn only from internal Articles.

## Language

### Knowledge Base

**Knowledge Base**:
The complete set of internal Articles the assistant is allowed to answer from.
_Avoid_: Corpus (outside technical discussion), document store

**Article**:
One authored source text in the Knowledge Base; the unit a CSM opens to verify an answer.
_Avoid_: Document, manual, page, file

**Section**:
A heading-delimited part of an Article, identified by its heading path (e.g. `Troubleshooting > Error AUTH-403`).
_Avoid_: Paragraph, part

**Passage**:
A verbatim excerpt of one Section; the unit the assistant retrieves and cites.
_Avoid_: Chunk (outside technical discussion), snippet

### Answers

**Answer**:
The assistant's grounded reply to a CSM's question, carrying the Citations it drew on.
_Avoid_: Response, completion

**Citation**:
A numbered reference in an Answer to a Passage the Answer drew on.
_Avoid_: Source (ambiguous between Article, Section and Passage), reference, footnote

**Uncited Answer**:
An Answer that contains no valid Citations, shown with a warning rather than presented as grounded.
_Avoid_: Ungrounded answer, hallucination

**Refusal**:
A reply stating that the Knowledge Base does not cover the question; it carries no Citations.
_Avoid_: No answer, fallback

### OmniCorp Nimbus (the fictional product)

**OmniCorp Nimbus**:
The fictional B2B workflow and integration platform the Knowledge Base documents.

**Platform Version**:
A major release of OmniCorp Nimbus: v2 (legacy) or v3 (current). An Article states which Platform Versions it applies to.
_Avoid_: Release, edition

**Plan Tier**:
The commercial plan a client is on (Starter, Business or Enterprise), which determines the features and limits available to them.
_Avoid_: Plan, edition, SKU, license

### People

**CSM (Customer Success Manager)**:
The OmniCorp employee who asks the assistant questions on behalf of a client.
_Avoid_: User (ambiguous with the client's own users), agent

### Conversation

**Conversation**:
The ordered Turns one CSM has with the assistant in a single browser session; it is not saved.
_Avoid_: Session, thread, chat history

**Turn**:
One question from the CSM together with the assistant's Answer or Refusal to it.
_Avoid_: Exchange, message pair

**Follow-up Question**:
A question that only makes sense in light of earlier Turns in the same Conversation (e.g. "and on v2?").

**Standalone Question**:
The self-contained rewrite of a Follow-up Question; it is what the Knowledge Base is actually searched with.
_Avoid_: Condensed query, rephrased query

### Evaluation

**Golden Question**:
A question, optionally with earlier Turns, paired with what the assistant should do with it: answer or refuse, which Sections to cite, and which terms the Answer must mention. The assistant's quality is measured against the whole set. A Golden Question is either **curated** (hand-designed to probe a planted hard case) or **generated** (written alongside a generated Article).
_Avoid_: Test case, benchmark question, eval sample
