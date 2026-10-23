---
id: nimbus-tier-workflow-run-quotas
title: Workflow Run Quotas
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-16
owner: Product Operations
---

Every Nimbus workspace has a monthly allowance of workflow runs set by its Plan Tier. The quota is counted per workspace, not per workflow or per user, and it covers every way a run can start: schedules, inbound webhook triggers, connector events and manual runs. This guide explains what counts, how Admins are warned before the allowance runs out, and what a client sees when it does.

Use it when a client asks why a scheduled workflow stopped firing near the end of the month, or when they are deciding whether their volume fits their current tier.

## Availability by Plan Tier

The quota applies on every tier. Enterprise has no monthly ceiling, but its runs are still counted and shown on the usage dashboard.

| | Starter | Business | Enterprise |
|---|---|---|---|
| Workflow runs per month | 5,000 | 100,000 | Unlimited |
| Builder test runs counted | No | No | No |
| Quota alert emails to Admins | 80% and 100% | 80% and 100% | Not sent (no ceiling) |
| Runs rejected with WF-300 at the limit | Yes | Yes | Never |
| Usage on Settings > Usage and `GET /workspace/usage` | Yes | Yes | Yes |

For the full list of what each tier includes, see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## How it works

A run is counted at the moment it starts, whatever happens to it afterwards. A run that fails on its second step, times out with WF-210 or is cancelled by a Builder has still used one run from the quota. Step retries inside a run don't add to the count: a connector step that is retried three times before succeeding is still part of one run.

What counts and what doesn't:

- **Counts:** scheduled runs, runs started by an inbound webhook trigger, runs started by a connector event, **Run now** on a published workflow, and `POST /workflows/{id}/runs`.
- **Counts once:** a run that pauses at an approval step. It is counted when it starts and not again when an approver releases it.
- **Counts in both environments:** on workspaces with environments switched on, runs in Development use the same quota as runs in Production.
- **Doesn't count:** **Test run** in the builder, which runs the unpublished draft against sample data and is labelled `test` in run history.
- **Doesn't count:** a run that was rejected with WF-300, because it never started.

The quota period is the calendar month in UTC. Usage resets to zero at 00:00 UTC on the 1st of each month, whatever the workspace time zone is set to under **Settings > Workspace**. A workspace in a time zone ahead of UTC therefore regains its allowance during the morning of the 1st, local time, not at midnight.

### Quota alerts and WF-300

Since release 3.5.0, every Admin in the workspace is emailed when usage reaches 80% of the monthly quota and again when it reaches 100%. Each alert is sent once per month. The email names the workspace, the runs used, the limit and the reset date, and links to **Settings > Usage**. Alert recipients can't be changed: the emails go to all Admins, not to the default notification recipients.

At 100%, Nimbus stops starting new runs until the quota resets or the tier is upgraded:

1. Scheduled and event-triggered runs are rejected and recorded in run history with status `failed` and error WF-300.
2. Inbound webhook triggers answer `403 Forbidden` with the code `forbidden` and a message starting `WF-300` instead of `202 Accepted`, so the caller can tell the payload was not processed.
3. Manual runs are rejected too, both from **Run now** and from the API.
4. Runs that had already started before the limit was reached carry on to completion.

Rejected runs aren't replayed later. Events that arrived while the workspace was at its limit have to be resent by the source system or rerun by hand after the reset.

## Turning it on

The quota is always enforced and needs no setup. What an Admin should do is check usage and make sure the alert emails reach someone who can act on them.

1. Go to **Settings > Usage** and read the **Workflow runs** card: runs used this month, the limit and the projected total at the current daily rate.
2. Select **View by workflow** to see which workflows used the most runs this month. A schedule that fires every few minutes is the usual cause of a sudden climb.
3. Go to **Settings > Users** and confirm that at least one Admin who reads email is active, because quota alerts go only to Admins.
4. If the projection is above the limit, reduce the busiest schedules or ask the account owner to request an upgrade.

The same figures are available from the API to workspaces with API access, for clients that feed them into their own monitoring:

```http
GET /workspace/usage HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "period_start": "2026-02-01T00:00:00Z",
  "period_end": "2026-03-01T00:00:00Z",
  "workflow_runs": { "limit": 100000, "used": 82417, "alerts_sent": ["80_percent"] },
  "seats": { "limit": 250, "used": 184 },
  "active_connectors": { "limit": 50, "used": 37 },
  "secrets": { "limit": 250, "used": 41 }
}
```

On Enterprise, `workflow_runs.limit` is `null` and `alerts_sent` is always empty.

## Limits

| Item | Value |
|---|---|
| Starter | 5,000 runs per month |
| Business | 100,000 runs per month |
| Enterprise | Unlimited |
| Quota period | Calendar month, 00:00 UTC on the 1st to the end of the month |
| Alert thresholds | 80% and 100%, emailed to every Admin |
| Error when the quota is used up | WF-300 |
| Manual API call at the limit | `403` with `{"error": {"code": "forbidden", "message": "WF-300: ..."}}` |

Unused runs don't carry over to the next month, and there is no way to buy extra runs within a tier. A client that regularly reaches the limit needs a higher tier, or fewer runs: batching records in a loop step inside one run, rather than starting one run per record, is the most effective change. The quota is separate from the [concurrent-run limit](nimbus-tier-concurrent-runs.md), which caps how many runs can be in progress at the same time.

## When the Plan Tier changes

An upgrade takes effect immediately. The new quota applies to the current month straight away, so a Starter workspace that was blocked at 5,000 runs can start new runs again as soon as it moves to Business. Runs already rejected with WF-300 stay rejected; the next scheduled firing or incoming event starts normally.

A downgrade takes effect at the end of the current billing period, and the lower quota applies from that moment. Runs already used in the current calendar month count against the new limit, so a workspace that has used 40,000 runs and drops to Starter mid-month is immediately over its quota and every new run is rejected with WF-300 until the 1st. As with seats and active connectors, a downgrade can be held when usage is above the new tier's limits, so check **Settings > Usage** with the client before the downgrade is due, and reduce schedules first if needed (see [Schedule Frequency Limits](nimbus-tier-schedule-intervals.md)).
