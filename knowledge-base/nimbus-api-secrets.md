---
id: nimbus-api-secrets
title: Secrets API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-01-19
owner: Platform API Team
---

The Secrets API manages the workspace secrets vault, the same store an Admin sees under **Settings > Secrets**. A secret is a named value, such as a database password, a partner's API token or an SFTP passphrase, that workflow steps read at run time with the expression `{{secrets.NAME}}`. The API is write-only for values: it can create, replace and delete a secret, and it can list secret names, but no endpoint ever returns a value once it has been stored.

Requests are authenticated with an API key sent as `Authorization: Bearer <api-key>`, and they act with Admin permissions in the key's workspace. For the console workflow and guidance on what belongs in the vault, see [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/secrets` | List the workspace's secrets: names and metadata only, never values. |
| `PUT` | `/secrets/{name}` | Create the secret `{name}`, or replace its value if it already exists. |
| `DELETE` | `/secrets/{name}` | Delete the secret `{name}` permanently. |

There is no `GET /secrets/{name}`. To check whether a single secret exists, list secrets with the `prefix` filter described below.

### Creating or replacing a secret

`PUT /secrets/{name}` is an upsert. It answers `201 Created` when the name is new and `200 OK` when it replaces an existing value. Because sending the same `PUT` twice leaves the vault in the same state, the call is safe to repeat after a timeout and doesn't need an `Idempotency-Key` header. A replaced value applies to every step that starts after the call returns; a step that is already running keeps the value it resolved when it started. Replacing a value doesn't publish a new workflow version, because workflows store only the reference, not the value.

The request body takes a required `value` (a non-empty UTF-8 string of at most 16 KB) and an optional `description` of up to 200 characters. Omitting `description` on a replace keeps the existing one.

### Naming rules

A secret name is between 1 and 64 characters long, uses only uppercase letters `A-Z`, digits and underscores, and starts with a letter. `SALESFORCE_CLIENT_SECRET` and `SFTP_KEY_2` are valid; `sftp-key`, `2FA_SEED` and `My Secret` are not. The prefix `NIMBUS_` is reserved for platform use and rejected. Because names are uppercase only, there is no case-sensitivity question: the name in the path is exactly the name a builder types after `secrets.` in an expression.

## Object fields

| Field | Type | Description |
|---|---|---|
| `name` | string | The secret's name, unique in the workspace. Also its identifier in the path. |
| `description` | string or null | Free text shown next to the name under Settings > Secrets. |
| `value` | string | Write-only. Accepted on `PUT`, never present in any response. |
| `created_at` | string | When the secret was first created (ISO 8601, UTC). |
| `updated_at` | string | When the value or description last changed. |
| `updated_by` | string | Who made the last change: a user id (`usr_`) for a console edit, an API key id (`key_`) for an API call. |
| `last_used_at` | string or null | When a run step last resolved the secret; `null` if no run has used it yet. Useful for finding secrets that are safe to delete. |

## Example request and response

Store a new token for a partner API that an HTTP Request step will call:

```http
PUT /secrets/ACME_PARTNER_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "value": "pk_live_7Hq2...rD9",
  "description": "Acme partner API, rotated quarterly by the integrations team"
}
```

```json
{
  "name": "ACME_PARTNER_TOKEN",
  "description": "Acme partner API, rotated quarterly by the integrations team",
  "created_at": "2026-01-12T09:41:07Z",
  "updated_at": "2026-01-12T09:41:07Z",
  "updated_by": "key_3mT8bQ1x",
  "last_used_at": null
}
```

The response has no `value` field. A builder then references the secret in a step's header mapping as `Bearer {{secrets.ACME_PARTNER_TOKEN}}`. Create, replace and delete calls are all recorded in the audit log with the secret's name, never its value.

## Filtering and pagination

`GET /secrets` is cursor-paginated like every list in the API. It accepts:

- `limit`: page size, default 25, maximum 100.
- `cursor`: the `next_cursor` value from the previous page.
- `prefix`: return only secrets whose name starts with this string, for example `prefix=SALESFORCE_`.
- `unused`: `true` returns only secrets whose `last_used_at` is `null`.

Results are sorted by `name`, ascending. To read every secret name in a large workspace:

1. Call `GET /secrets?limit=100`.
2. Process the entries in `data`.
3. If `next_cursor` is not `null`, call `GET /secrets?limit=100&cursor=<next_cursor>` and go back to step 2.
4. Stop when `next_cursor` is `null`; that was the last page.

A cursor is tied to the filters it was issued with, so keep `prefix` and `unused` the same on every page.

## Errors

Errors use the common envelope `{"error": {"code": "...", "message": "..."}}`; see [API Error Format and Idempotency](nimbus-api-error-format.md).

| HTTP status | Code | When the Secrets API returns it |
|---|---|---|
| 400 | `invalid_request` | The name breaks the naming rules, uses the `NIMBUS_` prefix, or `value` is missing, empty or larger than 16 KB. |
| 401 | `unauthorized` | The API key is missing, malformed, expired or revoked. |
| 404 | `not_found` | `DELETE` named a secret that doesn't exist. |
| 409 | `conflict` | `PUT` would create a new secret, but the workspace has reached its secrets limit. |
| 429 | `rate_limited` | The workspace is over its API rate limit; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | An internal Nimbus error. Repeat the `PUT` or `DELETE`; both are safe to retry. |

Deleting a secret that live workflows still reference succeeds. Those workflows keep running, but any step whose expression resolves `{{secrets.NAME}}` to nothing then fails with WF-400. Check `last_used_at` and search the workflows for the name before deleting.

### Limits per tier

The number of secrets a workspace can store depends on its Plan Tier. Replacing an existing secret never counts against the limit; only creating a new name does.

| Plan Tier | Secrets in the vault |
|---|---|
| Starter | 25 |
| Business | 250 |
| Enterprise | Unlimited |

When the limit is reached, `PUT` for a new name answers `409 conflict` with the message "Secrets limit reached for this Plan Tier (250)". Delete unused secrets or upgrade the workspace; an upgrade takes effect immediately. The current count is shown under **Settings > Usage**, and [Secrets Vault Limits](nimbus-tier-secrets-vault.md) explains what happens to existing secrets after a downgrade.
