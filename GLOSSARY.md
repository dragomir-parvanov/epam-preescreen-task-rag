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
