---
id: nimbus-tier-schedule-intervals
title: Schedule Frequency Limits
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-10-06
owner: Product Operations
---

A schedule trigger starts a workflow from a cron expression. The Plan Tier sets how close together two runs of the same schedule may be: the minimum schedule interval. A Starter workspace can't save a schedule that fires every 5 minutes, and a Business workspace can't save one that fires every minute; Nimbus rejects the expression with WF-100 when the workflow is saved.

This guide explains how Nimbus measures the interval, which expressions pass on which tier, and what happens to existing schedules when a workspace changes tier. The general mechanics of setting up a schedule are in [Scheduling Workflows](nimbus-admin-scheduling-workflows.md).

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Schedule triggers | Yes | Yes | Yes |
| Minimum schedule interval | 15 minutes | 5 minutes | 1 minute |
| Fastest regular expression | `*/15 * * * *` | `*/5 * * * *` | `* * * * *` |
| Time zone per schedule | Yes | Yes | Yes |

The limit applies only to schedule triggers. Connector event triggers, inbound webhook triggers and manual runs aren't affected by it.

## How it works

Nimbus schedules use five-field cron expressions (minute, hour, day of month, month, day of week). There is no seconds field. Each schedule runs in the workspace time zone set under **Settings > Workspace**, unless the schedule names its own IANA time zone, such as `Europe/Berlin` or `America/Chicago`.

When a Builder saves a schedule, Nimbus works out every firing time over the next 7 days and finds the shortest gap between two consecutive firings. If that gap is shorter than the tier's minimum, the save fails with WF-100 and the builder highlights the cron field. The check uses the shortest gap, not the average, so irregular lists of minutes are caught as well as step values:

| Expression | Shortest gap | Starter | Business | Enterprise |
|---|---|---|---|---|
| `0 * * * *` | 60 minutes | Accepted | Accepted | Accepted |
| `*/15 * * * *` | 15 minutes | Accepted | Accepted | Accepted |
| `0,10,30,45 * * * *` | 10 minutes | WF-100 | Accepted | Accepted |
| `*/5 8-18 * * 1-5` | 5 minutes | WF-100 | Accepted | Accepted |
| `0,2 9 * * *` | 2 minutes | WF-100 | WF-100 | Accepted |
| `* * * * *` | 1 minute | WF-100 | WF-100 | Accepted |

Gaps are measured on the schedule's own clock, so a daylight-saving change never turns a valid schedule into a rejected one, even on the night the clocks go back and an hour repeats.

The minimum interval is per schedule. Two workflows on the same 15-minute schedule are both allowed on Starter, even though together they start a run every 15 minutes twice over.

## Turning it on

The limit is enforced whenever a schedule is created or changed. To set a schedule within the limit:

1. Open the workflow in **Workflows** and select the trigger.
2. Choose **Schedule** and enter the cron expression, or pick a preset such as **Every 15 minutes**. Presets that are too frequent for the tier are greyed out.
3. Leave **Time zone** on **Workspace default**, or select an IANA time zone.
4. Check the **Next runs** preview under the field, which lists the next five firing times in that zone.
5. Publish the workflow. If the expression is too frequent, publishing stops with WF-100 and the message names the tier's minimum.

Clients with API access can set the same schedule with `PUT /workflows/{id}/schedule`:

```http
PUT /workflows/wf_2Rn8Yd/schedule HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{ "cron": "*/5 7-19 * * 1-5", "time_zone": "Europe/London" }
```

A Business workspace sending `"cron": "* * * * *"` gets `400` with a body like this:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "WF-100: The schedule fires every 1 minute; the minimum interval on your plan is 5 minutes."
  }
}
```

`GET /workflows/{id}/schedule` returns the saved expression, the time zone and the next firing time.

## Limits

| Plan Tier | Minimum interval | Most runs one schedule can start in a 31-day month |
|---|---|---|
| Starter | 15 minutes | 2,976 |
| Business | 5 minutes | 8,928 |
| Enterprise | 1 minute | 44,640 |

The right-hand column is worth showing clients before they shorten an interval. A single Starter workflow on a 15-minute schedule uses well over half of the 5,000 monthly runs on its own, and runs above the quota are rejected with WF-300; see [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md). Where a client wants near-real-time reaction rather than frequent polling, a connector event or inbound webhook trigger is usually the better design, because it starts a run only when something has changed.

Other values that apply to every tier:

- WF-100 is also the code for a malformed expression, such as a six-field cron with seconds, so read the message to tell a syntax error from a frequency error.
- A workflow has at most one schedule trigger. A client that wants two different cadences builds two workflows, each checked against the minimum on its own.
- Schedules on inactive workflows don't fire.

## When the Plan Tier changes

An upgrade takes effect immediately. Builders can save more frequent schedules as soon as the change is applied; existing schedules keep their current expressions until someone changes them.

A downgrade takes effect at the end of the current billing period, and schedules that are now too frequent are not rewritten for the client. When the downgrade takes effect:

1. Each schedule whose shortest gap is below the new minimum is paused. Its workflow stays active, so its other triggers aren't affected, but the schedule stops firing.
2. The builder shows WF-100 on the paused trigger, with the new tier's minimum.
3. Every Admin receives an email listing the paused schedules by workflow.
4. A Builder edits each expression to fit, and the schedule resumes as soon as the workflow is published.

When the downgrade is booked, go through the client's scheduled workflows with them and change the expressions in advance, so nothing pauses on the day. A schedule that fired every 5 minutes on Business can usually become `*/15 * * * *` on Starter, combined with a batch step that processes everything that arrived in the 15 minutes since the last run.
