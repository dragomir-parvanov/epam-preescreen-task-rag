<!-- session: 95e6c140-24b4-4a85-994b-54e57a85d674 -->

## user · 2026-10-23 11:24:11 · context 4.2% (42k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6

## assistant · 2026-10-23 11:24:37 · context 5.4% (54k / 1000k)

Claimed the corpus ticket; checking the brief and glossary before the first grilling round.

## assistant · 2026-10-23 11:25:21 · context 5.8% (57.5k / 1000k)

I've claimed **Knowledge-base corpus: domain, articles, metadata and planted hard cases** (part of **Map: Enterprise Knowledge Base RAG Chatbot**). Nothing blocks it, and its answer feeds **Chunking & retrieval strategy** and **Test & evaluation strategy**. There is no `GLOSSARY.md` or `docs/adr/` yet, so the terms we settle here will be the first entries.

This round covers the decisions that don't depend on each other. The article list, planted hard cases and golden questions depend on the answers, so they come next round.

❓ **Q1 - Product and domain**: CSMs answer *complex client configuration questions*, so the articles should read like admin/configuration manuals for one enterprise SaaS. Options:
- **(a) One product, one article per area.** A fictional B2B platform, e.g. **OmniCorp Nimbus**, a workflow/integration platform, with plan tiers (Starter / Business / Enterprise) and two platform versions (v2 legacy, v3 current). Cross-article questions come naturally: SCIM needs SSO *and* the Enterprise tier, and rate limits depend on both plan and version.
- (b) Several unrelated products, one article each. Cross-article questions would feel forced, and the corpus would read like a demo.
- (c) A non-SaaS domain (hardware, insurance). That is further from "configuration questions" and harder to make realistic.

➡️ (a): one product, **OmniCorp Nimbus**, with plan tiers and v2/v3. Tiers and versions are what make the hard cases real rather than contrived.

---

❓ **Q2 - Corpus size and article style**: The brief says 3–5 articles. I suggest **5**, each **~800–1,500 words** with 4–8 H2/H3 sections. That length makes chunking actually matter: several chunks per article, and some sections longer than one chunk. Articles should mix prose, numbered setup steps, **tables** (config matrices, error codes) and short code/config blocks (a SAML attribute map, a webhook payload).

➡️ Yes: 5 articles, ~800–1,500 words each, with mixed content (prose, steps, tables, code blocks).

---

❓ **Q3 - File format and metadata schema**: Markdown with YAML front-matter, one file per article. Proposed front-matter:

```yaml
id: nimbus-sso-saml          # stable slug, used in citations
title: Configuring SSO with SAML 2.0
product: OmniCorp Nimbus
applies_to: [v3]             # platform versions the article describes
doc_type: guide              # guide | reference | release-notes
status: current              # current | deprecated
last_updated: 2026-08-14
owner: Identity Team
```

The section heading path (e.g. `Troubleshooting > Error AUTH-403`) is **derived from the markdown body at ingestion**, not written in the front-matter. Leave out tags/keywords so retrieval has to work from the content.

➡️ Yes, that schema. `id`, `title`, `applies_to` and `status` are what the citation and version-conflict behaviour rely on. The rest is there for realism and display.

---

❓ **Q4 - How version conflicts are represented**: Two options:
- **(a) A separate legacy article.** A v2→v3 migration / legacy-behaviour article (`applies_to: [v2]`, `status: deprecated` for the v2 parts) contradicts current articles on specific facts, such as the webhook signature algorithm and rate-limit values. Retrieval sees two plausible chunks that disagree, and only the metadata tells them apart.
- (b) Version sections inside the same article ("In v2… In v3…"). This is easier for the model and teaches less, because the conflict is resolved in the text.

➡️ (a). One of the 5 articles is the **v2→v3 migration guide**, which holds the conflicting v2 facts. That makes "which version applies?" a real grounding test for the citation contract.

---

❓ **Q5 - Where the corpus lives**: Options are `knowledge-base/` at the repo root (visible to reviewers, mounted read-only into the backend container) or `backend/knowledge_base/` (inside the backend's Docker build context, so it's baked into the image). How ingestion is triggered is decided later in **Operational readiness**. This question only decides location.

➡️ `knowledge-base/` at the repo root, mounted read-only into the backend. The corpus is content, not code, and a reviewer should find it in one click.

---

❓ **Q6 - Domain terms**: The brief mixes "manuals", "documents" and "articles". Proposed canonical terms for `GLOSSARY.md`:
- **Knowledge Base**: the whole set of internal articles the assistant may answer from.
- **Article**: one authored source file in the Knowledge Base, the unit a CSM would open to verify an answer. ("Document" and "manual" are avoided as synonyms.)
- **Section**: a heading-delimited part of an Article, identified by its heading path.
- **Platform Version** (v2 / v3) and **Plan Tier** (Starter / Business / Enterprise): domain facts of the fictional product, needed to phrase hard cases precisely.

