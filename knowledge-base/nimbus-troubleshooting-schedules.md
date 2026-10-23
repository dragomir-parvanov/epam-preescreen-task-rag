---
id: nimbus-troubleshooting-schedules
title: Troubleshooting Scheduled Workflows
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-02-16
owner: Support Engineering
---

A schedule trigger starts a workflow from a standard cron expression, evaluated in the workspace time zone or in an IANA time zone chosen on the trigger, such as `Europe/London` or `America/Chicago`. When a schedule "doesn't work", the cause is almost always one of three things: the expression means something other than what the client intended, the time zone isn't the one they think, or the schedule fired and the run was rejected.

How to set a schedule up is described in [Scheduling Workflows](nimbus-admin-scheduling-workflows.md) and, for the API, in [Schedules API](nimbus-api-schedules.md).

## Symptoms

- A workflow didn't run at all at the expected time, and **Runs** has nothing for it.
- Runs happen, but an hour early or late, often starting on the weekend the clocks change.
- Runs happen at a time that matches UTC rather than the client's office hours.
- A run is listed at the right time but failed straight away with WF-300, without running any steps.
- Saving the trigger in the builder fails with WF-100, or the trigger panel's **Next run** field is empty.
- A one-off daily job ran twice, or not at all, on one particular night.

## Common causes

**The wrong time zone.** Without a time zone on the trigger, the cron expression uses the workspace time zone from **Settings > Workspace**. Workspaces created with the default of UTC, or by someone in another office, run schedules at times that look wrong locally. A schedule with an explicit time zone ignores the workspace setting entirely, which surprises clients who later change the workspace time zone and expect the schedule to follow.

**Daylight saving changes.** A schedule in a zone with daylight saving follows local clock time. On the night the clocks go forward, a time in the skipped hour doesn't exist: a job at 01:30 in `Europe/London` is skipped on the last Sunday of March and doesn't run that day. On the night the clocks go back, the repeated hour happens twice, and a job in it runs only on the first occurrence. A schedule set in UTC never shifts, so it appears to move by an hour against local time twice a year.

**An invalid expression.** Nimbus accepts five-field cron (minute, hour, day of month, month, day of week). Quartz-style expressions with a seconds field or `?`, and names in the wrong field, are rejected with WF-100.

**An interval shorter than the Plan Tier allows.** The minimum schedule interval is 15 minutes on Starter, 5 minutes on Business and 1 minute on Enterprise. A schedule that would fire more often than that can't be saved; see [Schedule Frequency Limits](nimbus-tier-schedule-intervals.md).

**The workflow is inactive.** A deactivated workflow keeps its schedule settings but nothing fires until it is activated again. The same applies to a workflow that was published but never activated.

**The run was rejected.** At 100% of the monthly workflow runs, scheduled runs are rejected with WF-300 until the quota resets on the 1st of the month (UTC) or the Plan Tier is upgraded. The schedule itself is working; it is the run that is refused.

**The change wasn't published.** Edits to the trigger in the builder take effect when the workflow is published; until then the previous version's schedule keeps running.

## Diagnosing the problem

1. Read the live schedule through the API rather than from a screenshot of the builder:

```http
GET /workflows/wf_7730/schedule HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{"cron": "30 1 * * *", "time_zone": "Europe/London", "enabled": true, "next_run_at": "2026-03-30T00:30:00Z", "last_run_at": "2026-03-28T01:30:00Z"}
```

2. Convert `next_run_at`, which is always UTC, into the schedule's time zone and check it against what the client expects. In the example the job skipped 29 March, the day the clocks went forward.
3. If `time_zone` is missing from the response, check **Settings > Workspace** for the workspace time zone the schedule is using.
4. Confirm the workflow is active under **Workflows**, and that the version with the schedule change has been published.
5. Filter **Runs** by the workflow and the time window. A run that failed at once with WF-300 means the schedule fired correctly and the quota stopped the run.

## Error reference

| Code | Where the client sees it | Meaning |
|---|---|---|
| WF-100 | When saving the trigger, and on the trigger panel | The trigger configuration is invalid: the cron expression isn't valid five-field cron, the interval is below the Plan Tier's minimum, or a required trigger field is missing. |
| WF-300 | On a run under **Runs** | The workspace has used its monthly workflow runs; the scheduled run was rejected. |
| WF-500 | On a run under **Runs** | An internal Nimbus error; the schedule fired but the run failed. The run can be retried. |

## Fixes

1. Set an explicit IANA time zone on the trigger, so the schedule no longer depends on the workspace setting.
2. Keep daily jobs outside the local daylight-saving changeover window, which is between 01:00 and 03:00 in most European and North American zones. If a job must run in that window every day, schedule it in UTC and accept that its local time moves twice a year.
3. Rewrite the expression as five-field cron. Some common patterns:

```cron
# Weekdays at 07:00 in the trigger's time zone
0 7 * * 1-5
# Every 15 minutes, the shortest interval Starter allows
*/15 * * * *
# 06:30 on the first day of every month
30 6 1 * *
```

4. Activate the workflow under **Workflows**, or with `POST /workflows/{id}/activate`, and publish any pending change to the trigger.
5. If the schedule needs a shorter interval than the Plan Tier allows, the options are to upgrade or to use an event trigger instead.
6. For WF-300, see [Troubleshooting Run Quota Errors](nimbus-troubleshooting-run-quota.md). Rejected scheduled runs aren't replayed after the reset; start a missed run by hand with **Run now** if it matters.

A schedule can also be replaced in one call with `PUT /workflows/{id}/schedule`, which is useful when a client manages many workflows from a script.

## Escalating to support

Escalate when `next_run_at` is correct but no run, rejected or otherwise, appears for that time. Collect:

- the workflow id (`wf_...`) and the full response of `GET /workflows/{id}/schedule`;
- the expected fire time with its time zone, and the actual time, if any, in UTC;
- the ids of the runs just before and after the gap;
- the workspace time zone from **Settings > Workspace**.
