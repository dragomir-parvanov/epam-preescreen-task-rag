---
id: nimbus-api-workflows
title: Workflows API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-25
owner: Platform API Team
---

The Workflows API lets a client's own systems list, create, change and remove workflows, switch them on and off, and read their published versions. It works on the same workflow definitions that Builders edit in the console under **Workflows**, so a change made through the API shows up in the builder straight away, and the other way round.

Every request goes to `https://api.nimbus.omnicorp.example` with an API key in the `Authorization: Bearer <api-key>` header. A key acts with Admin permissions in its workspace, so it can change any workflow regardless of who owns it; see [Creating and Rotating API Keys](nimbus-admin-api-keys.md). Bodies are JSON and every timestamp is ISO 8601 in UTC.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/workflows` | List the workspace's workflows, newest first. |
| `POST` | `/workflows` | Create a workflow. It starts inactive, as version 1. |
| `GET` | `/workflows/{id}` | Read one workflow with its trigger and steps. |
| `PATCH` | `/workflows/{id}` | Rename it, move it to a folder, change its owner, or publish a new definition. |
| `DELETE` | `/workflows/{id}` | Delete an inactive workflow and its version history. |
| `POST` | `/workflows/{id}/activate` | Validate the trigger and start accepting runs from it. |
| `POST` | `/workflows/{id}/deactivate` | Stop the trigger. Runs already in progress carry on. |
| `GET` | `/workflows/{id}/versions` | List the published versions that are still kept. |

Starting and reading runs lives in the [Runs API](nimbus-api-runs.md), and a workflow's cron schedule has its own resource, described in the [Schedules API](nimbus-api-schedules.md).

### Activating and deactivating

`POST /workflows/{id}/activate` checks the trigger before switching it on. A cron expression that doesn't parse, or a connector-event trigger with a missing field, fails the call with `400 invalid_request` and the message `WF-100: trigger configuration is invalid`, and the workflow stays inactive. Activating a workflow that is already active is harmless and returns the workflow unchanged. Deactivating stops new scheduled, event and inbound-webhook runs at once; it does not cancel a run that has already started.

### Versions

Changing `trigger` or `steps` with `PATCH` publishes the definition as a new version, exactly as **Publish** does in the builder. Changing only `name`, `description`, `folder_id` or `owner_id` updates the workflow without creating a version. Nimbus keeps the last 50 versions; `GET /workflows/{id}/versions` returns them newest first, each with its `version` number, `published_at` and `published_by`. Restoring an older version is done from **Version history** in the builder, which publishes it again as a new version; see [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md).

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | The workflow id, prefixed `wf_`. |
| `name` | string | Display name, up to 120 characters. Must be unique within its folder. |
| `description` | string or null | Free text shown in the workflow list. |
| `status` | string | `active` or `inactive`. |
| `folder_id` | string or null | The `fld_` id of its folder, or null at the top level. |
| `owner_id` | string | The `usr_` id of the owner, who must be a Builder or Admin. |
| `environment` | string | `development` or `production`. Workspaces without environments always show `production`. |
| `trigger` | object | `type` (`schedule`, `webhook`, `connector_event` or `manual`) plus that type's settings. |
| `steps` | array | Ordered steps, each with a `key`, a `type` and its configuration. |
| `version` | integer | The current published version number. |
| `published_at` | string | When the current version was published. |
| `created_at`, `updated_at` | string | Creation time and last change of any kind. |

A step's `type` is one of `action`, `transform`, `condition`, `loop`, `delay` or `approval`. Expressions inside step configuration use the double-brace syntax, for example `{{trigger.body.email}}` or `{{steps.find_deals.output.records}}`.

## Example request and response

This request creates a weekday-morning workflow that reads closed deals from Salesforce and posts a summary to Slack:

```http
POST /workflows HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 6c1f0e5a-create-daily-deals

{
  "name": "Daily closed-won digest",
  "folder_id": "fld_2207",
  "trigger": {"type": "schedule", "cron": "0 7 * * 1-5", "time_zone": "Europe/London"},
  "steps": [
    {"key": "find_deals", "type": "action", "connection_id": "con_8841",
     "action": "salesforce.query",
     "input": {"soql": "SELECT Name, Amount FROM Opportunity WHERE StageName = 'Closed Won' AND CloseDate = YESTERDAY"}},
    {"key": "post", "type": "action", "connection_id": "con_9012",
     "action": "slack.post_message",
     "input": {"channel": "#sales-wins", "text": "{{default(steps.find_deals.output.totalSize, 0)}} deals closed yesterday"}}
  ]
}
```

Nimbus answers `201 Created` with the new workflow. It is inactive until it is activated.

```json
{
  "id": "wf_7731",
  "name": "Daily closed-won digest",
  "description": null,
  "status": "inactive",
  "folder_id": "fld_2207",
  "owner_id": "usr_1180",
  "environment": "production",
  "trigger": {"type": "schedule", "cron": "0 7 * * 1-5", "time_zone": "Europe/London"},
  "steps": [{"key": "find_deals", "type": "action"}, {"key": "post", "type": "action"}],
  "version": 1,
  "published_at": "2026-05-18T08:02:11Z",
  "created_at": "2026-05-18T08:02:11Z",
  "updated_at": "2026-05-18T08:02:11Z"
}
```

A workflow created with an API key is owned by the Admin who created that key unless the body sets `owner_id`.

## Filtering and pagination

`GET /workflows` accepts these query parameters, which can be combined:

| Parameter | Effect |
|---|---|
| `status` | `active` or `inactive`. |
| `folder_id` | Only workflows in that folder; `none` for the top level. |
| `owner_id` | Only workflows owned by that user. |
| `trigger_type` | `schedule`, `webhook`, `connector_event` or `manual`. |
| `environment` | `development` or `production`. |
| `q` | Case-insensitive match on the name. |

The list is cursor-based. `limit` sets the page size (default 25, maximum 100) and `cursor` asks for the page after a previous one. To collect every active workflow in a folder:

1. Call `GET /workflows?status=active&folder_id=fld_2207&limit=100`.
2. Read the `data` array and keep the workflows.
3. If `next_cursor` is not null, call the same URL again with `&cursor=<next_cursor>` added.
4. Stop when `next_cursor` is null; that was the last page.

Keep the other parameters identical between pages. A cursor is only valid for the filter it was issued with. `GET /workflows/{id}/versions` pages the same way.

## Errors

Errors use the standard envelope `{"error": {"code": "...", "message": "..."}}`; see [API Error Format and Idempotency](nimbus-api-error-format.md).

| HTTP status | Code | Typical cause on this resource |
|---|---|---|
| 400 | `invalid_request` | Missing `name`, an unknown step `type`, an expression that doesn't parse, or `WF-100` on activate. |
| 400 | `invalid_request` | `owner_id` names a Viewer; owners must be Builders or Admins. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 404 | `not_found` | No workflow with that id in this workspace, or the `folder_id` or `connection_id` doesn't exist. |
| 409 | `conflict` | `DELETE` on an active workflow (deactivate it first), or a name already used in the same folder. |
| 429 | `rate_limited` | The workspace went over its API limit; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | A fault on the Nimbus side; retry with the same `Idempotency-Key`. |
