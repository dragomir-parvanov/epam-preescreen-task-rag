# LLM eval: anthropic claude-opus-5-5, prompt v2

| Run |  |
| --- | --- |
| Date | 2026-10-23T14:02:01+00:00 |
| Git SHA | 927a9b6 |
| Provider | anthropic |
| Model | claude-opus-5-5 (effort low) |
| Prompt version | v2 |
| Retrieval | hybrid, top_k 8, min_score 0.66 |
| Questions | curated (27 questions) |
| Concurrency | 1 Turn(s) at a time |

## Headline

Over 25 questions: the 2 known retrieval misses are reported apart below.

| Metric | Value |
| --- | --- |
| Outcome accuracy | 80.0% (20/25) |
| Refusal correctness | 8/13 unanswerable refused (5 got a gap Answer instead); 0 answerable refused |
| Citation precision | 45.4% |
| Citation recall | 100% |
| Retrieval recall | 100% |
| Uncited rate | 0% |
| must_mention hit rate | 100% |
| Standalone must_mention | 100% |
| Errors | 0 |
| Latency p50 / p95 | 4.2 s / 6.5 s |
| TTFT p50 | 2.0 s |
| Tokens | 72,424 input + 7,859 output tokens |
| Cost | $0.4469 ($0.0179 a question) |

Whole run, known misses included: 79,777 input + 9,404 output tokens, $0.5072.

## By category

| Category | n | Outcome | Cit. P | Cit. R | Retr. R | must_mention | p50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cross-article | 1 | 100% | 33.3% | 100% | 100% | 100% | 5.8 s |
| follow-up | 3 | 66.7% | 33.3% | 100% | 100% | 100% | 5.9 s |
| near-duplicate | 2 | 100% | 50.0% | 100% | 100% | 100% | 4.6 s |
| partial | 1 | 100% | 50.0% | 100% | 100% | 100% | 4.2 s |
| table-lookup | 3 | 100% | 52.8% | 100% | 100% | 100% | 3.2 s |
| unanswerable | 12 | 66.7% | - | - | - | - | 2.8 s |
| version-conflict | 3 | 100% | 45.6% | 100% | 100% | 100% | 4.0 s |

## Wrong outcomes

| Question | Expected | Got | Blame | Retr. R | Answer |
| --- | --- | --- | --- | --- | --- |
| gq-followup-topic-change-ldap | refusal | partial | model | - | Nimbus single sign-on works with SAML 2.0, with Nimbus acting as the service provider [1]. It supports sign-in from both the Nimbus login page (SP-initiated) a… |
| gq-scim-onelogin | refusal | partial | model | - | I couldn't find anything in the Knowledge Base about setting up SCIM provisioning with OneLogin. The SCIM setup guide documents the connection for only two ide… |
| gq-sso-ping-identity | refusal | partial | model | - | Nimbus acts as a standard SAML 2.0 service provider and supports both SP-initiated sign-in from the Nimbus login page and IdP-initiated sign-in from the IdP's … |
| gq-active-directory-sync | refusal | partial | model | - | Nimbus syncs users and groups from an identity provider (IdP) through **SCIM 2.0** [1]. The IdP sends Nimbus every change to the users and groups assigned to t… |
| gq-google-workspace-provisioning | refusal | partial | model | - | Automatic user provisioning with deprovisioning uses SCIM provisioning on the **Enterprise** tier [1]. The documented SCIM setup covers **Okta** and **Microsof… |

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
| gq-scim-business-tier | cross-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.8 s |
| gq-entra-auto-deprovision | cross-article (known miss) | answer | partial | **no** | 0% | 0% | 0% | 2/4 | 8.4 s |
| gq-webhook-signature | version-conflict | answer | answer | yes | 66.7% | 100% | 100% | 3/3 | 4.0 s |
| gq-rate-limit-business | version-conflict | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-v2-saml-email | version-conflict | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 3.2 s |
| gq-auth-401 | table-lookup | answer | answer | yes | 100% | 100% | 100% | 2/2 | 2.7 s |
| gq-audit-retention-business | table-lookup | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 3.2 s |
| gq-enterprise-burst | table-lookup | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.8 s |
| gq-jit-vs-scim | near-duplicate | answer | answer | yes | 50.0% | 100% | 100% | 3/3 | 4.6 s |
| gq-deprovisioned-data | near-duplicate | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-enterprise-price | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.2 s |
| gq-ldap | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.8 s |
| gq-google-sso | partial (known miss) | partial | partial | yes | 0% | 0% | 0% | 1/3 | 6.1 s |
| gq-webhook-retries-ips | partial | partial | partial | yes | 50.0% | 100% | 100% | 2/2 | 4.2 s |
| gq-followup-webhook-signature-v2 | follow-up | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 6.5 s |
| gq-followup-rate-limit-enterprise | follow-up | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 5.1 s |
| gq-followup-topic-change-ldap | follow-up | refusal | partial | **no** | - | - | - |  | 5.9 s |
| gq-scim-onelogin | unanswerable | refusal | partial | **no** | - | - | - |  | 5.5 s |
| gq-sso-ping-identity | unanswerable | refusal | partial | **no** | - | - | - |  | 6.4 s |
| gq-webhook-source-ips | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.0 s |
| gq-business-annual-discount | unanswerable | refusal | refusal (no_relevant_passages) | yes | - | - | - |  | 0.0 s |
| gq-upgrade-cost | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 3.4 s |
| gq-active-directory-sync | unanswerable | refusal | partial | **no** | - | - | - |  | 7.3 s |
| gq-google-workspace-provisioning | unanswerable | refusal | partial | **no** | - | - | - |  | 6.3 s |
| gq-v1-end-of-support | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.3 s |
| gq-saml-single-logout | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 3.7 s |
| gq-enterprise-uptime-sla | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 1.6 s |

## How it is scored

- **Outcome**: an unanswerable question expects a Refusal, a `partial` one an Answer stating the gap phrase (`GAP_PHRASE`, anywhere, any case, either apostrophe), any other an Answer without it. An Uncited Answer counts as an Answer. A failed Turn (`rewrite_failed`, `llm_unavailable`, ...) is an `error`. A gap Answer to an unanswerable question is a soft refusal: it says what it couldn't find, but answers neighbouring facts instead of refusing.
- **Blame** for a wrong outcome: `retrieval` when it is a Refusal or a gap and an expected Section wasn't retrieved, so the model never saw it; `model` otherwise; `error` for a failed Turn.
- **Citation precision and recall** are at Section level, over distinct Sections; citing any alternative of an expected source counts for it. Precision averages over the Answers that cite something; recall over the answerable questions, where a Refusal or an Uncited Answer scores 0. Precision is against the Golden Question's expected Sections only, so a correctly cited extra fact (a v2 caveat, a related error code) lowers it: read it as focus, not as wrong Citations.
- **Retrieval recall**: the share of expected sources with any option among the retrieved Passages.
- **must_mention**: whole-word, case-insensitive term groups (any term in a group counts), over every group of the answerable questions. **Standalone** checks a Follow-up's `standalone_must_mention` against its rewrite.
- **Latency** is the whole Turn, rewrite included; **TTFT** is to the first streamed token.
- **Cost** is at list price from the providers' reported token usage. A model Refusal (`not_in_context`) stops its stream at the sentinel, before the provider reports usage, so its generation call isn't charged: each one is under-counted by its prompt (about 3K input tokens).
