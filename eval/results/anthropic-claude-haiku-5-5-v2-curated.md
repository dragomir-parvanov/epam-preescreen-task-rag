# LLM eval: anthropic claude-haiku-5-5, prompt v2

| Run |  |
| --- | --- |
| Date | 2026-10-23T14:04:45+00:00 |
| Git SHA | 927a9b6 |
| Provider | anthropic |
| Model | claude-haiku-5-5 (effort low) |
| Prompt version | v2 |
| Retrieval | hybrid, top_k 8, min_score 0.66 |
| Questions | curated (27 questions) |
| Concurrency | 1 Turn(s) at a time |

## Headline

Over 25 questions: the 2 known retrieval misses are reported apart below.

| Metric | Value |
| --- | --- |
| Outcome accuracy | 72.0% (18/25) |
| Refusal correctness | 6/13 unanswerable refused (7 got a gap Answer instead); 0 answerable refused |
| Citation precision | 73.6% |
| Citation recall | 100% |
| Retrieval recall | 100% |
| Uncited rate | 0% |
| must_mention hit rate | 100% |
| Standalone must_mention | 100% |
| Errors | 0 |
| Latency p50 / p95 | 1.9 s / 4.5 s |
| TTFT p50 | 1.6 s |
| Tokens | 80,049 input + 7,355 output tokens |
| Cost | $0.0117 ($0.0005 a question) |

Whole run, known misses included: 87,402 input + 9,358 output tokens, $0.0134.

## By category

| Category | n | Outcome | Cit. P | Cit. R | Retr. R | must_mention | p50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cross-article | 1 | 100% | 66.7% | 100% | 100% | 100% | 2.2 s |
| follow-up | 3 | 66.7% | 75.0% | 100% | 100% | 100% | 3.4 s |
| near-duplicate | 2 | 100% | 75.0% | 100% | 100% | 100% | 1.9 s |
| partial | 1 | 100% | 100% | 100% | 100% | 100% | 1.2 s |
| table-lookup | 3 | 100% | 83.3% | 100% | 100% | 100% | 1.3 s |
| unanswerable | 12 | 50.0% | - | - | - | - | 1.2 s |
| version-conflict | 3 | 100% | 55.6% | 100% | 100% | 100% | 1.7 s |

## Wrong outcomes

| Question | Expected | Got | Blame | Retr. R | Answer |
| --- | --- | --- | --- | --- | --- |
| gq-enterprise-price | refusal | partial | model | - | The Enterprise Plan Tier has unlimited seats, and it is never reached [1][2]. I couldn't find anything in the Knowledge Base about Enterprise pricing or the co… |
| gq-followup-topic-change-ldap | refusal | partial | model | - | Nimbus supports single sign-on through SAML 2.0, acting as a SAML 2.0 service provider [1]. Users can sign in from the Nimbus login page or from the identity p… |
| gq-scim-onelogin | refusal | partial | model | - | SCIM provisioning is documented only for Okta and Microsoft Entra ID [1]. If the client uses one of those, the setup steps are in the Knowledge Base [2]. Befor… |
| gq-sso-ping-identity | refusal | partial | model | - | Nimbus acts as a SAML 2.0 service provider and supports sign-in from the Nimbus login page as well as from the IdP's app dashboard [1]. Before starting, confir… |
| gq-active-directory-sync | refusal | partial | model | - | Nimbus implements the SCIM 2.0 protocol for users and groups. The identity provider (IdP) sends Nimbus every change to users and groups assigned to the Nimbus … |
| gq-google-workspace-provisioning | refusal | partial | model | - | The Knowledge Base describes automated provisioning with SCIM 2.0 for Okta and Microsoft Entra ID, where only users and groups assigned to the Nimbus app are p… |
| gq-saml-single-logout | refusal | partial | model | - | I couldn't find anything in the Knowledge Base about SAML single logout. The Passages do describe how SSO enforcement affects existing sessions: once **Require… |

## Missed must_mention terms

None.

## Known retrieval misses

Their answering Sections are never retrieved, so expect a Refusal or a gap Answer.

