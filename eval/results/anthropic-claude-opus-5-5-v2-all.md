# LLM eval: anthropic claude-opus-5-5, prompt v2

| Run |  |
| --- | --- |
| Date | 2026-10-23T14:06:41+00:00 |
| Git SHA | 927a9b6 |
| Provider | anthropic |
| Model | claude-opus-5-5 (effort low) |
| Prompt version | v2 |
| Retrieval | hybrid, top_k 8, min_score 0.66 |
| Questions | all (317 questions) |
| Concurrency | 4 Turn(s) at a time |

## Headline

Over 315 questions: the 2 known retrieval misses are reported apart below.

| Metric | Value |
| --- | --- |
| Outcome accuracy | 95.2% (300/315) |
| Refusal correctness | 9/13 unanswerable refused (4 got a gap Answer instead); 1 answerable refused |
| Citation precision | 30.1% |
| Citation recall | 94.9% |
| Retrieval recall | 96.0% |
| Uncited rate | 0% |
| must_mention hit rate | 94.4% |
| Standalone must_mention | 100% |
| Errors | 0 |
| Latency p50 / p95 | 5.1 s / 7.3 s |
| TTFT p50 | 2.1 s |
| Tokens | 1,215,230 input + 137,766 output tokens |
| Cost | $7.62 ($0.0242 a question) |

Whole run, known misses included: 1,222,583 input + 139,294 output tokens, $7.68.

## By category

| Category | n | Outcome | Cit. P | Cit. R | Retr. R | must_mention | p50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cross-article | 1 | 100% | 33.3% | 100% | 100% | 100% | 5.9 s |
| follow-up | 3 | 100% | 29.2% | 100% | 100% | 100% | 5.2 s |
| near-duplicate | 2 | 100% | 50.0% | 100% | 100% | 100% | 3.7 s |
| partial | 1 | 100% | 50.0% | 100% | 100% | 100% | 4.1 s |
| single-article | 290 | 96.2% | 29.6% | 94.7% | 95.9% | 94.2% | 5.2 s |
| table-lookup | 3 | 100% | 52.8% | 100% | 100% | 100% | 3.2 s |
| unanswerable | 12 | 66.7% | - | - | - | - | 2.5 s |
| version-conflict | 3 | 100% | 33.3% | 100% | 100% | 100% | 4.7 s |

## Wrong outcomes

| Question | Expected | Got | Blame | Retr. R | Answer |
| --- | --- | --- | --- | --- | --- |
| gq-scim-onelogin | refusal | partial | model | - | The SCIM setup steps I found are for **Okta** and **Microsoft Entra ID** only [1]. **General prerequisites for SCIM provisioning:** 1. The workspace must be on… |
| gq-sso-ping-identity | refusal | partial | model | - | Nimbus acts as a standard SAML 2.0 service provider and supports both SP-initiated and IdP-initiated sign-in [1]. The documented step-by-step setups are for Ok… |
| gq-active-directory-sync | refusal | partial | model | - | Nimbus syncs users and groups from an identity provider (IdP) using the SCIM 2.0 protocol [1]. Once connected, the IdP sends Nimbus every change to the users a… |
| gq-google-workspace-provisioning | refusal | partial | model | - | Nimbus offers two ways to create users automatically. **SCIM 2.0 provisioning (Enterprise tier):** SCIM creates, updates and deactivates users from the identit… |
| gq-admin-bulk-user-import-2 | answer | partial | model | 100% | If the workspace doesn't have enough seats for every valid row, Nimbus stops the **whole import** before any invitation email goes out [1][2]. It doesn't send … |
| gq-admin-changing-roles-2 | answer | partial | retrieval | 50.0% | The role is most likely coming from the client's identity provider. In a workspace where roles are assigned by the identity provider, the group mapping still a… |
| gq-admin-exporting-the-audit-log-2 | answer | partial | model | 100% | **Yes, but not through a built-in setting.** Nimbus has no built-in scheduled export [1]. On any Plan Tier with API access, the client can build a workflow tha… |
| gq-api-api-keys-1 | answer | partial | model | 100% | Because Nimbus stores only a hash of each key's secret, no one can display it again, including the client's Admins and OmniCorp support [1][2]. The key's **nam… |
| gq-api-approvals-2 | answer | partial | model | 100% | If nobody approves or rejects the request within 7 days, the approval expires and the run fails with error **WF-410** [1][2]. The approval is then marked as ex… |
| gq-api-schedules-1 | answer | partial | model | 100% | To make a schedule follow a particular office's clock, set the schedule's `time_zone` field to that office's IANA time zone name, such as `Europe/London` or `A… |
| gq-api-webhook-endpoints-1 | answer | partial | model | 100% | No, the signing secret can't be retrieved again after registration. When you register an endpoint through the API, the response contains the new `whk_` id and … |
| gq-api-workspace-2 | answer | refusal (not_in_context) | retrieval | 0% |  |
| gq-security-access-reviews-2 | answer | partial | retrieval | 0% | For an access review, every API key in the workspace needs checking, because each key acts with Admin permissions and has no scopes [1]. Keys are listed in the… |
| gq-security-api-key-hygiene-2 | answer | partial | retrieval | 0% | On the current platform, Admins manage keys under **Settings > Developers > API keys**, and the API Keys API can list all of a workspace's keys [1]. Watching w… |
| gq-security-compliance-reports-1 | answer | partial | retrieval | 0% | Clients receive the SOC 2 Type II report through their CSM, under NDA [1]. The report is confidential: never attach it to a ticket, post it in a shared channel… |

