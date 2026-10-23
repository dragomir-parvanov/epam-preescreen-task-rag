---
id: nimbus-api-workspace
title: Workspace API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-02-23
owner: Platform API Team
---

The Workspace API describes the workspace an API key belongs to: its name, data region, time zone and Plan Tier, and how much of its monthly runs, seats, active connectors and secrets it is using. A client typically calls it from a monitoring job, to warn their own team before a quota runs out rather than after.

There is nothing to create or delete here; every endpoint is a `GET`, and the workspace is always the one the key belongs to, so no workspace id appears in the path. Settings such as the name and time zone are changed by an Admin under **Settings > Workspace**; see [Managing Workspace Settings](nimbus-admin-workspace-settings.md). Authenticate with `Authorization: Bearer <api-key>`.

## Endpoints

| Method | Path | Purpose | Since |
|---|---|---|---|
| `GET` | `/workspace` | The workspace's identity and configuration. | 3.0 |
| `GET` | `/workspace/usage` | Current-month usage against the Plan Tier's limits. | 3.5 |
| `GET` | `/workspace/entitlements` | The features and limits the Plan Tier includes. | 3.0 |

`GET /workspace/entitlements` returns, as machine-readable flags and numbers, the same entitlements that [Plan Tiers and Entitlements](nimbus-plan-tiers.md) lists per tier. Use that Article for the values and this endpoint to read them at run time, for example to hide an option in the client's own tooling when the tier doesn't include it.

### Reading usage

`GET /workspace/usage` arrived in 3.5, together with the usage dashboard under **Settings > Usage**, and returns the same four counters the dashboard shows. Each counter has `used` and `limit`; `limit` is null where the tier has no limit. How each one is counted:

| Counter | Counts |
|---|---|
| `runs` | Workflow runs started since the 1st of the month (UTC). Test runs in the builder don't count; a run counts when it starts, whatever its outcome. |
| `seats` | Active users of any role. Suspended users and pending invitations don't count. |
| `active_connectors` | Connectors with at least one connection used by an active workflow. |
| `secrets` | Entries in the secrets vault. |

`runs` also carries `percent_used`, which drives the quota alert emails Admins receive at 80% and 100%. At 100%, new runs are rejected with `WF-300` until the counter resets on the 1st or the tier is upgraded; see [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).

## Object fields

The workspace object from `GET /workspace`:

| Field | Type | Description |
|---|---|---|
| `id` | string | Workspace id, prefixed `ws_`. |
| `name` | string | Display name shown in the console header. |
| `data_region` | string | `eu`, `us` or `apac`; `apac` exists only on Enterprise. Set when the workspace was created and never changes. |
| `time_zone` | string | IANA time zone, e.g. `Europe/Berlin`; the default for schedule triggers. |
| `plan_tier` | string | `starter`, `business` or `enterprise`. |
| `pending_plan_change` | object or null | A downgrade waiting for the end of the billing period: `plan_tier` and `effective_at`. |
| `platform_version` | string | `v3`. |
| `sandbox` | boolean | True for an Enterprise sandbox workspace. |
| `created_at` | string | When the workspace was created. |

`time_zone` is only the default for schedule triggers: a workflow can name its own IANA time zone in its cron trigger, and that choice wins. Changing the workspace time zone moves the schedules that rely on the default from their next run.

Upgrades take effect immediately, so they never appear in `pending_plan_change`; a downgrade shows there until the end of the current billing period. Moving to another region means creating a new workspace and migrating the workflows; see [Creating a Workspace](nimbus-admin-creating-a-workspace.md).

## Example request and response

```http
GET /workspace HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "id": "ws_4821",
  "name": "ClientCo Operations",
  "data_region": "eu",
  "time_zone": "Europe/London",
  "plan_tier": "enterprise",
  "pending_plan_change": null,
  "platform_version": "v3",
  "sandbox": false,
  "created_at": "2025-04-22T10:31:07Z"
}
```

The usage of the same workspace in the middle of February:

```json
{
  "period": {"start": "2026-02-01T00:00:00Z", "end": "2026-03-01T00:00:00Z"},
  "runs": {"used": 418230, "limit": null, "percent_used": null},
  "seats": {"used": 612, "limit": null},
  "active_connectors": {"used": 37, "limit": null},
  "secrets": {"used": 291, "limit": null},
  "updated_at": "2026-02-16T08:40:00Z"
}
```

On Enterprise every counter is unlimited, so `limit` and `percent_used` are null. On a Business workspace the same call returns numbers, for example `"runs": {"used": 81240, "limit": 100000, "percent_used": 81.2}`, which would already have triggered the 80% alert. Counters are refreshed every few minutes; `updated_at` says when.

## Filtering and pagination

None of the three endpoints returns a list, so there is no `limit` or `cursor`. `GET /workspace/usage` takes one query parameter, `period`: `current` (the default) or `previous`, for the month that ended on the last 1st. Earlier months aren't available through the API.

A daily quota monitor on the client's side can be built like this:

1. Call `GET /workspace/usage` once a day; more often adds nothing, given the refresh interval.
2. For each counter with a non-null `limit`, compute `used / limit`.
3. Raise a warning in the client's own channel when a counter passes their threshold, such as 70%, earlier than Nimbus's own 80% email.
4. On the 2nd of each month, call `GET /workspace/usage?period=previous` and store the final figures for capacity planning.

```python
import requests

resp = requests.get(
    "https://api.nimbus.omnicorp.example/workspace/usage",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=10,
)
for name in ("runs", "seats", "active_connectors", "secrets"):
    counter = resp.json()[name]
    if counter["limit"] and counter["used"] / counter["limit"] >= 0.7:
        print(f"{name}: {counter['used']} of {counter['limit']}")
```

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `period` is something other than `current` or `previous`. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 429 | `rate_limited` | Too many requests; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | A Nimbus fault; try again shortly. |

A `404` is not possible here: the key always identifies its own workspace. A workspace that an Admin has deleted stops accepting its keys, which then get `401`.
