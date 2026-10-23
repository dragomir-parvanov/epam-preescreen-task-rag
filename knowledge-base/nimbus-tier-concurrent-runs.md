---
id: nimbus-tier-concurrent-runs
title: Concurrent Run Limits
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-17
owner: Product Operations
---

Since release 3.8.0 (2026-08-03), each workspace has a ceiling on how many workflow runs can be executing at the same moment. Runs that start while the workspace is at that ceiling aren't rejected: they wait in a queue with status `queued` and start, oldest first, as running ones finish. The concurrent-run limit is about pace, not volume; the number of runs a workspace can start each month is set separately by the [monthly run quota](nimbus-tier-workflow-run-quotas.md).

Clients usually notice the limit when a large import or a busy event source makes runs sit in `queued` for longer than they expect. This guide explains how the queue behaves, how long-running runs affect it, and how to design workflows that stay comfortably under the ceiling.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Concurrent runs | 5 | 25 | 100 |
| Extra runs wait as `queued` | Yes | Yes | Yes |
| WF-310 notice on queued runs | Yes | Yes | Yes |
| Run timeout (WF-210) | 60 minutes | 60 minutes | 60 minutes |

Unlike most Enterprise entitlements, this one is not unlimited: Enterprise workspaces have a fixed ceiling of 100.

## How it works

A run holds a concurrency slot only while its status is `running`. Every other status is free:

| Run status | Holds a slot |
|---|---|
| `queued` | No; waiting for a slot |
| `running` | Yes |
| `waiting_for_approval` | No; the slot is released while an approver decides |
| `succeeded`, `failed`, `cancelled`, `timed_out` | No |

When a scheduled firing, a connector event, an inbound webhook or a manual start arrives and all slots are taken, the run is created with status `queued` and the notice WF-310 in its run history. WF-310 is a notice, not a failure: the run will start, and nothing has to be retried. Inbound webhook triggers still answer `202 Accepted` with the run id straight away, so callers can't tell from the response whether the run is queued.

Queued runs start in the order they were created, across all workflows in the workspace. A busy workflow can therefore delay a quiet one, because there is one queue per workspace, not one per workflow. A run resumed after approval goes to the back of the queue if no slot is free.

Two more rules matter when explaining delays to a client:

- A run counts against the monthly quota when it starts, so a run that is still `queued` hasn't used a run yet, and a queued run that is cancelled never does.
- The 60-minute run timeout starts when the run moves to `running`. Time spent in the queue doesn't count.

### Long-running runs

A run that is slow, not stuck, still holds its slot until it ends. Only the run timeout frees it: a run still running after 60 minutes is stopped with status `timed_out` and WF-210. A single slow step fails with WF-200 after 10 minutes, and step retries happen inside the same run, so a step retried three times keeps its run's slot for the whole back-off of 30 seconds, 2 minutes and 10 minutes.

Delay steps keep the run in `running` too. A workflow that waits 45 minutes in a delay step holds a slot for those 45 minutes, which on Starter is a fifth of the workspace's capacity.

## Turning it on

The limit is always on. To see whether a client is hitting it and where the pressure comes from:

1. Open **Runs** and filter **Status** to **Queued**. If the list is empty most of the time, the limit isn't affecting the client.
2. Filter run history by notice **WF-310** over the last week, and group by workflow to see which workflows queue most.
3. Go to **Settings > Usage** and read the **Concurrent runs** card, which shows runs in progress, runs queued and the peak for the current month.
4. Open the busiest workflows and look for delay steps, slow polling queries and schedules that all fire on the hour.
5. Cancel queued runs that are no longer wanted with **Cancel** in run history, so they don't delay the rest.

The same view through the API, for workspaces with API access:

```bash
curl -s "https://api.nimbus.omnicorp.example/runs?status=queued&limit=100" \
  -H "Authorization: Bearer <api-key>"

curl -s -X POST "https://api.nimbus.omnicorp.example/runs/run_6Vb1Kx/cancel" \
  -H "Authorization: Bearer <api-key>"
```

`GET /workspace/usage` returns `"concurrent_runs": { "limit": 25, "running": 25, "queued": 14 }` alongside the other usage counters.

### Designing workflows to stay under the limit

Most queueing comes from many short runs starting together. These changes help most, in order of effect:

1. **Batch instead of fanning out.** One run that loops over 500 records uses one slot; 500 runs triggered one per record compete for the same slots.
2. **Stagger schedules.** Twenty workflows scheduled with `0 * * * *` all fire at the top of the hour. Spread them out:

   ```cron
   5 * * * *     # invoice sync
   20 * * * *    # CRM contact refresh
   35 * * * *    # ticket digest
   ```

3. **Replace long delay steps** with a second workflow on a schedule, so no run sits in `running` while it waits.
4. **Move sign-off waits into approval steps**, which release the slot while the run waits.
5. **Keep runs well under 60 minutes.** A run that regularly nears the timeout is a sign it should be split.

## Limits

| Item | Starter | Business | Enterprise |
|---|---|---|---|
| Runs executing at once | 5 | 25 | 100 |
| Queued runs | No cap | No cap | No cap |
| Queue order | Oldest first, workspace-wide | Oldest first, workspace-wide | Oldest first, workspace-wide |
| Run timeout | 60 minutes from start of running | Same | Same |
| Step timeout | 10 minutes (WF-200) | Same | Same |

Test runs in the builder don't take a slot and are never queued, so Builders can keep testing when production runs are queueing.

## When the Plan Tier changes

An upgrade takes effect immediately. The extra slots are available at once, and queued runs start straight away in their original order until the new ceiling is reached.

A downgrade takes effect at the end of the current billing period. Runs already executing when it takes effect are never stopped to fit the lower ceiling; they finish normally. New runs queue until the number running drops below the new limit. A workspace moving from Business to Starter should check the **Concurrent runs** peak on **Settings > Usage** beforehand: if the peak is well above 5, apply the design changes above before the date, or queues will grow during busy hours.