## Missed must_mention terms

| Question | Missed (first term of each group) | Answer |
| --- | --- | --- |
| gq-admin-api-keys-1 | `shown once` | No. The key value is shown only once, when the key is created [1][2]. Nimbus stores only a one-way hash of it, so neither the console, the API nor OmniCorp sup… |
| gq-admin-changing-roles-2 | `overwritten` | The role is most likely coming from the client's identity provider. In a workspace where roles are assigned by the identity provider, the group mapping still a… |
| gq-admin-promoting-workflows-1 | `per environment` | **No.** Promotion copies the workflow definition but never copies connections or environment variable values, because those belong to each environment [1][2]. … |
| gq-admin-workspace-settings-1 | `next occurrence` | When an Admin changes the workspace time zone, only scheduled workflows whose trigger has **no time zone of its own** are affected, and they start running at t… |
| gq-api-api-keys-1 | `last_four` | Because Nimbus stores only a hash of each key's secret, no one can display it again, including the client's Admins and OmniCorp support [1][2]. The key's **nam… |
| gq-api-secrets-1 | `never`, `Write-only` | No. A client can't read back a secret's value through the Secrets API; it returns secret names only [1][2]. The API can create, replace and delete a secret and… |
| gq-api-webhook-endpoints-1 | `rolled` | No, the signing secret can't be retrieved again after registration. When you register an endpoint through the API, the response contains the new `whk_` id and … |
| gq-api-workflows-2 | `50` | No, renaming a workflow doesn't create a new version. A `PATCH /workflows/{id}` that changes only `name`, `description`, `folder_id` or `owner_id` updates the … |
| gq-security-access-reviews-2 | `GET /api-keys`, `last_used_at`, `created_by` | For an access review, every API key in the workspace needs checking, because each key acts with Admin permissions and has no scopes [1]. Keys are listed in the… |
| gq-security-api-key-hygiene-2 | `last_used_at`, `/api-keys` | On the current platform, Admins manage keys under **Settings > Developers > API keys**, and the API Keys API can list all of a workspace's keys [1]. Watching w… |
| gq-security-audit-events-2 | `secret.updated`, `never logged` | No, the audit log never stores a secret's value. Creating, updating and deleting a secret are recorded in **Settings > Audit log** by name only [1][2]. A few r… |
| gq-security-compliance-reports-1 | `Security documentation request` | Clients receive the SOC 2 Type II report through their CSM, under NDA [1]. The report is confidential: never attach it to a ticket, post it in a shared channel… |
| gq-security-credential-storage-1 | `never` | No. Secret values are write-only, so once a secret is saved, nobody can read its value back, in the console or through the API [1]. This includes Admins and Om… |
| gq-security-data-deletion-1 | `Erased immediately`, `new connection` | When a Builder or Admin deletes a connection, Nimbus **erases its stored credentials immediately**; there is no retention period [1][2]. Those credentials can … |
| gq-tier-active-connector-limits-1 | `count once` | It counts as **one active connector** [1][2]. The active connector limit is per connector, not per connection, so a sandbox org and a production org on the Sal… |
| gq-tier-audit-log-streaming-2 | `CSV export` | When a destination rejects a batch or doesn't return a 2xx status within 10 seconds, Nimbus keeps the batch and retries it with exponential backoff for up to 2… |
| gq-tier-environments-1 | `Production version` | No. Promotion never copies connection assignments or environment variables, because each environment keeps its own [1][2]. This means promoting can't accidenta… |
| gq-tier-seat-limits-1 | `Accepting an invitation` | No. Neither a pending invitation nor a suspended user takes a seat [1]. Only active users hold seats, and every active user counts as one seat whatever their r… |
| gq-tier-usage-dashboard-2 | `5-minute refresh` | For a resource that is Unlimited on the client's Plan Tier, `GET /workspace/usage` still returns the counter with its `used` figure, but `limit` is `null` [1][… |
| gq-troubleshooting-database-connections-2 | `Route through agent` | The client needs the private connector agent, which is an Enterprise feature [1][2]. On other plan tiers, the SQL Server's port (1433 by default) must accept T… |
| gq-troubleshooting-password-sign-in-1 | `10 failed attempts` | After **10 consecutive failed sign-in attempts**, a Nimbus account is locked for **15 minutes** [1][2]. The count covers every device and browser, and a succes… |
| gq-troubleshooting-third-party-throttling-1 | `CONN-429` | When a third-party app such as Zendesk throttles the connector, Nimbus **backs off and retries the step automatically** [1][2]. The connection stays **Connecte… |
| gq-v2-admin-api-keys-2 | `shown once` | No. On v2 (deprecated), an API key is shown only once, when it is created, and it can't be retrieved afterwards [1][2]. The client needs to replace the key ins… |
| gq-v2-security-sessions-2 | `optional` | No. On v2 (deprecated), the Admin menu has no session or password settings, so an Admin can't require two-factor authentication for the whole workspace [1]. A … |
| gq-v2-troubleshooting-workflow-runs-2 | `POST /workflows/{id}/runs` | On v2, which is deprecated, there is no retry button or retry endpoint, so the client starts the run again by hand [1][2]. 1. **Fix the cause first.** For exam… |