| Question | Expected | Got | Retr. R | Why retrieval misses |
| --- | --- | --- | --- | --- |
| gq-entra-auto-deprovision | answer | partial | 0% | "Leavers removed automatically" shares no words with SCIM or deprovisioning, and "what happens to their data" pulls in data-deletion and GDPR Sections, so neither SCIM Section is in the hybrid top 20. Needs query expansion (#28). |
| gq-google-sso | partial | partial | 0% | "Set up SSO with Google Workspace" pulls in workspace-creation, two-factor and FAQ setup Sections; Attribute mapping ranks 20th. Needs query expansion (#28). |

## Every question

| Question | Category | Expected | Got | Right | Cit. P | Cit. R | Retr. R | Terms | Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gq-scim-business-tier | cross-article | answer | answer | yes | 66.7% | 100% | 100% | 2/2 | 2.2 s |
| gq-entra-auto-deprovision | cross-article (known miss) | answer | partial | **no** | 0% | 0% | 0% | 2/4 | 4.1 s |
| gq-webhook-signature | version-conflict | answer | answer | yes | 66.7% | 100% | 100% | 3/3 | 1.7 s |
| gq-rate-limit-business | version-conflict | answer | answer | yes | 66.7% | 100% | 100% | 2/2 | 1.2 s |
| gq-v2-saml-email | version-conflict | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 3.6 s |
| gq-auth-401 | table-lookup | answer | answer | yes | 100% | 100% | 100% | 2/2 | 1.1 s |
| gq-audit-retention-business | table-lookup | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 1.3 s |
| gq-enterprise-burst | table-lookup | answer | answer | yes | 100% | 100% | 100% | 2/2 | 1.3 s |
| gq-jit-vs-scim | near-duplicate | answer | answer | yes | 50.0% | 100% | 100% | 3/3 | 1.9 s |
| gq-deprovisioned-data | near-duplicate | answer | answer | yes | 100% | 100% | 100% | 2/2 | 1.9 s |
| gq-enterprise-price | unanswerable | refusal | partial | **no** | - | - | - |  | 2.5 s |
| gq-ldap | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 0.8 s |
| gq-google-sso | partial (known miss) | partial | partial | yes | 0% | 0% | 0% | 1/3 | 5.9 s |
| gq-webhook-retries-ips | partial | partial | partial | yes | 100% | 100% | 100% | 2/2 | 1.2 s |
| gq-followup-webhook-signature-v2 | follow-up | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 4.5 s |
| gq-followup-rate-limit-enterprise | follow-up | answer | answer | yes | 100% | 100% | 100% | 1/1 | 2.5 s |
| gq-followup-topic-change-ldap | follow-up | refusal | partial | **no** | - | - | - |  | 3.4 s |
| gq-scim-onelogin | unanswerable | refusal | partial | **no** | - | - | - |  | 3.9 s |
| gq-sso-ping-identity | unanswerable | refusal | partial | **no** | - | - | - |  | 5.4 s |
| gq-webhook-source-ips | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 0.8 s |
| gq-business-annual-discount | unanswerable | refusal | refusal (no_relevant_passages) | yes | - | - | - |  | 0.0 s |
| gq-upgrade-cost | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.2 s |
| gq-active-directory-sync | unanswerable | refusal | partial | **no** | - | - | - |  | 3.6 s |
| gq-google-workspace-provisioning | unanswerable | refusal | partial | **no** | - | - | - |  | 3.3 s |
| gq-v1-end-of-support | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 1.0 s |
| gq-saml-single-logout | unanswerable | refusal | partial | **no** | - | - | - |  | 1.2 s |
| gq-enterprise-uptime-sla | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 0.8 s |

## How it is scored

- **Outcome**: an unanswerable question expects a Refusal, a `partial` one an Answer stating the gap phrase (`GAP_PHRASE`, anywhere, any case, either apostrophe), any other an Answer without it. An Uncited Answer counts as an Answer. A failed Turn (`rewrite_failed`, `llm_unavailable`, ...) is an `error`. A gap Answer to an unanswerable question is a soft refusal: it says what it couldn't find, but answers neighbouring facts instead of refusing.
- **Blame** for a wrong outcome: `retrieval` when it is a Refusal or a gap and an expected Section wasn't retrieved, so the model never saw it; `model` otherwise; `error` for a failed Turn.
- **Citation precision and recall** are at Section level, over distinct Sections; citing any alternative of an expected source counts for it. Precision averages over the Answers that cite something; recall over the answerable questions, where a Refusal or an Uncited Answer scores 0. Precision is against the Golden Question's expected Sections only, so a correctly cited extra fact (a v2 caveat, a related error code) lowers it: read it as focus, not as wrong Citations.
- **Retrieval recall**: the share of expected sources with any option among the retrieved Passages.
- **must_mention**: whole-word, case-insensitive term groups (any term in a group counts), over every group of the answerable questions. **Standalone** checks a Follow-up's `standalone_must_mention` against its rewrite.
- **Latency** is the whole Turn, rewrite included; **TTFT** is to the first streamed token.
- **Cost** is at list price from the providers' reported token usage. A model Refusal (`not_in_context`) stops its stream at the sentinel, before the provider reports usage, so its generation call isn't charged: each one is under-counted by its prompt (about 3K input tokens).
