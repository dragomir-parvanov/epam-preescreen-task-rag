---
id: nimbus-troubleshooting-third-party-throttling
title: Troubleshooting Third-Party Throttling
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-09
owner: Support Engineering
---

Every SaaS application limits how hard an integration may call its API. When an application refuses a call from a Nimbus connector because the connected account has used up its allowance, the step reports CONN-429. This is the third-party application throttling Nimbus, not Nimbus throttling the client: the Nimbus API's own limits are covered in [API Rate Limits and Webhooks](nimbus-api-webhooks.md) and [Troubleshooting API Errors](nimbus-troubleshooting-api-errors.md).

The allowances themselves belong to the vendor and differ by vendor, edition and contract, so this reference doesn't quote them. Point the client to the vendor's own documentation or account team for the numbers, and use the steps below to reduce how many calls their workflows make.

## Symptoms

- In run history, a step shows the amber **Retrying** badge with CONN-429, and the run stays in `running` far longer than usual.
- Runs that normally finish in seconds take many minutes, and some end as `timed_out` because the whole run passed 60 minutes.
- A run fails with CONN-429 on the last attempt of a step.
- Failures cluster at particular times of day, often just after several scheduled workflows start together, or near the end of a vendor's daily allocation window.
- Other integrations the client runs against the same application start failing at the same time, because they share the same allowance.

## Common causes

Throttling is almost always a volume problem on the client's side of the integration, made visible by Nimbus.

A **loop step that calls the application once per item** is the most common cause. A loop over 4,000 HubSpot contacts with an **Update contact** action inside makes 4,000 calls in quick succession, where one batch action would make a few dozen.

**Unfiltered polling triggers** read every changed record on every poll. A Salesforce trigger on all updated Opportunities, in an org where an internal job touches every record nightly, starts a flood of runs that each call back into Salesforce.

**Many workflows sharing one connection** draw on the same allowance, since most vendors count calls per connected user or per installed app. Twenty workflows on one Zendesk connection compete with each other and with every other integration that uses the same agent's API token.

**High concurrency** lets more runs hit the same application at once. A Business or Enterprise workspace can run many workflows in parallel, which shortens queues but concentrates calls.

**Vendor-side allocations** such as Salesforce's rolling daily API allocation or the NetSuite account's concurrency governance apply across the client's whole tenant, so a heavy data load by another team can leave Nimbus with nothing.

## Diagnosing the problem

1. Filter **Runs** to the affected workflow and status `failed`, then open a run and select the step with CONN-429. The step log records each attempt and the application's own response:

   ```text
   2026-03-04T10:15:22Z step=update_tickets attempt=1/4 CONN-429 zendesk: HTTP 429 (Retry-After: 45)
   2026-03-04T10:16:07Z step=update_tickets attempt=2/4 CONN-429 zendesk: HTTP 429 (Retry-After: 52)
   2026-03-04T10:18:07Z step=update_tickets attempt=3/4 succeeded
   ```

2. List the failed runs in the time window through the API to see how widespread the problem is: `GET /runs?status=failed&from=2026-03-04T09:00:00Z&to=2026-03-04T12:00:00Z`, then `GET /runs/{id}/steps` for each to separate CONN-429 from other errors.
3. Under **Connections**, open the connection and check **Used by**, which lists every workflow using it. Count how many of them are scheduled or triggered at the same time.
4. For each of those workflows, look for loop steps that contain an action on the same connector, and for polling triggers without a filter.
5. Ask the client whether other systems (their own scripts, another integration platform, a data warehouse sync) use the same account or app in the application.

## Error reference

| Code | Meaning | How it relates to throttling |
|---|---|---|
| CONN-429 | The third-party application throttled the connector. Nimbus backs off and retries the step. | The primary symptom. The run fails only if the last retry is throttled too. |
| WF-200 | A single step ran longer than 10 minutes and was stopped. | A batch action can hit this if the application slows its responses instead of refusing them. |
| WF-210 | The run was still running after 60 minutes and was stopped (`timed_out`). | Long waits between retries in several steps add up. |
| WF-310 | The concurrent-run limit was reached; the run waits as `queued`. | A notice, not a failure. It can be a sign that runs are piling up behind throttled ones. |
| CONN-503 | The third-party application is unavailable. | Not throttling: the application is down or erroring, and the fix is to wait for the vendor. |

When a step is throttled, Nimbus waits before each retry using the step's retry schedule (by default 3 retries, after 30 seconds, 2 minutes and 10 minutes). If the application's response says how long to wait and that is longer than the next scheduled delay, Nimbus waits the longer of the two.

## Fixes

Work through these in order; the first two usually remove the problem.

1. **Replace per-item actions with batch actions.** Collect the items into a list with a transform step and send them in one call: **Batch update contacts** in HubSpot, **Upsert records (bulk)** in Salesforce, **Update many tickets** in Zendesk. A loop is still the right tool when each item needs a different action.
2. **Filter at the trigger.** Narrow polling triggers so only relevant records start runs. For Salesforce, set the trigger's **Filter** field to a SOQL condition; for Jira Cloud, use a JQL filter on the event.
3. **Spread schedules out.** Stagger cron expressions so workflows on the same connection don't start in the same minute, for example `7 * * * *` and `37 * * * *` instead of two jobs at `0 * * * *`. See [Scheduling Workflows](nimbus-admin-scheduling-workflows.md).
4. **Separate connections.** Where the vendor counts per connected user, give heavy workflows their own connection with their own integration user.
5. **Raise the step's retries.** On the step's **Settings** tab, raise **Retries** to 5 so a short throttling episode doesn't fail the run.
6. **Add a delay inside long loops.** A **Delay** step at the end of each iteration slows the loop to a pace the application accepts.

A filtered Salesforce polling trigger in the workflow definition looks like this:

```yaml
trigger:
  connector: salesforce
  event: record_updated
  object: Opportunity
  filter: "StageName = 'Closed Won' AND LastModifiedBy.Alias != 'intsync'"
```

## Escalating to support

Escalate only after the fixes above, since support can't raise a vendor's allowance. Collect:

- the workspace id, connection id and connector;
- three or more run ids with CONN-429, and the time window in UTC;
- the application's response text from the step log, including any wait value it returned;
- the list of workflows under **Used by** on the connection, with their triggers and schedules;
- whether the client has already asked the vendor about their allocation.
