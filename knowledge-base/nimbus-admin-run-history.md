---
id: nimbus-admin-run-history
title: Searching and Exporting Run History
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-12-08
owner: Workspace Administration Team
---

Every workflow run leaves a record on the **Runs** page: when it started, what triggered it, which version it ran, and the input, output and log of each step. CSMs most often send clients here when a run has failed and they need the exact error, or when a client's auditors want a list of what an integration did over a period.

This guide explains how to filter run history, read a single run, export a list as CSV, query runs through the API and retry a failed run.

## Before you begin

Run history is available on every Plan Tier. What a user can do with it depends on their role:

| Action | Viewer | Builder | Admin |
|---|---|---|---|
| Search and open runs, read step input, output and logs | Yes | Yes | Yes |
| Export the run list as CSV | Yes | Yes | Yes |
| Cancel a queued or running run | No | Yes | Yes |
| Retry a failed run | No | Yes | Yes |

Querying runs through the API needs an API key, which only an Admin can create; see [Creating and Rotating API Keys](nimbus-admin-api-keys.md). Retrying from the API needs release 3.8.0 or later, which every v3 workspace already has.

## How it works

A run is created as soon as a trigger fires, a manual run starts or a run is started with `POST /workflows/{id}/runs`. It moves through these statuses:

- `queued`: waiting to start, for example because the concurrent-run limit was reached (notice WF-310).
- `running`: executing steps.
- `waiting_for_approval`: paused at an approval step.
- `succeeded`, `failed`, `cancelled` or `timed_out`: finished.

Run history keeps each run's inputs, outputs and step logs for 90 days on every Plan Tier. After that the run and everything in it is deleted, and neither the console nor the API can return it. Clients who need a longer record should export regularly, as described below.

Each run's detail page has a timeline of its steps. Opening a step shows three tabs: **Input** (the resolved values after expressions were evaluated), **Output** (what the connector or transform returned) and **Log** (timestamps, retries and the error code if the step failed). Secrets are masked in all three tabs, and connection credentials are never shown.

Retrying a failed run creates a new run that starts again from the first step with the original trigger input, so steps that had already succeeded run again. The new run has its own id and links back to the original under **Retry of**. It runs on the workflow's currently published version, not the version the original run used, and counts towards the monthly run quota like any other run.

## Step-by-step

To find and export runs in the console:

1. Open **Runs** from the main menu.
2. Use the filter bar: **Workflow** (one or several), **Status**, and **Started** with a date range. Dates are shown in the workspace time zone.
3. Click a run to open its timeline, then click a step to read its input, output and log.
4. To export, go back to the list with your filters set and click **Export CSV**. The file contains one row per run in the filtered list, with the columns `run_id`, `workflow_id`, `workflow_name`, `version`, `status`, `trigger_type`, `started_at`, `finished_at`, `duration_ms` and `error_code`. Step input and output aren't included.
5. To retry, open a run with status `failed` and click **Retry**. Confirm the dialog.

The API returns the same data with richer filters. This example lists failed runs of one workflow during a week, 100 per page:

```http
GET /runs?workflow_id=wf_5cTz81Lm&status=failed&from=2025-11-24T00:00:00Z&to=2025-12-01T00:00:00Z&limit=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "id": "run_q7Rw2bX9",
      "workflow_id": "wf_5cTz81Lm",
      "version": 23,
      "status": "failed",
      "trigger_type": "schedule",
      "started_at": "2025-11-27T06:00:02Z",
      "finished_at": "2025-11-27T06:00:41Z",
      "error_code": "CONN-404"
    }
  ],
  "next_cursor": "c2VxPTEwMQ"
}
```

Pass `next_cursor` back as `cursor` until it comes back `null`. Fetch a run's step detail with `GET /runs/{id}/steps`, and retry it with `POST /runs/{id}/retry`.

### Scheduled exports

For records beyond the retention window, build a small workflow with a schedule trigger that calls `GET /runs` for the previous day through the [HTTP Request Connector](nimbus-connector-http-request.md) and writes the result to the client's storage, for example with the [Amazon S3 Connector](nimbus-connector-amazon-s3.md).

## Verifying the change

Exports and retries are easy to confirm:

- Open the CSV and check the row count against the count shown above the filtered list in **Runs**. If they differ, the list probably changed between loading and exporting; refresh and export again.
- After a retry, the original run's page shows a **Retried as** link, and the new run appears at the top of **Runs** with status `queued` or `running`. Open it and check that the timeline begins at the first step.
- From the API, `GET /runs/{id}` for the new run returns `"retry_of": "run_..."` with the original id.

## Troubleshooting

| Problem | Explanation and fix |
|---|---|
| A run the client mentions can't be found | It is older than the retention window, or the filters exclude it. Clear **Status** and widen **Started**. Runs past the window can't be recovered. |
| **Retry** is greyed out | The run isn't `failed`, `timed_out` or `cancelled`, or the user is a Viewer. Runs that are still in progress or `succeeded` can't be retried. |
| The retried run fails at the same step | The underlying cause is still there. Read the step's **Log**: CONN-401 needs the connection reconnected, CONN-403 needs the permission granted in the third-party app, WF-400 needs the mapping fixed. |
| A retry is rejected with WF-300 | The workspace has used its monthly runs; retries count like any other run. See [Configuring Failure Notifications](nimbus-admin-failure-notifications.md) for the quota alert emails. |
| The CSV has no step output | By design. Use `GET /runs/{id}/steps` for step-level data. |
| Times in the CSV don't match the console | The CSV uses UTC (ISO 8601); the console uses the workspace time zone. |
