---
id: nimbus-api-schedules
title: Schedules API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2025-12-08
owner: Platform API Team
---

The Schedules API reads, sets and removes the schedule of a single workflow. A schedule is a cron expression plus a time zone; while the workflow is active, Nimbus starts a run each time the expression matches. The schedule is a sub-resource of its workflow, so every path starts with `/workflows/{id}` and there is no workspace-wide schedule list.

This is the API counterpart of the Schedule trigger in the workflow builder. For the console steps and advice on choosing a cron expression, see [Scheduling Workflows](nimbus-admin-scheduling-workflows.md). Requests use an API key in the `Authorization: Bearer <api-key>` header.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/workflows/{id}/schedule` | Read the workflow's schedule and its next run time. |
| `PUT` | `/workflows/{id}/schedule` | Set or replace the schedule, making Schedule the workflow's trigger. |
| `DELETE` | `/workflows/{id}/schedule` | Remove the schedule; the workflow can then only be run manually. |

### Setting a schedule

`PUT` takes the whole schedule: `cron` is required and `time_zone` is optional. If the workflow's trigger is Manual, the call turns it into a Schedule trigger; if it already has a schedule, the new one replaces it. Each successful `PUT` publishes a new workflow version, so the change shows in Version history with the API key as its author. The new `next_run_at` is calculated straight away and returned in the response.

A workflow has exactly one trigger. A workflow started by an inbound webhook or a connector event can't also have a schedule, and `PUT` answers `409 conflict`; change the trigger in the builder first.

### Removing a schedule

`DELETE` answers `204 No Content` and sets the trigger back to Manual, which also publishes a new version. Runs that have already started are not affected. The workflow stays active and can still be started with **Run now** or `POST /workflows/{id}/runs`.

## Object fields

| Field | Type | Description |
|---|---|---|
| `workflow_id` | string | The workflow this schedule belongs to (`wf_`). Read-only. |
| `cron` | string | Five-field cron expression: minute, hour, day of month, month, day of week. |
| `time_zone` | string or null | IANA time zone name, such as `Europe/London` or `America/Chicago`. `null` means the workspace time zone. |
| `effective_time_zone` | string | The time zone actually used: `time_zone`, or the workspace time zone when that is `null`. Read-only. |
| `next_run_at` | string or null | When the next run is due, in ISO 8601 UTC. `null` while the workflow is deactivated. Read-only. |
| `last_run_id` | string or null | The run id (`run_`) of the most recent scheduled run. Read-only. |
| `updated_at` | string | When the schedule last changed. Read-only. |

The workspace time zone is set under **Settings > Workspace**. Leaving `time_zone` as `null` means a later change there moves every such schedule with it, which is usually what a client wants; set an explicit zone when a workflow must follow a particular office's clock.

Cron fields accept numbers, `*`, ranges (`1-5`), lists (`1,15`) and steps (`*/15`). Six-field expressions with seconds and the non-standard `@daily` shortcuts are rejected. In a zone with daylight saving time, a local time skipped when the clocks go forward runs at the next valid minute, and a local time that occurs twice when they go back runs once.

## Example request and response

Run a Salesforce-to-Snowflake sync at 06:30 Berlin time on weekdays:

```http
PUT /workflows/wf_8kD2nR4q/schedule HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "cron": "30 6 * * 1-5",
  "time_zone": "Europe/Berlin"
}
```

```json
{
  "workflow_id": "wf_8kD2nR4q",
  "cron": "30 6 * * 1-5",
  "time_zone": "Europe/Berlin",
  "effective_time_zone": "Europe/Berlin",
  "next_run_at": "2025-12-09T05:30:00Z",
  "last_run_id": "run_5Zt0mV7c",
  "updated_at": "2025-12-08T10:02:44Z"
}
```

`next_run_at` is in UTC: 06:30 in Berlin in December is 05:30 UTC. Each scheduled run counts against the workspace's monthly workflow runs, and once the quota is used up scheduled runs are rejected with WF-300 while `next_run_at` keeps advancing.

## Filtering and pagination

The schedule endpoints return a single object, so they take no query parameters and are never paginated. To review every schedule in a workspace, combine them with the cursor-paginated workflow list, filtered to scheduled workflows:

1. Call `GET /workflows?trigger_type=schedule&limit=100`.
2. For each workflow in `data`, call `GET /workflows/{id}/schedule` and record `cron`, `effective_time_zone` and `next_run_at`.
3. If `next_cursor` is not `null`, call `GET /workflows?trigger_type=schedule&limit=100&cursor=<next_cursor>` and repeat step 2.
4. Stop when `next_cursor` is `null`.

`limit` defaults to 25 and can be at most 100. Adding `status=active` to the workflow list skips deactivated workflows, whose `next_run_at` is always `null`. The full workflow filters are in [Workflows API](nimbus-api-workflows.md).

## Errors

All errors use the common `{"error": {"code": "...", "message": "..."}}` envelope. For schedule problems the `message` starts with the workflow error code, so a client can tell an invalid expression from a tier limit.

| HTTP status | Code | Cause |
|---|---|---|
| 400 | `invalid_request` | `WF-100`: the cron expression can't be parsed, has the wrong number of fields, or `time_zone` isn't a known IANA name. |
| 400 | `invalid_request` | The expression fires more often than the Plan Tier's minimum schedule interval. |
| 401 | `unauthorized` | Missing, expired or revoked API key. |
| 404 | `not_found` | The workflow doesn't exist, or `GET`/`DELETE` was called on a workflow that has no schedule. |
| 409 | `conflict` | The workflow's trigger is an inbound webhook or a connector event, not Manual or Schedule. |
| 429 | `rate_limited` | Too many API requests; wait and retry. |

A rejected `PUT` changes nothing: the previous schedule and its `next_run_at` stay in place.

The minimum interval is checked against the gap between any two consecutive matches of the expression, not just the step value:

| Plan Tier | Minimum schedule interval | Example of the tightest valid cron |
|---|---|---|
| Starter | 15 minutes | `*/15 * * * *` |
| Business | 5 minutes | `*/5 * * * *` |
| Enterprise | 1 minute | `* * * * *` |

So `0,5 9 * * *` is rejected on Starter even though it runs only twice a day. See [Schedule Frequency Limits](nimbus-tier-schedule-intervals.md) for how the limits change on an upgrade or downgrade.
