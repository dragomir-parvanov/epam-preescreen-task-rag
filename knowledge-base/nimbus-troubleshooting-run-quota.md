---
id: nimbus-troubleshooting-run-quota
title: Troubleshooting Run Quota Errors
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-13
owner: Support Engineering
---

Each Plan Tier includes a number of workflow runs per month: 5,000 on Starter, 100,000 on Business and unlimited on Enterprise. A run counts when it starts, whether it then succeeds or fails, and test runs in the builder don't count. When a workspace reaches its quota, new runs are rejected with WF-300 until the quota resets or the workspace upgrades, so workflows that the client relies on simply stop.

This reference helps a CSM confirm that WF-300 is the problem, find the workflows that used the runs, and choose between waiting, reducing usage and upgrading. How quotas work in general is in [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).

## Symptoms

- Runs under **Runs** fail immediately with WF-300 and no steps executed.
- Admins received the quota alert emails, first at 80% and then at 100% of the month's runs. Clients often miss the 80% email and notice only when workflows stop.
- **Run now** in the builder shows an error instead of starting a run; manual runs are rejected at the quota too.
- API calls to `POST /workflows/{id}/runs` and calls to inbound trigger URLs answer `403 Forbidden` with a message beginning `WF-300`.
- Test runs in the builder still work, which can make a Builder think the workflow is fine.

## Common causes

Workspaces rarely run out because of steady growth. Usually one or two workflows account for most of the month's runs:

- **Triggers without a filter.** A connector event trigger starts a run for every event the app sends. A HubSpot or Jira Cloud trigger on "record updated" fires for every field change, including changes the workflow then ignores in its first condition step. Every one of those runs counts.
- **One run per record.** A sender that calls an inbound trigger once per order line, or a polling trigger that starts a run for each new row, uses one run per item where one run per batch would do.
- **Short schedule intervals.** A workflow scheduled every 5 minutes starts 8,928 runs in a 31-day month even when it usually finds nothing to do. On its own, that is more than the Starter quota.
- **Re-run failures.** Running a failed run again, by hand or from the client's own scripts, starts a new run and counts again. Step retries are different: they happen inside the same run and don't count as extra runs.
- **Runaway loops.** A workflow whose HTTP Request step calls its own trigger URL, or two workflows that trigger each other, can use thousands of runs in an hour.

## Diagnosing the problem

1. Open **Settings > Usage**. The usage dashboard shows runs used this month against the quota, a daily chart, and **Runs by workflow**, which lists the workflows that started the most runs. See [Usage Dashboard and Quota Alerts](nimbus-tier-usage-dashboard.md).
2. Read the same figures from the API, which is useful for clients who monitor usage themselves:

```http
GET /workspace/usage HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{"period_start": "2026-04-01T00:00:00Z", "period_end": "2026-04-30T23:59:59Z", "runs": {"used": 5000, "included": 5000}, "seats": {"used": 8}, "active_connectors": {"used": 4}}
```

3. If the client wants the breakdown over a custom window, count runs per workflow from `GET /runs`, following `next_cursor` until it is null:

```python
from collections import Counter

import requests

API = "https://api.nimbus.omnicorp.example"
HEADERS = {"Authorization": "Bearer <api-key>"}

counts = Counter()
params = {"from": "2026-04-01T00:00:00Z", "limit": 100}
while True:
    page = requests.get(f"{API}/runs", headers=HEADERS, params=params, timeout=30).json()
    counts.update(run["workflow_id"] for run in page["data"])
    if page["next_cursor"] is None:
        break
    params["cursor"] = page["next_cursor"]

for workflow_id, runs in counts.most_common(10):
    print(workflow_id, runs)
```

4. Open the top workflows and look at their trigger type and their first steps. A condition step that discards most runs straight away is the clearest sign that the trigger needs a filter.

## Error reference

| Code | Meaning | Is it the quota? |
|---|---|---|
| WF-300 | The workspace has used its monthly workflow runs; the run was rejected. | Yes |
| WF-500 | An internal Nimbus error; the run can be retried. | No; it counts as a run like any other failure. |
| 403 `forbidden` with `WF-300` | An API call or inbound trigger call was refused because of the quota. | Yes |

## Fixes

### Reducing runs

1. **Filter at the trigger.** Move the condition that discards irrelevant events from the first step into the trigger's **Filter** settings. Filtered events never start a run, so they don't count. For database polling triggers, narrow the query itself, for example `WHERE status = 'ready' AND updated_at > :last_checked`.
2. **Batch.** Replace one-run-per-record designs with a scheduled run that collects the pending records and processes them with a loop step. A sender that can't batch can write to a queue or a file that a scheduled workflow reads.
3. **Lengthen intervals.** A schedule every 15 minutes uses a third of the runs of one every 5 minutes.
4. **Deactivate what isn't needed.** Old test or duplicate workflows still use runs while they are active.

Builders can keep testing in the builder while they make these changes, because test runs don't count.

### Getting runs back now

The quota resets at 00:00 UTC on the 1st of each month. If the client can't wait, an Admin can upgrade the Plan Tier under **Settings > Plan**; upgrades take effect immediately and the new quota applies at once. Runs rejected with WF-300 are not queued or replayed after the reset or the upgrade. Once runs are available again, start the important missed runs with **Run now** or `POST /workflows/{id}/runs`, and ask the senders of inbound calls to send theirs again.

## Escalating to support

Escalate when WF-300 appears although **Settings > Usage** shows the workspace below its quota, or when the count includes runs the client is sure didn't happen. Collect:

- the workspace id (`ws_...`), its Plan Tier and the usage figures from `GET /workspace/usage`;
- the time the 100% alert email arrived;
- the ids of a few WF-300 runs and of the top workflows from **Runs by workflow**;
- any runs the client believes were counted wrongly, for example test runs.
