---
id: nimbus-api-connections
title: Connections API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-15
owner: Platform API Team
---

A connector is an integration Nimbus offers, such as Salesforce or SFTP; a connection is one client account authorised on it, such as the client's production Salesforce org. The Connections API lists and reads a workspace's connections, tests whether one still works and deletes one that is no longer needed. It also exposes the connector catalogue through `GET /connectors`.

Connections are created and reconnected in the console under **Connections**, not through the API, because most of them need an OAuth consent screen or a credential typed by a person. The API never returns credentials: they are encrypted when saved and never shown again. Requests use an API key in `Authorization: Bearer <api-key>`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/connections` | List the workspace's connections. |
| `GET` | `/connections/{id}` | Read one connection, including its status. |
| `POST` | `/connections/{id}/test` | Make a harmless read call with the stored credentials and report the result. |
| `DELETE` | `/connections/{id}` | Delete a connection that no active workflow uses. |
| `GET` | `/connectors` | List the connector catalogue: auth methods, trigger mode and release. |

### Testing a connection

`POST /connections/{id}/test` takes no body. Nimbus calls a read-only operation on the third-party app, for example the identity endpoint for an OAuth connector or `SELECT 1` for a database, and answers `200 OK` with `"result": "ok"` or `"result": "failed"` and an `error` in the same CONN- codes that steps use. A test never changes data in the other system.

A failed test with `CONN-401` means the authorisation has expired or been revoked. The connection then shows `needs_attention`, the `connector.disconnected` webhook event is sent, and a Builder or Admin has to click **Reconnect** under **Connections**. A `CONN-503` result on a connection that goes through a private connector agent usually means the agent itself is offline; see [Private Connector Agent](nimbus-tier-private-connector-agent.md).

### Deleting a connection

`DELETE /connections/{id}` is refused while any active workflow has a step that uses the connection. Deactivate those workflows, or point their steps at another connection, and try again. Deleting removes the stored credentials from Nimbus but doesn't revoke the grant inside the third-party app; for OAuth connectors, the client should also remove the Nimbus app from the account there.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Connection id, prefixed `con_`. |
| `connector` | string | Connector slug, e.g. `salesforce`, `servicenow`, `sftp`. |
| `name` | string | The name given when the connection was made, e.g. "Salesforce production". |
| `status` | string | `connected` or `needs_attention`. |
| `status_reason` | object or null | While `needs_attention`, the CONN- `code` and `message` that caused it. |
| `auth_method` | string | How it authenticates: `oauth2`, `api_token`, `basic`, `key_pair`, `access_key`, `iam_role`, `ssh_key`, and so on. |
| `account_label` | string | Which account it uses, shown without secrets: an org name, a username or a host. |
| `private_agent` | string or null | Name of the private connector agent the connection goes through, if any. |
| `used_by_workflows` | integer | Workflows with at least one step on this connection. |
| `used_by_active_workflows` | integer | Of those, how many are active. Above zero, the connector counts as active. |
| `created_by` | string | The `usr_` id of the person who made it. |
| `created_at`, `last_used_at`, `last_tested_at` | string or null | Lifecycle timestamps. |

`last_used_at` moves whenever a step or a trigger uses the connection, so a connection with an old `last_used_at` and `used_by_workflows` at 0 is a safe candidate for deletion. A connector counts towards the workspace's active connectors when at least one of its connections is used by an active workflow; see [Active Connector Limits](nimbus-tier-active-connector-limits.md).

## Example request and response

Testing a ServiceNow connection that uses an integration user:

```http
POST /connections/con_7215/test HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "connection_id": "con_7215",
  "result": "failed",
  "error": {
    "code": "CONN-403",
    "message": "User nimbus.integration lacks the itil role required to read the incident table"
  },
  "tested_at": "2026-06-11T13:20:08Z"
}
```

The status stays `connected`: a permission problem is fixed in ServiceNow by giving the integration user the missing role, not by reconnecting. A `GET /connectors` entry for the same connector looks like this:

```json
{
  "slug": "servicenow",
  "name": "ServiceNow",
  "auth_methods": ["oauth2", "basic"],
  "trigger_mode": "polling",
  "available_since": "3.7.0"
}
```

`trigger_mode` is `push` for connectors whose app sends events within seconds, `polling` for connectors Nimbus checks every 5 minutes, and `none` for action-only connectors such as Snowflake and HTTP Request. The catalogue is the same for every workspace; `available_since` tells a CSM which release added a connector, which helps when a client asks why a connector they read about isn't in an older integration guide.

## Filtering and pagination

`GET /connections` filters:

- `connector`: one slug, e.g. `connector=hubspot`.
- `status`: `connected` or `needs_attention`.
- `created_by`: a `usr_` id.
- `in_use`: `true` for connections used by at least one active workflow, `false` for the rest.

`GET /connectors` filters by `trigger_mode` and `auth_method`. Both lists use `limit` (default 25, maximum 100) and `cursor`. A daily health check that reports broken connections:

1. Call `GET /connections?status=needs_attention&limit=100`.
2. For each connection in `data`, note `connector`, `name` and `status_reason.code`.
3. If `next_cursor` isn't null, call again with `cursor=<next_cursor>`.
4. When `next_cursor` is null, send the list to the people who can reconnect them.

Subscribing to the `connector.disconnected` webhook event gives the same signal without polling; see [Webhook Endpoints API](nimbus-api-webhook-endpoints.md).

## Errors

| HTTP status | Code | When |
|---|---|---|
| 400 | `invalid_request` | An unknown `status`, `trigger_mode` or `auth_method` filter value. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 404 | `not_found` | No connection with that id in the workspace. |
| 409 | `conflict` | `DELETE` while an active workflow still uses the connection. |
| 429 | `rate_limited` | The workspace's API limit was reached; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | A Nimbus fault while running the test; try again. |

A test that reaches the third-party app and gets an error back still returns `200 OK`; the problem is in `result` and `error`, not in the HTTP status.
