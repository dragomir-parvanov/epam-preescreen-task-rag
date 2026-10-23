---
id: nimbus-v2-api-workflows
title: Workflows API (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-02-17
owner: Platform API Team
---

The Workflows API lets a client's systems list, create, change, activate and delete workflows in a workspace on the legacy Nimbus platform. Each workflow is a single live definition: there is no version history, no Development and Production split and no promotion, so every change made through this API takes effect on the running workflow at once.

Requests go to `https://api.nimbus.omnicorp.example` with an API key in the `Authorization: Bearer <api-key>` header. Keys are created under **Admin > API keys**; see [Managing API Keys (v2)](nimbus-v2-admin-api-keys.md). Limits, webhook signing and the platform's end of support are in the [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/workflows` | List workflows, one page at a time. |
| `POST` | `/workflows` | Create a workflow. It starts inactive. |
| `GET` | `/workflows/{id}` | Read one workflow with its trigger and steps. |
| `PATCH` | `/workflows/{id}` | Change the name, description, trigger or steps. |
| `DELETE` | `/workflows/{id}` | Delete an inactive workflow. |
| `POST` | `/workflows/{id}/activate` | Turn the workflow on; its trigger starts firing. |
| `POST` | `/workflows/{id}/deactivate` | Turn it off; runs already in progress finish. |

Runs are started and read through the [Runs API (v2)](nimbus-v2-api-runs.md), not through these endpoints.

### Creating a workflow

`POST /workflows` takes `name` (required, up to 120 characters), `description`, `trigger` and `steps`. Most clients build workflows in the console and use the API only to copy a workflow between workspaces: read it with `GET /workflows/{id}`, drop the read-only fields, and post the rest to the other workspace. Connection ids differ between workspaces, so the copied steps' `connection_id` values must be replaced before the workflow is activated.

The endpoint doesn't accept an `Idempotency-Key` header. If a create request times out, call `GET /workflows?name=<name>` before sending it again; otherwise a retry can leave two workflows with the same name.

### Updating a workflow

`PATCH /workflows/{id}` replaces each top-level field it is given and leaves the others alone. Sending `steps` replaces the whole step list, not individual steps. The change applies to the next run that starts; a run in progress finishes with the definition it started with.

There is no version history, so the previous definition can't be restored afterwards. Before any scripted change, save the output of `GET /workflows/{id}` to a file; restoring means sending that saved `trigger` and `steps` back with another `PATCH`.

## Object fields

| Field | Type | Writable | Description |
|---|---|---|---|
| `id` | string | No | Workflow id, prefixed `wf_`. |
| `name` | string | Yes | Shown in the console's workflow list. Names don't have to be unique. |
| `description` | string or null | Yes | Free text. |
| `status` | string | No | `active` or `inactive`; changed only by the activate and deactivate endpoints. |
| `trigger` | object | Yes | `type` (`schedule`, `webhook`, `connector_event` or `manual`) plus its settings, such as `cron` and `time_zone` for a schedule. |
| `steps` | array | Yes | Ordered steps, each with `key`, `type`, `connection_id` where relevant, and its configuration. |
| `owner_id` | string | Yes | The `usr_` id of the owning Builder or Admin. |
| `created_at` | string | No | ISO 8601, UTC. |
| `updated_at` | string | No | When the definition last changed. |
| `last_run_at` | string or null | No | When the most recent run started. |

The object has no `version`, `environment` or `folder_id` field.

## Example request and response

Move a nightly export from 02:00 to 03:30 workspace time:

```http
PATCH /workflows/wf_5Lr2dK8m HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "trigger": {"type": "schedule", "cron": "30 3 * * *", "time_zone": null}
}
```

```json
{
  "id": "wf_5Lr2dK8m",
  "name": "Nightly orders export to SFTP",
  "description": "Exports the previous day's orders as CSV",
  "status": "active",
  "trigger": {"type": "schedule", "cron": "30 3 * * *", "time_zone": null},
  "steps": [
    {"key": "fetch_orders", "type": "action", "connection_id": "con_4Pg7", "action": "mysql.query"},
    {"key": "write_csv", "type": "action", "connection_id": "con_9Tc1", "action": "sftp.upload_file"}
  ],
  "owner_id": "usr_2Wb6",
  "created_at": "2024-03-11T10:05:22Z",
  "updated_at": "2025-02-14T16:48:03Z",
  "last_run_at": "2025-02-14T02:00:04Z"
}
```

A `null` `time_zone` means the workspace time zone. The response always returns the complete workflow, so a client can confirm the change without a second request.

## Filtering and pagination

`GET /workflows` is page-based. It takes `page` (starting at 1) and `per_page` (default 50, maximum 100), and every list response carries `total`, the number of workflows matching the filters:

```json
{"data": [ ... ], "page": 1, "per_page": 50, "total": 137}
```

Filters can be combined: `status` (`active` or `inactive`), `trigger_type`, `owner_id`, and `name` (case-insensitive, matches part of the name). Results are sorted by `created_at`, oldest first. To fetch every active workflow:

1. Call `GET /workflows?status=active&per_page=100&page=1`.
2. Work out the number of pages: `total` divided by `per_page`, rounded up.
3. Call the same URL with `page=2`, `page=3` and so on up to that number.
4. Stop early if a page returns an empty `data` array.

Because pages are positions in a sorted list, a workflow created or deleted while the loop runs shifts later results by one. For an exact export, run the loop when nobody is editing, or de-duplicate on `id`.

## Errors

An error response has the HTTP status and a body with one plain message, for example `{"error": "workflow not found"}`. There are no error codes, so clients branch on the status and log the message as it is.

| HTTP status | Typical message | Why |
|---|---|---|
| 400 | `name is required` / `invalid cron expression` | The body is missing a field or has a value that can't be parsed. |
| 401 | `invalid API key` | The key is missing, mistyped or has been deleted. |
| 404 | `workflow not found` | No workflow with that id in the workspace. |
| 409 | `workflow is active` | `DELETE` was sent for an active workflow; deactivate it first. |
| 429 | `rate limit exceeded` | Too many requests; wait for the seconds in `Retry-After`. |
| 500 | `internal error` | An internal Nimbus error; retry `GET` requests, check before retrying `POST`. |

Responses carry no rate-limit headers, so a client learns it is over the limit only from a `429`. API keys never expire, so a `401` from a key that used to work means an Admin deleted it.
