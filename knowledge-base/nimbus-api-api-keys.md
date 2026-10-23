---
id: nimbus-api-api-keys
title: API Keys API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-04
owner: Platform API Team
---

API keys are how a client's systems authenticate to the Nimbus API. This resource lists a workspace's keys, creates new ones and revokes old ones, so that a client can automate rotation instead of doing it by hand under **Settings > Developers > API keys**. The console procedure, and who in the client's organisation should hold keys, is in [Creating and Rotating API Keys](nimbus-admin-api-keys.md).

Keys have no scopes. Every key acts with Admin permissions in its workspace, including on this resource, so any key can create or revoke any other. A key belongs to the workspace rather than to the Admin who made it and keeps working if that person leaves. Whether a workspace can use the API at all depends on its Plan Tier; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api-keys` | List the workspace's keys. The secret is never included. |
| `POST` | `/api-keys` | Create a key; the response holds the secret, once. |
| `DELETE` | `/api-keys/{id}` | Revoke a key. Requests with it fail with 401 from the next one. |

### Creating a key

`POST /api-keys` takes a `name`, which should say what uses the key ("Finance ETL, production"), and an optional `expires_at`. Without `expires_at` the key doesn't expire. The `201 Created` response is the only time the full key appears, in the `secret` field; Nimbus stores only a hash of it. If the secret is lost, revoke the key and create another one.

The secret starts with `nmb_live_`, which makes it easy for secret scanners in the client's code repositories to spot. In requests it goes in the header `Authorization: Bearer <api-key>`. The key's `name` is what the audit log shows as the actor for every change the key makes, so a descriptive name pays off when an Admin later asks which system changed something.

Once `expires_at` passes, requests with the key get `401 unauthorized` with the message "API key expired", while a revoked key gets "API key revoked". That message is the quickest way to tell the two apart when a client's integration suddenly stops.

### Rotating a key

Because two keys can be valid at once, rotation needs no downtime:

1. Create the replacement with `POST /api-keys`, giving it a name that shows it is the successor, e.g. "Finance ETL, production (2026-05)".
2. Store the new `secret` in the client's secret manager and deploy it to every system that used the old key.
3. Watch the old key's `last_used_at` with `GET /api-keys`. When it stops moving, nothing is using it any more.
4. Revoke the old key with `DELETE /api-keys/{id}`.

Setting `expires_at` on every key, and rotating a few weeks before that date, turns rotation into a routine task instead of a surprise.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Key id, prefixed `key_`. This is not the secret and can be logged safely. |
| `name` | string | Label shown in the console and in audit events, up to 80 characters. |
| `last_four` | string | Last four characters of the secret, to tell keys apart. |
| `secret` | string | Only in the `POST` response. |
| `created_by` | string | The `usr_` id of the Admin, or the `key_` id of the key, that created it. |
| `created_at` | string | Creation time. |
| `expires_at` | string or null | When it stops working; null for no expiry. |
| `expired` | boolean | True once `expires_at` has passed. |
| `last_used_at` | string or null | The last request made with the key, to the minute; null if never used. |

Revoked keys are removed from the list straight away. Expired keys stay listed, with `expired: true`, until someone revokes them, so they can be told apart from keys that never existed when a client reports a 401.

## Example request and response

```http
POST /api-keys HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: rotate-finance-etl-2026-05

{
  "name": "Finance ETL, production (2026-05)",
  "expires_at": "2027-05-01T00:00:00Z"
}
```

```json
{
  "id": "key_4419",
  "name": "Finance ETL, production (2026-05)",
  "last_four": "Q7xd",
  "secret": "nmb_live_8fK2pLw0RzT6yHcN3vJmA5eUQ7xd",
  "created_by": "key_3307",
  "created_at": "2026-05-02T09:14:00Z",
  "expires_at": "2027-05-01T00:00:00Z",
  "expired": false,
  "last_used_at": null
}
```

The same key in a later `GET /api-keys` response has every field except `secret`. Revoking it is `DELETE /api-keys/key_4419`, which answers `204 No Content`.

## Filtering and pagination

`GET /api-keys` supports a few filters that help with key hygiene:

| Parameter | Effect |
|---|---|
| `expired` | `true` for expired keys only, `false` for keys that still work. |
| `last_used_before` | Keys whose `last_used_at` is earlier than this timestamp, or that were never used. |
| `q` | Partial, case-insensitive match on `name`. |
| `limit`, `cursor` | Page size (25 by default, 100 at most) and continuation. |

A clean-up job that finds keys nobody has used since the start of the year:

1. Call `GET /api-keys?expired=false&last_used_before=2026-01-01T00:00:00Z&limit=100`.
2. Collect `id`, `name` and `created_by` from each key in `data`.
3. Follow `next_cursor` with `cursor=<next_cursor>` until it is null.
4. Confirm each key with its owner before revoking it, since a quarterly job may simply not have run yet.

Most workspaces have only a handful of keys, so one page is usually enough.

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `name` is missing or too long, or `expires_at` is in the past. |
| 401 | `unauthorized` | The key in the request is missing, expired or revoked. |
| 403 | `forbidden` | The workspace's Plan Tier doesn't include API access. |
| 404 | `not_found` | No key with that id; it may already have been revoked. |
| 429 | `rate_limited` | Too many requests; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |

A key may revoke itself. The `DELETE` call still succeeds with `204`, and the next request made with that key gets `401 unauthorized`. Scripts that rotate their own key should switch to the new secret before revoking the old one, never after.