(*Chunk*, *Citation*, *Source* and *Refusal* are left to **Citation & grounding contract**.)

➡️ Yes, those terms, with "Article" as the canonical unit.

---

❓ **Q7 - Who writes the articles, and when**: Resolving this ticket spawns a build ticket. Options: (a) one AFK build ticket where an agent writes all 5 articles from the outline we agree here, plus a golden-questions file, delivered as a PR you review; (b) you write them yourself (HITL).

➡️ (a): one build ticket, agent-written from a tight per-article outline (sections, the exact planted facts and tables), reviewed in the PR. The planted facts are the part that matters, so we lock them here and the prose can be generated.

## user · 2026-10-23 11:33:18 · context 6.1% (61.2k / 1000k)

q1: reccomended
q2: reccomended
q3: reccomended
q4: reccomended
q5: it has somehow be loaded into the vector db, right?
q6: yes
q7: a

## assistant · 2026-10-23 11:34:17 · context 6.4% (64k / 1000k)

I've created `GLOSSARY.md` with the settled terms (Knowledge Base, Article, Section, OmniCorp Nimbus, Platform Version, Plan Tier, CSM). It's in the working tree only, not committed.

**On Q5:** yes. The folder is only where the source Articles live. An **ingestion** step reads each markdown file, splits it into chunks, embeds them and writes them to the vector store. The files are the source of truth, and the vector store is derived from them and can be rebuilt at any time. *When* ingestion runs (on backend startup, a `pixi run ingest` task, or an API call) is decided in **Operational readiness**. Here we only decide where the backend reads from.

Round 2:

❓ **Q5′ - Corpus location**: `knowledge-base/` at the repo root, mounted read-only into the backend container, and read by ingestion from there.

➡️ Yes, `knowledge-base/` at the root.

---

❓ **Q8 - Article list and planted facts**: Five Articles. All are v3 unless noted. The **bold** facts are deliberately planted:

| # | `id` / title | Type | Sections and planted facts |
|---|---|---|---|
| 1 | `nimbus-plan-tiers`, *Plan Tiers and Entitlements* | reference | Feature × tier **matrix table**: SSO Business+, **SCIM Enterprise only**, API access Business+, **audit-log retention 30 / 90 / 365 days**, data regions EU/US on all tiers, **APAC Enterprise only**. Seat limits. No prices. |
| 2 | `nimbus-sso-saml`, *Configuring SSO with SAML 2.0* | guide | Setup steps for Okta and Microsoft Entra ID (no other IdPs). **Attribute-mapping table** (`email`, `firstName`, `lastName`, `groups`). **JIT provisioning**. Enforcing SSO plus a break-glass admin. **Error-code table**: AUTH-401 clock skew > 5 min, AUTH-403 user not assigned to the app, AUTH-409 duplicate email. |
| 3 | `nimbus-scim-provisioning`, *Automated User Provisioning with SCIM 2.0* | guide | Prerequisites: "Enterprise tier, see *Plan Tiers*" and **SSO must be configured first**. Token generation (**token expires after 365 days**). Group → role mapping. **Deprovisioning suspends the user; their data is kept 30 days and then deleted.** Sync runs **every 40 min**. |
| 4 | `nimbus-api-webhooks`, *API Rate Limits and Webhooks* | reference | **Rate-limit table**: Business 600 req/min, Enterprise 3,000 req/min, burst ×2 for 10 s. 429 responses carry a `Retry-After` header. Webhooks are signed with **HMAC-SHA256 in `X-Nimbus-Signature-256`**. **8 retries with exponential backoff over 24 h; an endpoint is auto-disabled after 3 days of failures.** Example payload. |
| 5 | `nimbus-v2-to-v3-migration`, *Migrating from Nimbus v2 to v3* | guide, `applies_to: [v2, v3]` | "What changed" summary. **v2 end of support 2027-03-31.** A **Legacy v2 reference** section written as plain statements with no "in v2" framing: webhooks signed with **HMAC-SHA1 in `X-Nimbus-Signature`**, **300 req/min flat for all tiers**, SAML attribute **`mail`** instead of `email`. |

➡️ Yes, this list and these facts. Each fact exists so that at least one golden question depends on it.

---

❓ **Q9 - Planted hard cases**: Each category below is what a specific retrieval or grounding behaviour gets judged against:

