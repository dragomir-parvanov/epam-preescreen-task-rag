---
id: nimbus-admin-scheduling-workflows
title: Scheduling Workflows
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-04-06
owner: Workspace Administration Team
---

A schedule trigger starts an OmniCorp Nimbus workflow at fixed times: every weekday at 07:00, on the first of the month, every 15 minutes during office hours. Schedules are written as cron expressions and evaluated in a time zone, which is where most of the questions about them come from, particularly around daylight saving changes.

This guide covers adding a schedule, choosing its time zone, what happens when the clocks change, the shortest interval each Plan Tier allows, and pausing a schedule without unpublishing the workflow.

## Before you begin

- **Role:** Builder or Admin. Viewers can see a workflow's schedule and its next run times but can't change them.
- **Plan Tier:** schedules work on every tier, but the shortest interval differs:

| Plan Tier | Minimum interval between scheduled runs |
|---|---|
| Starter | 15 minutes |
| Business | 5 minutes |
| Enterprise | 1 minute |

- **Run quota:** every scheduled run counts towards the workspace's monthly workflow runs from the moment it starts. A workflow that runs every 5 minutes uses close to 9,000 runs a month on its own, so check **Settings > Usage** before setting a frequent schedule.
- **Time zone:** know which time zone the client means. "09:00" for a team in Singapore and one in Lisbon are different moments.

## How it works

A schedule is a standard five-field cron expression: minute, hour, day of month, month and day of week. Some common patterns:

```cron
# minute hour day-of-month month day-of-week
0 7 * * 1-5        # 07:00 Monday to Friday
*/15 8-18 * * 1-5  # every 15 minutes from 08:00 to 18:45 on weekdays
30 2 1 * *         # 02:30 on the 1st of every month
0 */4 * * *        # every 4 hours, on the hour
```

Nimbus evaluates the expression in the workspace time zone set under **Settings > Workspace**, unless the schedule names its own IANA time zone, such as `America/Chicago`. Use a schedule time zone when a workflow serves a team in a different place from the rest of the workspace; it also protects the schedule from a later change to the workspace setting. See [Managing Workspace Settings](nimbus-admin-workspace-settings.md).

### Daylight saving time

Because schedules follow the local clock, a run set for 07:00 stays at 07:00 local time all year, and its UTC time moves when the clocks change. Two edge cases need care:

- **Clocks go forward.** Local times inside the skipped hour don't exist that night. A schedule set for a time in the gap, such as 01:30 in `Europe/London` on the last Sunday of March, runs once at the first valid minute after the gap, 02:00.
- **Clocks go back.** Local times in the repeated hour happen twice. A schedule set for 01:30 runs once, at the first occurrence.

Schedules that repeat every few minutes or hours follow real elapsed time across both changes, so they neither skip nor double a run. To avoid daylight saving behaviour entirely, give the schedule the time zone `UTC`.

A schedule more frequent than the Plan Tier's minimum can't be saved. If a downgrade leaves an existing schedule too frequent, each occurrence is rejected with WF-100 until a Builder edits it. When the workspace has used its monthly runs, scheduled runs are rejected with WF-300; when it is at its concurrent-run limit, they wait as `queued` with the notice WF-310 and start as soon as a slot is free.

## Step-by-step

1. Open **Workflows**, open the workflow and click its trigger at the top of the builder.
2. Choose **Schedule** as the trigger type.
3. Enter the **Cron expression**, or build it with the **Simple** tab (frequency, days and time). The panel shows the next five run times as you type.
4. Under **Time zone**, keep **Workspace default** or pick an IANA time zone.
5. Click **Publish**. The schedule starts with the published version; drafts never run on a schedule.

To pause, open the trigger and switch **Paused** on, then publish. The workflow stays published, **Run now** still works, and occurrences missed while paused are not run later. Switch it off to resume from the next occurrence.

The API manages a schedule as a sub-resource of the workflow:

```http
PUT /workflows/wf_7730/schedule HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"cron": "0 7 * * 1-5", "time_zone": "Europe/London", "paused": false}
```

The response includes `next_run_at`, in UTC. `GET /workflows/{id}/schedule` reads the schedule, and `DELETE /workflows/{id}/schedule` removes it, after which the workflow only runs manually.

## Verifying the change

The trigger panel lists the next five run times in the schedule's time zone; check them against what the client asked for, particularly across a daylight saving date. On the **Workflows** list, the workflow shows a clock icon with its next run time, or **Paused**. After the first occurrence, filter the **Runs** page by the workflow: a scheduled run shows the trigger **Schedule** and starts within a few seconds of the planned time. `GET /workflows/{id}/schedule` returns `paused` and `next_run_at`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Runs more often than the minimum interval for this Plan Tier" when saving | The cron fires more often than the tier allows. | Lengthen the interval or upgrade the tier. |
| Runs fail at once with WF-100 | The expression is invalid, or a downgrade made it too frequent. | Correct the expression in the trigger and publish. |
| Runs start an hour early or late | The schedule uses a different time zone from the one the client expects, or a daylight saving change. | Set the intended IANA time zone on the schedule. |
| No run on the night the clocks went forward | The schedule fell in the skipped hour. | It ran at the first valid minute instead; check run history around 02:00 local. |
| Scheduled runs rejected with WF-300 | The monthly run quota is used up. | Wait for the reset on the 1st (UTC) or upgrade. |
| Runs sit in `queued` with WF-310 | The concurrent-run limit was reached. | Stagger schedules so they don't all start on the same minute. |
