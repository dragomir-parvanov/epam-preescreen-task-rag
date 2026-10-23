---
id: nimbus-api-webhooks
title: API Rate Limits and Webhooks
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-30
owner: Platform API Team
---

The OmniCorp Nimbus REST API lets a client's own systems start workflows, read run results and manage users, and webhooks let Nimbus notify those systems when something happens. This reference covers the limits the API enforces, the events Nimbus sends, how to verify that a webhook really came from Nimbus, and how failed deliveries are retried.

API access and webhooks are available on the Business and Enterprise tiers; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md). Starter workspaces can't create API keys or register webhook endpoints.

## Authentication

Every API request is authenticated with an API key that a Nimbus Admin creates under **Settings > Developers > API keys**. A key belongs to the workspace, not to a person, so it keeps working when the Admin who created it leaves. Send it as a bearer token:

```http
GET /workflows?status=active HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Accept: application/json
```

Keys can be revoked at any time on the same page; a revoked key is rejected with HTTP 401 from the next request. Rotate a key by creating the new one, switching the client's systems over, and then revoking the old one.

## Rate limits

Rate limits apply per workspace, across all of its API keys, and depend on the Plan Tier:

| Plan Tier | Sustained limit | Burst allowance |
|---|---|---|
| Starter | No API access | No API access |
| Business | 600 req/min | 1,200 req/min for 10 s |
| Enterprise | 3,000 req/min | 6,000 req/min for 10 s |

The burst allowance lets a workspace go to ×2 their sustained limit for 10 s, to absorb short spikes such as a nightly batch starting. After a burst, traffic has to drop back under the sustained limit before another burst is allowed.

Every response carries the current limit and what is left of it in the `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers. When a workspace goes over its limit, Nimbus answers with `429 Too Many Requests` and a `Retry-After` header that gives the number of seconds to wait:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 12
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 0

{"error": {"code": "rate_limited", "message": "Rate limit exceeded. Retry after 12 seconds."}}
```

Clients should wait for at least the `Retry-After` value before retrying, rather than retrying in a tight loop. Requests rejected with 429 don't count towards the limit.

## Webhook events

A webhook endpoint is an HTTPS URL on the client's side that Nimbus calls with a `POST` request when a subscribed event happens. An Admin registers endpoints under **Settings > Developers > Webhooks**, picks the events each one receives, and gets a signing secret for each endpoint.

| Event | Sent when |
|---|---|
| `workflow.run.completed` | A workflow run finishes successfully. |
| `workflow.run.failed` | A workflow run fails after its own retries. |
| `user.provisioned` | A user is created by SCIM or just-in-time provisioning. |
| `user.suspended` | A user is suspended, by an Admin or by SCIM deprovisioning. |
| `connector.disconnected` | A connector loses its authorization and needs to be reconnected. |

The endpoint must answer with a 2xx status within 15 seconds. Any other status, or no answer in time, counts as a failed delivery. Each delivery carries a unique id in the `X-Nimbus-Delivery` header; a retried delivery keeps the same id, so the client can ignore duplicates.

## Example payload

Every event has the same envelope. The `data` object depends on the event type.

```json
{
  "id": "evt_01J9ZK4M2Q8R6T",
  "event": "workflow.run.completed",
  "created_at": "2026-07-14T09:21:37Z",
  "workspace_id": "ws_4821",
  "data": {
    "workflow_id": "wf_7730",
    "workflow_name": "Sync closed deals to finance",
    "run_id": "run_55120931",
    "status": "succeeded",
    "duration_ms": 8412
  }
}
```

## Verifying signatures

Nimbus signs every delivery so that the client can check it came from Nimbus and wasn't changed on the way. The signature is an HMAC-SHA256 of the raw request body, keyed with the endpoint's signing secret, and it is sent in the `X-Nimbus-Signature-256` header as `sha256=` followed by the hex digest.

To verify a delivery:

1. Read the raw request body as bytes, before any JSON parsing.
2. Compute the HMAC-SHA256 of the body with the endpoint's signing secret.
3. Prefix the hex digest with `sha256=` and compare it with the `X-Nimbus-Signature-256` header using a constant-time comparison.
4. Reject the request with HTTP 401 if they don't match.

```python
import hashlib
import hmac


def is_from_nimbus(body: bytes, signature_header: str, signing_secret: str) -> bool:
    digest = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature_header)
```

A signing secret can be rolled under **Settings > Developers > Webhooks**. The new secret is used from the next delivery onwards, so the client should be ready to switch their endpoint over at the same moment.

## Retries and auto-disable

A failed delivery is retried up to 8 times with exponential backoff over 24 h. The delays between attempts grow as follows:

| Retry | Delay after the previous attempt | Time since the first attempt |
|---|---|---|
| 1 | 1 minute | 1 minute |
| 2 | 5 minutes | 6 minutes |
| 3 | 15 minutes | 21 minutes |
| 4 | 30 minutes | 51 minutes |
| 5 | 1 hour | about 2 hours |
| 6 | 3 hours | about 5 hours |
| 7 | 7 hours | about 12 hours |
| 8 | 12 hours | about 24 hours |

If the last retry fails too, that delivery is dropped. It stays visible, with every attempt's response status, in the endpoint's delivery log.

An endpoint that keeps failing is disabled automatically after 3 days of failed deliveries, meaning no successful delivery to it for 3 days in a row. Nimbus emails the workspace's Admins when that happens. While an endpoint is disabled, events for it are not queued. To turn it back on, an Admin fixes the endpoint, clicks **Send test event** and, once that succeeds, clicks **Enable**.