- **H1 Cross-article.** "Can a Business-tier client set up SCIM with Okta?" The answer is no: SCIM is Enterprise-only (Article 1) and needs SSO first (Articles 3 and 2). The answer needs at least two Articles.
- **H2 Version conflict.** "Which header carries the webhook signature?" Article 4 (v3) and Article 5 (v2) disagree. The answer should give v3 and flag v2, or say it depends on the version. "What's the API rate limit?" depends on both tier and version.
- **H3 Table lookup.** "What does AUTH-401 mean?" or "How long are audit logs kept on Business?" The fact sits in one table cell, which tests whether tables chunk well.
- **H4 Near-duplicate terms.** JIT provisioning vs SCIM provisioning. "Suspended" vs "deleted". **"30 days"** appears as both Starter audit-log retention and deprovisioned-user data retention. These look alike semantically but have different answers.
- **H5 Unanswerable.** "How much does Enterprise cost?" (prices aren't in the Knowledge Base) and "Does Nimbus support LDAP?" (never mentioned, so the assistant must refuse rather than guess "no").
- **H6 Partially answerable.** "How do I set up SSO with Google Workspace, and what attributes are required?" The attribute part can be answered. The Google-specific steps can't, because only Okta and Entra are covered.

➡️ Yes, all six categories are planted.

---

❓ **Q10 - Golden-question file format and location**: These are machine-readable so **Test & evaluation strategy** can reuse them. The file would be `eval/golden-questions.yaml` at the repo root, kept out of `knowledge-base/` so ingestion never indexes it. Each entry:

```yaml
- id: gq-scim-business-tier
  question: Can a Business-tier client set up SCIM provisioning with Okta?
  category: cross-article        # cross-article | version-conflict | table-lookup | near-duplicate | unanswerable | partial
  answerable: true               # false → a Refusal is expected
  expected_sources:              # Article id + Section heading path
    - { article: nimbus-plan-tiers, section: "Feature matrix" }
    - { article: nimbus-scim-provisioning, section: "Prerequisites" }
  expected_facts: ["SCIM requires the Enterprise tier"]
```

How the file is *run* and scored stays with **Test & evaluation strategy**.

➡️ Yes, `eval/golden-questions.yaml` with this shape. Next round we'd fix the seed list: about 12–15 questions, at least 2 per category.

## user · 2026-10-23 11:39:25 · context 6.8% (68.5k / 1000k)

q5: yes
q8: yes
q9: yes
q10: yes

## assistant · 2026-10-23 11:40:05 · context 6.8% (68.5k / 1000k)

Round 3 covers the golden questions, plus one gap I found in the metadata.

❓ **Q11 - Seed golden questions** (14 in total, at least 2 per category). The Section names listed below become the required headings in the Articles.

| id | Question | Category | Expected answer | Expected sources (Article › Section) |
|---|---|---|---|---|
| gq-scim-business-tier | Can a Business-tier client set up SCIM provisioning with Okta? | cross-article | No. SCIM is Enterprise-only and also needs SSO configured first | plan-tiers › Feature matrix; scim › Prerequisites |
| gq-entra-auto-deprovision | An Enterprise client on Entra ID wants leavers removed automatically. What must be set up, and what happens to their data? | cross-article | SAML SSO with Entra, then SCIM. The leaver is suspended and their data deleted after 30 days | sso › Configuring Microsoft Entra ID; scim › Prerequisites; scim › Deprovisioning |
| gq-webhook-signature | Which header carries the webhook signature, and what algorithm is used? | version-conflict | v3: `X-Nimbus-Signature-256`, HMAC-SHA256. v2 differs: `X-Nimbus-Signature`, HMAC-SHA1 | api-webhooks › Verifying signatures; v2 › Webhooks (v2) |
| gq-rate-limit-business | What is the API rate limit for a Business client? | version-conflict | 600 req/min on v3 (v2: 300 req/min flat) | api-webhooks › Rate limits; v2 › API limits (v2) |
| gq-v2-saml-email | A client still on v2 asks which SAML attribute carries the user's email. | version-conflict | `mail` (v3 uses `email`) | v2 › SAML attributes (v2) |
| gq-auth-401 | What does error AUTH-401 mean and how is it fixed? | table-lookup | IdP/SP clock skew over 5 minutes, fixed by syncing the clocks | sso › Troubleshooting |
| gq-audit-retention-business | How long are audit logs kept on the Business tier? | table-lookup | 90 days | plan-tiers › Feature matrix |
| gq-enterprise-burst | How far can an Enterprise client burst above its rate limit? | table-lookup | ×2 (6,000 req/min) for 10 s | api-webhooks › Rate limits |
| gq-jit-vs-scim | What's the difference between JIT provisioning and SCIM? | near-duplicate | JIT creates a user on first SSO login and never deprovisions. SCIM syncs every 40 min, including deprovisioning | sso › Just-in-time provisioning; scim › Overview |
| gq-deprovisioned-data | Is a deprovisioned user's data deleted immediately? | near-duplicate | No. The user is suspended and the data deleted after 30 days. (Distractor: Starter's 30-day audit-log retention) | scim › Deprovisioning |
| gq-enterprise-price | How much does the Enterprise tier cost per seat? | unanswerable | Refusal | none |
| gq-ldap | Does Nimbus support LDAP directory sync? | unanswerable | Refusal (not a confident "no") | none |
| gq-google-sso | How do I set up SSO with Google Workspace, and which attributes are required? | partial | Attributes from the mapping table. States that Google-specific steps aren't covered | sso › Attribute mapping |
| gq-webhook-retries-ips | How many times are failed webhooks retried, and which IP ranges should the client allowlist? | partial | 8 retries over 24 h. IP ranges aren't documented | api-webhooks › Retries and auto-disable |

