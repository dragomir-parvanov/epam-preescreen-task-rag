---
id: nimbus-api-error-format
title: API Error Format and Idempotency
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-29
owner: Platform API Team
---

Every endpoint of the Nimbus REST API reports failures the same way: an HTTP status, a JSON envelope with a machine-readable `code` and a human-readable `message`, and a request id in the response headers. This reference describes that envelope, lists every error code with its status, and explains the `Idempotency-Key` header that makes `POST` requests safe to retry.

The conventions here apply to `https://api.nimbus.omnicorp.example` and every resource under it. Per-resource Articles, such as the [Runs API](nimbus-api-runs.md), list which of these codes each endpoint returns and why. Rate-limit values and headers are covered only in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Endpoints

The behaviour on retry depends on the method, not the resource:

| Method | Examples | Retry behaviour |
|---|---|---|
| `GET` | `GET /runs`, `GET /workspace/usage` | Always safe to repeat. |
| `POST` | `POST /workflows/{id}/runs`, `POST /invitations`, `POST /api-keys` | Accepts `Idempotency-Key`; without it, a retry can create a second object. |
| `PUT` | `PUT /secrets/{name}`, `PUT /workflows/{id}/schedule` | Idempotent by design; the header is ignored. |
| `PATCH` | `PATCH /users/{id}`, `PATCH /folders/{id}` | Repeating the same body leaves the same result; the header is ignored. |
| `DELETE` | `DELETE /api-keys/{id}` | A repeat after success answers `404 not_found`, which a client can treat as done. |

### Idempotency-Key

Send `Idempotency-Key: <value>` on any `POST`. The value is a string of up to 255 characters chosen by the client; a random UUID or a stable business key such as `invoice-55871-run` both work. Nimbus remembers each key for 24 hours per workspace, together with the request body and the response it produced.

1. A first request with a new key is processed normally, and its response is stored.
2. A repeat with the same key and the same body isn't processed again. Nimbus replays the stored status and body and adds `Idempotency-Replayed: true`.
3. A repeat with the same key and a different body is rejected with `409 conflict`, because the key was already used for something else.
4. A repeat that arrives while the first request is still being processed is rejected with `409 conflict`; wait a second and retry.
5. After 24 hours the key is forgotten, and a request with it is processed as new.

Responses with status `500` aren't stored, so retrying a failed request with the same key processes it again. Keys are per workspace, so two workspaces using the same value never collide.

### Request ids

Every response, successful or not, carries an `X-Request-Id` header such as `req_01J8ZK4T6QX9`. It identifies the request in OmniCorp's logs. When a client escalates an API problem, the CSM should ask for the request id, the method and path, and the time in UTC; with those, support can find the exact request without the client sending payloads or API keys.

## Object fields

The error envelope:

| Field | Type | Description |
|---|---|---|
| `error` | object | Present on every error response, absent on success. |
| `error.code` | string | One of the codes in the Errors table. Stable; branch on this. |
| `error.message` | string | Explanation for a person, naming the field or object at fault. The wording can change between releases, so don't parse it. |

Response headers that matter for errors:

| Header | Present on | Meaning |
|---|---|---|
| `X-Request-Id` | Every response | The request's id for support. |
| `Idempotency-Replayed` | Replayed `POST` responses | `true` when the body is a stored response, not a new result. |

## Example request and response

A run started with an `Idempotency-Key`, where the client's first attempt timed out on its side:

```http
POST /workflows/wf_8kD2nR4q/runs HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: nightly-erp-sync-2026-06-25

{"input": {"business_date": "2026-06-25"}}
```

The retry gets the original response back instead of a second run:

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
X-Request-Id: req_01J8ZK7W2MD4
Idempotency-Replayed: true

{"id": "run_3Fh8nQ2d", "workflow_id": "wf_8kD2nR4q", "status": "queued"}
```

The same key sent with `{"input": {"business_date": "2026-06-26"}}` fails instead:

```json
{
  "error": {
    "code": "conflict",
    "message": "Idempotency-Key 'nightly-erp-sync-2026-06-25' was already used with a different request body."
  }
}
```

## Filtering and pagination

List endpoints validate their query parameters before doing any work, and a bad parameter returns `400 invalid_request` rather than an empty list. The usual causes are a `limit` above 100 or below 1, a `cursor` that was cut short when copied, a `cursor` reused with different filters, and a timestamp filter that isn't ISO 8601. An unknown query parameter is ignored, not rejected, so a misspelt filter returns unfiltered results; check parameter names against the resource's Article.

A paging loop that survives transient errors:

1. Request the first page with the filters and `limit=100`.
2. On `200`, process `data` and keep `next_cursor`.
3. On `429` or `500`, wait and send the same request again with the same cursor; cursors stay valid across retries.
4. On any other `4xx`, stop and log the `code`, `message` and `X-Request-Id`; retrying won't help.
5. Repeat with `cursor=<next_cursor>` until `next_cursor` is `null`.

## Errors

| HTTP status | Code | Meaning | Retry? |
|---|---|---|---|
| 400 | `invalid_request` | The body or query is malformed, a required field is missing, or a value is out of range. | No; fix the request. |
| 401 | `unauthorized` | No `Authorization: Bearer` header, or the key is unknown, expired or revoked. | No; check the key. |
| 403 | `forbidden` | The workspace's Plan Tier doesn't include the feature, such as environments or approval steps, or a run was refused because the monthly workflow runs are used up (message starting `WF-300`). | No; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md). |
| 404 | `not_found` | The object doesn't exist in this workspace, or the path is wrong. | No. |
| 409 | `conflict` | The request clashes with the current state: a duplicate name, an already decided approval, or a reused `Idempotency-Key`. | After re-reading the object. |
| 429 | `rate_limited` | The workspace is over its rate limit. | Yes, after the wait the response specifies. |
| 500 | `internal_error` | An unexpected Nimbus error. | Yes, with the same `Idempotency-Key`. |

API keys carry Admin permissions and have no scopes, so a `403` is never about the key's role; it means the feature or the monthly run quota is outside the workspace's entitlements, shown under **Settings > Plan** and **Settings > Usage**. A `401` right after an Admin revokes a key is expected; see [API Keys API](nimbus-api-api-keys.md).
