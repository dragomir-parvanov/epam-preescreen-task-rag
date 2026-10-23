---
id: nimbus-faq-api-and-integrations
title: API and Integrations FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-25
owner: Customer Success Enablement
---

Clients who integrate their own systems with Nimbus ask a predictable set of questions: who can use the API, how keys work, how to page through lists, how to make retries safe, and whether to start workflows through an inbound webhook trigger or through the Runs API. This FAQ collects the answers CSMs need for those conversations.

Which Plan Tiers include API access, and the request limits that apply, are covered in [Plan Tiers and Entitlements](nimbus-plan-tiers.md) and [API Rate Limits and Webhooks](nimbus-api-webhooks.md). Quote them from there rather than from memory.

## General questions

**Where is the API, and is it versioned?**

The base URL is https://api.nimbus.omnicorp.example, with no version segment in the path: `GET /workflows`, not a path with a version prefix. Request and response bodies are JSON, and every timestamp is ISO 8601 in UTC, for example `2026-05-18T09:30:00Z`.

**How does a request authenticate?**

With an API key created by an Admin, sent in the `Authorization` header as `Bearer <api-key>`. A key acts with Admin permissions in its workspace, and keys have no scopes, so treat every key like an Admin password and give each integration its own key so one can be revoked without breaking the others.

**How are objects identified?**

Every id carries a prefix that tells you what it is: `ws_` (workspace), `wf_` (workflow), `run_` (run), `usr_` (user), `inv_` (invitation), `con_` (connection), `key_` (API key), `whk_` (webhook endpoint), `dlv_` (delivery), `evt_` (event), `fld_` (folder) and `apr_` (approval). A `404 not_found` on a valid-looking id usually means the id belongs to a different workspace than the key.

**Should a client start workflows with an inbound webhook trigger or the Runs API?**

Both start a run; they suit different callers.

| | Inbound webhook trigger | Runs API |
|---|---|---|
| How it is called | `POST https://hooks.nimbus.omnicorp.example/t/<trigger-token>` | `POST /workflows/{id}/runs` on the API base URL |
| Authentication | The trigger token in the URL; no API key | `Authorization: Bearer <api-key>` |
| Payload | JSON up to 1 MB, available as `{{trigger.body.<field>}}` | JSON input for the run |
| Response | `202 Accepted` with the run id | The created run object |
| Best for | Third-party apps that can only send a webhook | The client's own services that already hold an API key |

The inbound trigger URL is a secret in itself: anyone who has it can start the workflow. If it leaks, regenerate the trigger token in the builder and update the sender.

## Setup questions

**How do I page through a long list?**

List endpoints are cursor-based. Pass `limit` (default 25, maximum 100) and, for every page after the first, the `cursor` from the previous response. Stop when `next_cursor` is null.

```bash
curl -s "https://api.nimbus.omnicorp.example/runs?limit=100" \
  -H "Authorization: Bearer <api-key>"

# {"data": [{"id": "run_9QwE4m", "status": "succeeded", ...}], "next_cursor": "c3RhcnQ9MTAw"}

curl -s "https://api.nimbus.omnicorp.example/runs?limit=100&cursor=c3RhcnQ9MTAw" \
  -H "Authorization: Bearer <api-key>"
```

**How do I make a POST safe to retry?**

Send an `Idempotency-Key` header with a value unique to the operation, such as the client's own order number or a UUID. Nimbus remembers a key for 24 hours: a repeat of the same request with the same key returns the original response instead of, for example, starting a second run.

### How do I create an API key?

API keys are created by an Admin in the console:

1. Go to Settings > Developers > API keys and click Create API key.
2. Enter a name that identifies the integration, for example "ERP nightly sync".
3. Optionally set an expiry date. Without one, the key stays valid until it is revoked.
4. Click Create and copy the key immediately. It is shown once and can't be displayed again.
5. Store it in the calling system's secret store, never in source code.

To retire a key, click Revoke next to it. Requests with a revoked key get `401 unauthorized` from the next request onwards.

## Limits and edge cases

**What happens if a key is lost?**

It can't be recovered. Create a new key, update the integration, then revoke the old one.

**Can a key be limited to read-only access?**

No. Keys have no scopes and always act with Admin permissions. Clients who need a read-only view should give people the Viewer role in the console instead.

**What happens to a payload bigger than 1 MB on an inbound trigger?**

It is rejected and no run is started. Send a reference (a file path or record id) instead and let a connector step fetch the data.

**What does the client see when they send requests too fast?**

A `429` response with the `rate_limited` error code. The limits and the headers that report them are documented in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Troubleshooting questions

**Every call returns 401.**

The key is wrong, expired or revoked, or the header is malformed. The header must read `Authorization: Bearer <api-key>` with a single space and no quotes. Check the key's status under Settings > Developers > API keys.

**A call returns 409 conflict.**

Most often the same `Idempotency-Key` was reused within 24 hours for a request with a different body. Use a fresh key for each distinct operation.

**A call returns 400 invalid_request.**

The body or a query parameter is invalid, for example `limit=500`. The `message` in the error body names the field:

```json
{"error": {"code": "invalid_request", "message": "limit must be between 1 and 100"}}
```

**The inbound webhook trigger returns 202 but no run appears.**

Check that the workflow is active and that the sender is using the current trigger token. See [Troubleshooting Inbound Webhook Triggers](nimbus-troubleshooting-inbound-triggers.md).

## Where to find more

- [Creating and Rotating API Keys](nimbus-admin-api-keys.md) and [API Key Security Practices](nimbus-security-api-key-hygiene.md).
- [API Error Format and Idempotency](nimbus-api-error-format.md) for every error code.
- [Runs API](nimbus-api-runs.md) and [Inbound Webhook Triggers](nimbus-api-inbound-webhook-triggers.md).
- [Troubleshooting API Errors](nimbus-troubleshooting-api-errors.md).