How an answer should *behave* on a version conflict when the question doesn't say which version (default to v3? give both? ask?) is left to **Citation & grounding contract**. These rows only fix the facts and the sources.

➡️ Yes, these 14 as the seed set. The build ticket writes them into `eval/golden-questions.yaml` and keeps the Article headings exactly as listed.

---

❓ **Q12 - Metadata gap in Article 5**: `applies_to` and `status` belong to the whole Article, but Article 5 as I drafted it mixes v2 and v3 content (`applies_to: [v2, v3]`, `status: current`). A chunk from its Legacy v2 section would then carry metadata that *doesn't* mark it as v2, the `status: deprecated` value would never be used, and the Q4 design would lose its point. Fix: re-scope it as **`nimbus-v2-legacy`, *Nimbus v2 Legacy Reference*** with `applies_to: [v2]` and `status: deprecated`. It documents v2 behaviour, the end-of-support date, and an "Upgrading to v3" section that points to the current Articles. Every chunk from it is then marked v2/deprecated by metadata alone.

➡️ Yes, re-scope Article 5 this way. (Per-Section version metadata is the alternative, but it complicates the schema for one Article.)

---

❓ **Q13 - Cross-references and build-ticket scope**: Articles link to each other with relative markdown links where a real manual would (e.g. SCIM Prerequisites → `[Plan Tiers and Entitlements](nimbus-plan-tiers.md)`). Links are text only and are not followed at retrieval time. The build ticket (**Write the Knowledge Base articles and golden questions**, AFK) delivers just the 5 Articles in `knowledge-base/` and `eval/golden-questions.yaml`: no ingestion code and no Compose mount, which belong to later build tickets. Its acceptance criteria are that every planted fact from Q8 (with the Q12 change) appears verbatim, every Section named in Q11 exists with that exact heading, all front-matter validates against the Q3 schema, and every Article is 800–1,500 words.

➡️ Yes to both.

## user · 2026-10-23 11:40:12 · context 7.3% (72.7k / 1000k)

reccomended

## assistant · 2026-10-23 11:40:23 · context 7.3% (72.7k / 1000k)

The design tree is fully worked and you accepted every recommendation. Recording the resolution now.

## assistant · 2026-10-23 11:41:16 · context 8% (80.4k / 1000k)

Now the map's Decisions-so-far (re-fetching first, since other sessions may have edited it).

## assistant · 2026-10-23 11:41:31 · context 8.2% (82k / 1000k)

**Knowledge-base corpus: domain, articles, metadata and planted hard cases** is now resolved and closed.

- **Decision** (the full spec is in the [resolution comment](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6#issuecomment-6361002781)):
  - **Product:** one fictional product, OmniCorp Nimbus, with Starter/Business/Enterprise tiers and two platform versions, v2 and v3.
  - **Articles:** five markdown files with YAML front-matter in `knowledge-base/`. Each planted fact is written down exactly.
  - **Version conflicts:** all v2 facts live in one separate, deprecated v2 Article. A v2 chunk can then only be told apart from a v3 chunk by its metadata.
  - **Test material:** six categories of planted hard cases, and 14 seed golden questions for `eval/golden-questions.yaml`.
- **New build ticket:** [Write the Knowledge Base articles and golden questions](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/17). It's an agent-only ticket with acceptance criteria, including a pytest check that every golden question's expected sources point to real Article headings.
- **Map:** a pointer to this decision is added to Decisions so far. Closing this ticket unblocks **Chunking & retrieval strategy** and **Test & evaluation strategy**.
- **`GLOSSARY.md`:** created in the working tree but **not committed**. You're on `build/walking-skeleton`, so I left it there. Either commit it yourself wherever you like, or let the build ticket's PR include it (that's in its scope).

How an answer should behave on a version conflict when the question doesn't name a version is deliberately left to **Citation & grounding contract**.