## Known retrieval misses

Their answering Sections are never retrieved, so expect a Refusal or a gap Answer.

| Question | Expected | Got | Retr. R | Why retrieval misses |
| --- | --- | --- | --- | --- |
| gq-entra-auto-deprovision | answer | partial | 0% | "Leavers removed automatically" shares no words with SCIM or deprovisioning, and "what happens to their data" pulls in data-deletion and GDPR Sections, so neither SCIM Section is in the hybrid top 20. Needs query expansion (#28). |
| gq-google-sso | partial | partial | 0% | "Set up SSO with Google Workspace" pulls in workspace-creation, two-factor and FAQ setup Sections; Attribute mapping ranks 20th. Needs query expansion (#28). |

## Every question

| Question | Category | Expected | Got | Right | Cit. P | Cit. R | Retr. R | Terms | Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gq-scim-business-tier | cross-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.9 s |
| gq-entra-auto-deprovision | cross-article (known miss) | answer | partial | **no** | 0% | 0% | 0% | 3/4 | 8.5 s |
| gq-webhook-signature | version-conflict | answer | answer | yes | 40.0% | 100% | 100% | 3/3 | 5.1 s |
| gq-rate-limit-business | version-conflict | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 4.7 s |
| gq-v2-saml-email | version-conflict | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 4.6 s |
| gq-auth-401 | table-lookup | answer | answer | yes | 100% | 100% | 100% | 2/2 | 2.7 s |
| gq-audit-retention-business | table-lookup | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 3.2 s |
| gq-enterprise-burst | table-lookup | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.5 s |
| gq-jit-vs-scim | near-duplicate | answer | answer | yes | 50.0% | 100% | 100% | 3/3 | 4.6 s |
| gq-deprovisioned-data | near-duplicate | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 3.7 s |
| gq-enterprise-price | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.2 s |
| gq-ldap | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.5 s |
| gq-google-sso | partial (known miss) | partial | partial | yes | 0% | 0% | 0% | 1/3 | 5.7 s |
| gq-webhook-retries-ips | partial | partial | partial | yes | 50.0% | 100% | 100% | 2/2 | 4.1 s |
| gq-followup-webhook-signature-v2 | follow-up | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.6 s |
| gq-followup-rate-limit-enterprise | follow-up | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 5.2 s |
| gq-followup-topic-change-ldap | follow-up | refusal | refusal (not_in_context) | yes | - | - | - |  | 4.2 s |
| gq-scim-onelogin | unanswerable | refusal | partial | **no** | - | - | - |  | 6.0 s |
| gq-sso-ping-identity | unanswerable | refusal | partial | **no** | - | - | - |  | 6.3 s |
| gq-webhook-source-ips | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.4 s |
| gq-business-annual-discount | unanswerable | refusal | refusal (no_relevant_passages) | yes | - | - | - |  | 0.0 s |
| gq-upgrade-cost | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 3.2 s |
| gq-active-directory-sync | unanswerable | refusal | partial | **no** | - | - | - |  | 6.3 s |
| gq-google-workspace-provisioning | unanswerable | refusal | partial | **no** | - | - | - |  | 6.5 s |
| gq-v1-end-of-support | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 2.3 s |
| gq-saml-single-logout | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 3.4 s |
| gq-enterprise-uptime-sla | unanswerable | refusal | refusal (not_in_context) | yes | - | - | - |  | 1.3 s |
| gq-admin-api-keys-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/2 | 5.4 s |
| gq-admin-api-keys-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 4.8 s |
| gq-admin-approval-steps-1 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 4.4 s |
| gq-admin-approval-steps-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 6.0 s |
| gq-admin-bulk-user-import-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.8 s |
| gq-admin-bulk-user-import-2 | single-article | answer | partial | **no** | 50.0% | 100% | 100% | 2/2 | 6.7 s |
| gq-admin-changing-roles-1 | single-article | answer | answer | yes | 50.0% | 50.0% | 50.0% | 1/1 | 5.6 s |
| gq-admin-changing-roles-2 | single-article | answer | partial | **no** | 33.3% | 50.0% | 50.0% | 1/2 | 9.9 s |
| gq-admin-creating-a-workspace-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.5 s |
| gq-admin-creating-a-workspace-2 | single-article | answer | answer | yes | 66.7% | 100% | 100% | 1/1 | 6.0 s |
| gq-admin-deleting-a-workspace-1 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 6.0 s |
| gq-admin-deleting-a-workspace-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.5 s |
| gq-admin-exporting-the-audit-log-1 | single-article | answer | answer | yes | 66.7% | 100% | 100% | 3/3 | 4.2 s |
| gq-admin-exporting-the-audit-log-2 | single-article | answer | partial | **no** | 25.0% | 100% | 100% | 2/2 | 6.2 s |
| gq-admin-failure-notifications-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 6.7 s |
| gq-admin-failure-notifications-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.8 s |
| gq-admin-inviting-users-1 | single-article | answer | answer | yes | 28.6% | 100% | 100% | 2/2 | 6.6 s |
| gq-admin-inviting-users-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.3 s |
| gq-admin-promoting-workflows-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 1/2 | 7.0 s |
| gq-admin-promoting-workflows-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 3.6 s |
| gq-admin-requiring-two-factor-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 7.3 s |
| gq-admin-requiring-two-factor-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 4.5 s |
| gq-admin-restoring-workflow-versions-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 4.7 s |
| gq-admin-restoring-workflow-versions-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.6 s |
| gq-admin-run-history-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.8 s |
| gq-admin-run-history-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.7 s |
| gq-admin-scheduling-workflows-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 4.4 s |
| gq-admin-scheduling-workflows-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 4.8 s |
| gq-admin-secrets-vault-1 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 6.2 s |
| gq-admin-secrets-vault-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 8.0 s |
| gq-admin-session-timeouts-1 | single-article | answer | answer | yes | 0% | 0% | 100% | 2/2 | 2.1 s |
| gq-admin-session-timeouts-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.2 s |
| gq-admin-suspending-users-1 | single-article | answer | answer | yes | 0% | 0% | 0% | 2/2 | 5.6 s |
| gq-admin-suspending-users-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 3.5 s |
| gq-admin-transferring-workflow-ownership-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.0 s |
| gq-admin-transferring-workflow-ownership-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.8 s |
| gq-admin-webhook-endpoints-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.6 s |
| gq-admin-webhook-endpoints-2 | single-article | answer | answer | yes | 0% | 0% | 0% | 2/2 | 7.0 s |
| gq-admin-workspace-settings-1 | single-article | answer | answer | yes | 0% | 0% | 0% | 1/2 | 5.1 s |
| gq-admin-workspace-settings-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 3.7 s |
| gq-api-api-keys-1 | single-article | answer | partial | **no** | 20.0% | 100% | 100% | 0/1 | 8.4 s |
| gq-api-api-keys-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 4.7 s |
| gq-api-approvals-1 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 6.5 s |
| gq-api-approvals-2 | single-article | answer | partial | **no** | 25.0% | 100% | 100% | 2/2 | 7.2 s |
| gq-api-audit-log-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 7.2 s |
| gq-api-audit-log-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-api-connections-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.7 s |
| gq-api-connections-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.7 s |
| gq-api-environments-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 5.2 s |
| gq-api-environments-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 6.0 s |
| gq-api-error-format-1 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 4.8 s |
| gq-api-error-format-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 4.6 s |
| gq-api-folders-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.1 s |
| gq-api-folders-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.8 s |
| gq-api-inbound-webhook-triggers-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.7 s |
| gq-api-inbound-webhook-triggers-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.5 s |
| gq-api-invitations-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 3.5 s |
| gq-api-invitations-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 6.3 s |
| gq-api-run-steps-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.3 s |
| gq-api-run-steps-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 2.7 s |
| gq-api-runs-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.6 s |
| gq-api-runs-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-api-schedules-1 | single-article | answer | partial | **no** | 33.3% | 100% | 100% | 2/2 | 5.9 s |
| gq-api-schedules-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 6.2 s |
| gq-api-secrets-1 | single-article | answer | answer | yes | 60.0% | 100% | 100% | 0/2 | 3.8 s |
| gq-api-secrets-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.8 s |
| gq-api-users-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.1 s |
| gq-api-users-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 5.9 s |
| gq-api-webhook-deliveries-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.3 s |
| gq-api-webhook-deliveries-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.9 s |
| gq-api-webhook-endpoints-1 | single-article | answer | partial | **no** | 33.3% | 100% | 100% | 1/2 | 9.1 s |
| gq-api-webhook-endpoints-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.7 s |
| gq-api-workflows-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 3.7 s |
| gq-api-workflows-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/2 | 5.0 s |
| gq-api-workspace-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.2 s |
| gq-api-workspace-2 | single-article | answer | refusal (not_in_context) | **no** | - | 0% | 0% | 0/2 | 3.3 s |
| gq-connector-amazon-s3-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-connector-amazon-s3-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.2 s |
| gq-connector-asana-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.8 s |
| gq-connector-asana-2 | single-article | answer | answer | yes | 100% | 100% | 100% | 2/2 | 3.9 s |
| gq-connector-azure-blob-storage-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.1 s |
| gq-connector-azure-blob-storage-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.8 s |
| gq-connector-bamboohr-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.6 s |
| gq-connector-bamboohr-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.8 s |
| gq-connector-box-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.3 s |
| gq-connector-box-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-connector-dropbox-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.4 s |
| gq-connector-dropbox-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.8 s |
| gq-connector-dynamics-365-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 6.0 s |
| gq-connector-dynamics-365-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 4.4 s |
| gq-connector-github-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 3/3 | 4.8 s |
| gq-connector-github-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.3 s |
| gq-connector-gitlab-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.8 s |
| gq-connector-gitlab-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.7 s |
| gq-connector-http-request-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.4 s |
| gq-connector-http-request-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.3 s |
| gq-connector-hubspot-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 2.6 s |
| gq-connector-hubspot-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 5.8 s |
| gq-connector-intercom-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 4.3 s |
| gq-connector-intercom-2 | single-article | answer | answer | yes | 66.7% | 100% | 100% | 2/2 | 5.5 s |
| gq-connector-jira-cloud-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 1/1 | 5.7 s |
| gq-connector-jira-cloud-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 2.7 s |
| gq-connector-marketo-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.4 s |
| gq-connector-marketo-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 3.4 s |
| gq-connector-microsoft-teams-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 5.7 s |
| gq-connector-microsoft-teams-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 8.4 s |
| gq-connector-mysql-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.4 s |
| gq-connector-mysql-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-connector-netsuite-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 4.1 s |
| gq-connector-netsuite-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 3.0 s |
| gq-connector-postgresql-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.7 s |
| gq-connector-postgresql-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.7 s |
| gq-connector-salesforce-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 6.0 s |
| gq-connector-salesforce-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.1 s |
| gq-connector-servicenow-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.3 s |
| gq-connector-servicenow-2 | single-article | answer | answer | yes | 0% | 0% | 0% | 2/2 | 2.8 s |
| gq-connector-sftp-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.6 s |
| gq-connector-sftp-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.1 s |
| gq-connector-sharepoint-online-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 4.3 s |
| gq-connector-sharepoint-online-2 | single-article | answer | answer | yes | 100% | 100% | 100% | 2/2 | 4.4 s |
| gq-connector-slack-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-connector-slack-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 5.7 s |
| gq-connector-snowflake-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 9.9 s |
| gq-connector-snowflake-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-connector-sql-server-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 7.4 s |
| gq-connector-sql-server-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.8 s |
| gq-connector-twilio-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 2.4 s |
| gq-connector-twilio-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.8 s |
| gq-connector-workday-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.4 s |
| gq-connector-workday-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.0 s |
| gq-connector-zendesk-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 5.8 s |
| gq-connector-zendesk-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.0 s |
| gq-faq-api-and-integrations-1 | single-article | answer | answer | yes | 100% | 100% | 100% | 2/2 | 4.8 s |
| gq-faq-api-and-integrations-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 7.1 s |
| gq-faq-connectors-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.7 s |
| gq-faq-connectors-2 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 5.9 s |
| gq-faq-getting-started-1 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 4.4 s |
| gq-faq-getting-started-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.9 s |
| gq-faq-notifications-and-alerts-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-faq-notifications-and-alerts-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.9 s |
| gq-faq-security-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.9 s |
| gq-faq-security-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 3.0 s |
| gq-faq-upgrading-from-v2-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-faq-upgrading-from-v2-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 7.1 s |
| gq-faq-user-management-1 | single-article | answer | answer | yes | 0% | 0% | 100% | 1/1 | 1.9 s |
| gq-faq-user-management-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.6 s |
| gq-faq-workflow-builder-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.7 s |
| gq-faq-workflow-builder-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 4.6 s |
| gq-faq-workspace-and-account-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-faq-workspace-and-account-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.7 s |
| gq-release-2-15-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.5 s |
| gq-release-2-15-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.8 s |
| gq-release-2-16-1 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 6.8 s |
| gq-release-2-16-1-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 4.6 s |
| gq-release-2-16-1-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 7.9 s |
| gq-release-2-16-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.5 s |
| gq-release-2-16-2-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.9 s |
| gq-release-2-16-2-2 | single-article | answer | answer | yes | 100% | 100% | 100% | 2/2 | 3.9 s |
| gq-release-2-16-3-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 3/3 | 5.8 s |
| gq-release-2-16-3-2 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 2/2 | 7.0 s |
| gq-release-3-0-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-release-3-0-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 3/3 | 3.6 s |
| gq-release-3-1-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.3 s |
| gq-release-3-1-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 3.8 s |
| gq-release-3-2-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.2 s |
| gq-release-3-2-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.6 s |
| gq-release-3-3-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.2 s |
| gq-release-3-3-2 | single-article | answer | answer | yes | 0% | 0% | 100% | 2/2 | 6.1 s |
| gq-release-3-4-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 2.3 s |
| gq-release-3-4-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.0 s |
| gq-release-3-5-1 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 3/3 | 5.9 s |
| gq-release-3-5-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.6 s |
| gq-release-3-6-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 6.6 s |
| gq-release-3-6-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 6.3 s |
| gq-release-3-7-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 7.5 s |
| gq-release-3-7-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.0 s |
| gq-release-3-8-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 3/3 | 5.1 s |
| gq-release-3-8-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.2 s |
| gq-release-3-9-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 2.5 s |
| gq-release-3-9-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 3/3 | 5.3 s |
| gq-security-access-reviews-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 6.2 s |
| gq-security-access-reviews-2 | single-article | answer | partial | **no** | 0% | 0% | 0% | 0/3 | 6.3 s |
| gq-security-api-key-hygiene-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.7 s |
| gq-security-api-key-hygiene-2 | single-article | answer | partial | **no** | 0% | 0% | 0% | 0/2 | 8.4 s |
| gq-security-audit-events-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 6.0 s |
| gq-security-audit-events-2 | single-article | answer | answer | yes | 0% | 0% | 0% | 0/2 | 4.5 s |
| gq-security-compliance-reports-1 | single-article | answer | partial | **no** | 0% | 0% | 0% | 1/2 | 6.0 s |
| gq-security-compliance-reports-2 | single-article | answer | answer | yes | 100% | 100% | 100% | 1/1 | 4.0 s |
| gq-security-credential-storage-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/2 | 3.7 s |
| gq-security-credential-storage-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.9 s |
| gq-security-data-deletion-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 0/2 | 14.7 s |
| gq-security-data-deletion-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-security-data-residency-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.5 s |
| gq-security-data-residency-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.0 s |
| gq-security-encryption-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.5 s |
| gq-security-encryption-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 7.5 s |
| gq-security-gdpr-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 3/3 | 4.6 s |
| gq-security-gdpr-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 3.5 s |
| gq-security-incident-notification-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-security-incident-notification-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.6 s |
| gq-security-password-policy-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 3/3 | 4.3 s |
| gq-security-password-policy-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.8 s |
| gq-security-session-management-1 | single-article | answer | answer | yes | 40.0% | 100% | 100% | 3/3 | 3.0 s |
| gq-security-session-management-2 | single-article | answer | answer | yes | 12.5% | 100% | 100% | 2/2 | 5.9 s |
| gq-security-vulnerability-disclosure-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.1 s |
| gq-security-vulnerability-disclosure-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 4.9 s |
| gq-tier-active-connector-limits-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/2 | 6.5 s |
| gq-tier-active-connector-limits-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.7 s |
| gq-tier-approval-steps-1 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 6.7 s |
| gq-tier-approval-steps-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.1 s |
| gq-tier-audit-log-streaming-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 3/3 | 6.7 s |
| gq-tier-audit-log-streaming-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/3 | 6.7 s |
| gq-tier-concurrent-runs-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 7.3 s |
| gq-tier-concurrent-runs-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 2.9 s |
| gq-tier-customer-managed-keys-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 3.6 s |
| gq-tier-customer-managed-keys-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.2 s |
| gq-tier-environments-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/2 | 5.8 s |
| gq-tier-environments-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.1 s |
| gq-tier-private-connector-agent-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 3/3 | 3.4 s |
| gq-tier-private-connector-agent-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 3/3 | 6.4 s |
| gq-tier-sandbox-workspace-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.7 s |
| gq-tier-sandbox-workspace-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.8 s |
| gq-tier-schedule-intervals-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-tier-schedule-intervals-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.9 s |
| gq-tier-seat-limits-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 1/2 | 4.2 s |
| gq-tier-seat-limits-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 5.9 s |
| gq-tier-secrets-vault-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-tier-secrets-vault-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.6 s |
| gq-tier-usage-dashboard-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 3/3 | 5.4 s |
| gq-tier-usage-dashboard-2 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 1/2 | 4.1 s |
| gq-tier-version-history-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.0 s |
| gq-tier-version-history-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 3.9 s |
| gq-tier-workflow-run-quotas-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 3.7 s |
| gq-tier-workflow-run-quotas-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.9 s |
| gq-tier-workflow-templates-1 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.1 s |
| gq-tier-workflow-templates-2 | single-article | answer | answer | yes | 66.7% | 100% | 100% | 2/2 | 3.9 s |
| gq-troubleshooting-api-errors-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 3/3 | 6.2 s |
| gq-troubleshooting-api-errors-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 7.0 s |
| gq-troubleshooting-approvals-1 | single-article | answer | answer | yes | 0% | 0% | 0% | 2/2 | 5.7 s |
| gq-troubleshooting-approvals-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-troubleshooting-connection-errors-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 3.2 s |
| gq-troubleshooting-connection-errors-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 2/2 | 2.7 s |
| gq-troubleshooting-data-mapping-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-troubleshooting-data-mapping-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 3.9 s |
| gq-troubleshooting-database-connections-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.4 s |
| gq-troubleshooting-database-connections-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/3 | 4.8 s |
| gq-troubleshooting-failed-runs-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 3/3 | 6.1 s |
| gq-troubleshooting-failed-runs-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.8 s |
| gq-troubleshooting-file-transfers-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 3/3 | 5.0 s |
| gq-troubleshooting-file-transfers-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/1 | 3.3 s |
| gq-troubleshooting-inbound-triggers-1 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 5.6 s |
| gq-troubleshooting-inbound-triggers-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 3.6 s |
| gq-troubleshooting-notifications-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 1/1 | 4.9 s |
| gq-troubleshooting-notifications-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.2 s |
| gq-troubleshooting-password-sign-in-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/2 | 5.7 s |
| gq-troubleshooting-password-sign-in-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 7.2 s |
| gq-troubleshooting-private-agent-1 | single-article | answer | answer | yes | 33.3% | 50.0% | 100% | 2/2 | 3.2 s |
| gq-troubleshooting-private-agent-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 3/3 | 4.9 s |
| gq-troubleshooting-promotion-1 | single-article | answer | answer | yes | 28.6% | 100% | 100% | 2/2 | 5.2 s |
| gq-troubleshooting-promotion-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 6.0 s |
| gq-troubleshooting-run-quota-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 3/3 | 3.5 s |
| gq-troubleshooting-run-quota-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.7 s |
| gq-troubleshooting-schedules-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.8 s |
| gq-troubleshooting-schedules-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.5 s |
| gq-troubleshooting-third-party-throttling-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/2 | 6.6 s |
| gq-troubleshooting-third-party-throttling-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 7.5 s |
| gq-troubleshooting-timeouts-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 3.8 s |
| gq-troubleshooting-timeouts-2 | single-article | answer | answer | yes | 14.3% | 100% | 100% | 2/2 | 5.7 s |
| gq-troubleshooting-webhook-deliveries-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 6.4 s |
| gq-troubleshooting-webhook-deliveries-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 5.0 s |
| gq-v2-admin-api-keys-1 | single-article | answer | answer | yes | 66.7% | 100% | 100% | 2/2 | 4.8 s |
| gq-v2-admin-api-keys-2 | single-article | answer | answer | yes | 50.0% | 100% | 100% | 1/2 | 5.5 s |
| gq-v2-admin-managing-users-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 2/2 | 7.1 s |
| gq-v2-admin-managing-users-2 | single-article | answer | answer | yes | 100% | 100% | 100% | 1/1 | 2.7 s |
| gq-v2-api-runs-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.0 s |
| gq-v2-api-runs-2 | single-article | answer | answer | yes | 16.7% | 100% | 100% | 2/2 | 3.9 s |
| gq-v2-api-users-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.5 s |
| gq-v2-api-users-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.2 s |
| gq-v2-api-workflows-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 6.2 s |
| gq-v2-api-workflows-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 4.0 s |
| gq-v2-connector-salesforce-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 4.9 s |
| gq-v2-connector-salesforce-2 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 4.9 s |
| gq-v2-connector-slack-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 6.9 s |
| gq-v2-connector-slack-2 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 2/2 | 5.4 s |
| gq-v2-faq-1 | single-article | answer | answer | yes | 33.3% | 100% | 100% | 1/1 | 2.8 s |
| gq-v2-faq-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 3/3 | 7.0 s |
| gq-v2-security-sessions-1 | single-article | answer | answer | yes | 25.0% | 100% | 100% | 2/2 | 5.5 s |
| gq-v2-security-sessions-2 | single-article | answer | answer | yes | 0% | 0% | 0% | 1/2 | 7.3 s |
| gq-v2-troubleshooting-workflow-runs-1 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/1 | 5.1 s |
| gq-v2-troubleshooting-workflow-runs-2 | single-article | answer | answer | yes | 20.0% | 100% | 100% | 1/2 | 5.4 s |

## How it is scored

- **Outcome**: an unanswerable question expects a Refusal, a `partial` one an Answer stating the gap phrase (`GAP_PHRASE`, anywhere, any case, either apostrophe), any other an Answer without it. An Uncited Answer counts as an Answer. A failed Turn (`rewrite_failed`, `llm_unavailable`, ...) is an `error`. A gap Answer to an unanswerable question is a soft refusal: it says what it couldn't find, but answers neighbouring facts instead of refusing.
- **Blame** for a wrong outcome: `retrieval` when it is a Refusal or a gap and an expected Section wasn't retrieved, so the model never saw it; `model` otherwise; `error` for a failed Turn.
- **Citation precision and recall** are at Section level, over distinct Sections; citing any alternative of an expected source counts for it. Precision averages over the Answers that cite something; recall over the answerable questions, where a Refusal or an Uncited Answer scores 0. Precision is against the Golden Question's expected Sections only, so a correctly cited extra fact (a v2 caveat, a related error code) lowers it: read it as focus, not as wrong Citations.
- **Retrieval recall**: the share of expected sources with any option among the retrieved Passages.
- **must_mention**: whole-word, case-insensitive term groups (any term in a group counts), over every group of the answerable questions. **Standalone** checks a Follow-up's `standalone_must_mention` against its rewrite.
- **Latency** is the whole Turn, rewrite included; **TTFT** is to the first streamed token.
- **Cost** is at list price from the providers' reported token usage. A model Refusal (`not_in_context`) stops its stream at the sentinel, before the provider reports usage, so its generation call isn't charged: each one is under-counted by its prompt (about 3K input tokens).
