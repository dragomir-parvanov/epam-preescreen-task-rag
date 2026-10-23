---
id: nimbus-troubleshooting-api-errors
title: Troubleshooting API Errors
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-08
owner: Support Engineering
---

The Nimbus REST API at `https://api.nimbus.omnicorp.example` reports every error with an HTTP status and a JSON body of the form `{"error": {"code": "...", "message": "..."}}`. The `code` is one of seven fixed values, and together with the status it is usually enough to tell whether the client's request, their API key, their Plan Tier or Nimbus itself is at fault.

This reference helps a CSM read an error a client pastes from their integration logs and point them to the fix. The full error format and the `Idempotency-Key` header are described in [API Error Format and Idempotency](nimbus-api-error-format.md).

## Symptoms

Clients rarely report "a 409". They report what their integration did:

- a nightly sync script that ran for months suddenly stops, with every call answered 401;
- an integration works in the client's test workspace but every call fails in another workspace;
- after a downgrade takes effect, all API calls from their middleware fail;
- a job that creates runs or users fails intermittently with 409 when their HTTP library retries;
- a bulk job slows down and logs a run of 429 responses;
- an occasional 500 that disappears when the call is repeated.

## Common causes

**400 `invalid_request`.** The request itself is wrong: the body isn't valid JSON, a required field is missing, a field has the wrong type, `limit` is above 100, a `cursor` was edited or reused from a different list, or a timestamp isn't ISO 8601.

**401 `unauthorized`.** The key isn't accepted. Either the `Authorization` header is missing or lacks the `Bearer ` prefix, or the key was revoked (revoked keys get 401 from the very next request), or it passed the optional expiry date set when it was created, or it belongs to a different workspace.

**403 `forbidden`.** The key is valid but the workspace can't use the API. Starter workspaces have no API access ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)), so a Business workspace that downgrades to Starter keeps its keys, but every call is answered 403 once the downgrade takes effect at the end of the billing period. Starting a run also gets 403, with a message starting `WF-300`, when the workspace has used its monthly workflow runs. Keys have no scopes and always act with Admin permissions, so a 403 is never about what the key itself is allowed to do.

**404 `not_found`.** The id doesn't exist in this workspace: it was deleted, it belongs to another workspace, or it has the wrong prefix (a `run_` id passed to `/workflows/{id}`). A path with a version segment, such as `/v3/workflows`, also returns 404, because the API has no version segment in its paths.

**409 `conflict`.** Either the resource's state doesn't allow the action, for example cancelling a run that has already finished, or the request reused an `Idempotency-Key` with a different body. Nimbus remembers a key for 24 hours; a retry with the same key and the same body returns the original response, but the same key with a changed body is rejected with 409. HTTP libraries that generate one key per job rather than one per request cause this.

**429 `rate_limited`.** The workspace sent more calls than its rate limit allows. The response carries a `Retry-After` header with the number of seconds to wait.

**500 `internal_error`.** Something failed inside Nimbus. These are rare and normally transient.

## Diagnosing the problem

1. Get the full response, not just the status. Ask the client to repeat one failing call with `curl -i` so the headers are visible:

```bash
curl -i https://api.nimbus.omnicorp.example/workspace/entitlements \
  -H "Authorization: Bearer <api-key>"
```

A 403 for a Starter workspace looks like this:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{"error": {"code": "forbidden", "message": "API access is not included in this workspace's Plan Tier."}}
```

2. For 401, open **Settings > Developers > API keys**. Each key shows its status (*Active*, *Expired* or *Revoked*), its expiry date and when it was last used. A key that shows *Revoked* has a matching `api_key.revoked` event in **Settings > Audit log** that names the Admin who revoked it.
3. For 403, check the Plan Tier under **Settings > Plan**, including any downgrade scheduled for the end of the billing period.
4. For 409, find the `Idempotency-Key` the client sent and check whether an earlier request with that key had a different body within the previous 24 hours.
5. For 429, record the `Retry-After`, `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers from the response.

## Error reference

| Status | `code` | Meaning | First thing to check |
|---|---|---|---|
| 400 | `invalid_request` | The request is malformed or a value is out of range. | The `message`, which names the field. |
| 401 | `unauthorized` | The key is missing, revoked, expired or from another workspace. | **Settings > Developers > API keys** |
| 403 | `forbidden` | The workspace's Plan Tier has no API access (Starter), or a run start hit the monthly run quota (`WF-300`). Keys have no scopes, so the key's permissions are never the cause. | **Settings > Plan**, **Settings > Usage** |
| 404 | `not_found` | The resource doesn't exist in this workspace, or the path is wrong. | The id prefix and the path. |
| 409 | `conflict` | The action conflicts with the resource's state, or an `Idempotency-Key` was reused with a different body. | The idempotency key. |
| 429 | `rate_limited` | The workspace is over its rate limit. | The `Retry-After` header. |
| 500 | `internal_error` | An internal Nimbus error. | Retry; escalate if it persists. |

## Fixes

- **401:** create a new key under **Settings > Developers > API keys**, switch the client's systems to it, and revoke the old one; set an expiry date and a reminder to rotate before it. See [Creating and Rotating API Keys](nimbus-admin-api-keys.md).
- **403:** API access needs the Business or Enterprise tier. An upgrade under **Settings > Plan** takes effect immediately, and existing keys start working again without being recreated.
- **409:** generate a new `Idempotency-Key` for each logical operation and reuse it only when retrying exactly the same request.
- **429:** wait at least the `Retry-After` value before the next call, and spread scheduled jobs so they don't all start on the hour. The limits themselves are in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).
- **500:** retry with backoff, sending the same `Idempotency-Key` so a POST isn't applied twice.

A retry loop that follows these rules:

```python
import time
import uuid

import requests

def post_with_retry(url: str, body: dict, api_key: str, attempts: int = 5) -> requests.Response:
    headers = {"Authorization": f"Bearer {api_key}", "Idempotency-Key": str(uuid.uuid4())}
    for attempt in range(attempts):
        response = requests.post(url, json=body, headers=headers, timeout=30)
        if response.status_code == 429:
            time.sleep(int(response.headers.get("Retry-After", "1")))
        elif response.status_code >= 500:
            time.sleep(2 ** attempt)
        else:
            return response
    return response
```

## Escalating to support

Escalate repeated 500 responses, and any error whose `message` contradicts what the console shows. Collect:

- the HTTP method and path, with ids but without the API key;
- the timestamp of the request in UTC and the full response, headers included;
- the workspace id (`ws_...`) and the key's id (`key_...`), never the key itself;
- the `Idempotency-Key` for POST requests;
- whether the error reproduces with `curl`.
