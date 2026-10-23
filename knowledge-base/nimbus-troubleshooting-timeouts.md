---
id: nimbus-troubleshooting-timeouts
title: Troubleshooting Step and Run Timeouts
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2025-12-22
owner: Support Engineering
---

Nimbus enforces two time limits on workflows. A single step that takes longer than 10 minutes is stopped and fails with WF-200. A whole run that is still running after 60 minutes is stopped with the status `timed_out` and the code WF-210. Both limits are the same on every Plan Tier and can't be raised for a workspace, so the fix is always to make the work faster or to divide it up.

Timeouts tend to appear gradually: a workflow that took 4 minutes at launch takes 40 a year later because the table it reads has grown. This reference helps a CSM find the slow part and recommend a change to the workflow's design.

## Symptoms

- A step fails with WF-200 after almost exactly 10 minutes, often a database query, a file transfer or a large export from a third-party app.
- A run ends with the status `timed_out` rather than `failed`, with WF-210 on whichever step was running at the 60-minute mark.
- Runs that used to finish comfortably now finish close to the limit, and some time out, especially at month end or after a data import.
- The `workflow.run.failed` event and failure alerts arrive about an hour after the run started.

## Common causes

**Slow queries.** Database steps and polling triggers on PostgreSQL, MySQL, Microsoft SQL Server and Snowflake run whatever query the Builder wrote. A query that filters on an unindexed column, selects every column, or sorts a whole table becomes slower as the data grows, until it passes 10 minutes. On Snowflake, a small or suspended warehouse adds its own delay.

**Large files.** A single file passed between steps can be up to 100 MB. Moving a file near that size from a slow SFTP server, or converting a large CSV in a transform step, can take most of the 10 minutes on its own.

**Loops over long lists.** Each step inside a loop is timed per iteration, so an individual call rarely reaches WF-200. The loop's total time counts towards the run, though: 4,000 iterations of a step that takes one second, plus the API call to fetch the next record, easily pass 60 minutes.

**Retries eating the run's time.** A connector step that fails is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. If the step keeps hitting WF-200, four 10-minute attempts and the waits between them take 52.5 minutes, so a run that spent more than 7.5 minutes on earlier steps reaches WF-210 before the last attempt finishes. Throttling makes this worse, because Nimbus backs off and retries steps that the third-party app answers with CONN-429.

**What doesn't count.** The 60 minutes measure time in the `running` status only. A run waiting in `waiting_for_approval` for an approval step isn't running, so time spent waiting for an approver doesn't count towards the 60 minutes.

## Diagnosing the problem

1. Open the run under **Runs**. The step timeline shows each step's duration and, for loops, the number of iterations completed; the longest bar is usually the answer.
2. For several runs, compare durations through the API. Each step lists its attempts with their start and finish times:

```http
GET /runs/run_2PL6W0TK/steps HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{"data": [{"key": "load_orders", "type": "connector", "status": "failed", "attempts": 4, "started_at": "2025-12-15T05:00:04Z", "finished_at": "2025-12-15T05:52:41Z", "error": {"code": "WF-200", "message": "Step ran longer than 10 minutes and was stopped."}}], "next_cursor": null}
```

3. For a slow database step, copy the query from the step's settings and ask the client's database administrator to run it with the execution plan:

```sql
EXPLAIN ANALYZE
SELECT order_id, customer_id, total, updated_at
FROM orders
WHERE updated_at > '2025-12-14T05:00:00Z'
ORDER BY updated_at;
```

A sequential scan over the whole table points to a missing index on `updated_at`.

4. For file steps, check the file's `size_bytes` on the step's **Input** tab.
5. For loops, divide the loop's duration by its iteration count to get the time per item, and multiply by the largest list the workflow has to handle.

## Error reference

| Code | Limit | Meaning | Run status |
|---|---|---|---|
| WF-200 | 10 minutes per step | A step ran longer than 10 minutes and was stopped. The step is retried if it has retries left. | `failed` once retries are used up |
| WF-210 | 60 minutes per run | The run was still running after 60 minutes and was stopped. | `timed_out` |
| CONN-429 | None | The third-party app throttled the connector; Nimbus backs off and retries the step, which lengthens it. | Unchanged |

## Fixes

### Making steps faster

- Index the columns that queries filter and sort on, select only the columns the workflow uses, and read incrementally from a watermark (the last `updated_at` processed) instead of re-reading the table.
- Split large files at the source, or compress them, and stream them from connector to connector rather than transforming them in a step.
- For steps that time out rather than fail quickly, set **Settings > Retries** to 0 or 1, so a stuck step doesn't use up the run's 60 minutes. Retries are configurable from 0 to 5 per step.

### Splitting the work

When a run does more than an hour's work, give it less to do:

1. Limit each run to a batch, for example `LIMIT 500` in the query, and store the watermark at the end of the run.
2. Schedule the workflow often enough that the batches keep up; see [Scheduling Workflows](nimbus-admin-scheduling-workflows.md).
3. Alternatively, have a parent workflow divide the list and start a child workflow per chunk with `POST /workflows/{id}/runs`.

Each extra run counts against the monthly workflow runs, so check the client's quota before recommending many small runs; see [Troubleshooting Run Quota Errors](nimbus-troubleshooting-run-quota.md).

## Escalating to support

Escalate when a step reaches WF-200 although the same query or transfer completes well within 10 minutes outside Nimbus, or when a run reaches WF-210 although its steps add up to much less than 60 minutes. Collect:

- the run id (`run_...`), the workflow id (`wf_...`) and the key of the step that timed out;
- the step durations from `GET /runs/{id}/steps`;
- the query text and its execution plan, or the file size, or the loop's iteration count;
- the time the same work takes when run outside Nimbus.
