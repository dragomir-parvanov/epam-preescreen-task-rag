---
id: nimbus-api-runs
title: Runs API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-10
owner: Platform API Team
---

A run is one execution of a workflow, from its trigger to its last step. The Runs API starts runs on demand with an input payload, lists and filters the run history, reads a single run, and cancels or retries runs. It returns the same records a CSM sees under **Runs** in the admin console.

Requests are authenticated with an API key in the `Authorization: Bearer <api-key>` header and act with Admin permissions. Run history, including inputs, outputs and step logs, is kept for 90 days on every Plan Tier; older runs are no longer returned. The step-by-step detail of a run has its own reference, the [Run Steps and Logs API](nimbus-api-run-steps.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/workflows/{id}/runs` | Start a manual run of a workflow, with an optional `input` object. |
| `GET` | `/runs` | List runs across the workspace, newest first. |
| `GET` | `/runs/{id}` | Read one run, including its status, timing and error. |
| `POST` | `/runs/{id}/cancel` | Cancel a run that hasn't finished yet. |
| `POST` | `/runs/{id}/retry` | Start a new run with the same input as a finished run (since 3.8). |
| `GET` | `/runs/{id}/steps` | Read each step's status, attempts and logs. |

### Starting a run

`POST /workflows/{id}/runs` is the API form of **Run now** in the builder. The body's `input` object is handed to the workflow as its trigger payload, so a step reads a value with `{{trigger.body.<field>}}`. Nimbus answers `202 Accepted` with the new run in status `queued`; poll `GET /runs/{id}` or subscribe to the `workflow.run.completed` and `workflow.run.failed` webhook events to learn the outcome.

Send an `Idempotency-Key` header on every start. If the same key arrives again within 24 hours, Nimbus returns the run it created the first time instead of starting a second one, which makes it safe to retry a request that timed out on the client's side. Reusing a key with a different body is rejected with `409 conflict`. See [API Error Format and Idempotency](nimbus-api-error-format.md).

A run counts against the workspace's monthly workflow runs when it starts. Once the quota is used up, manual runs are rejected as well as scheduled and event-triggered ones; see [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).

### Cancelling and retrying

`POST /runs/{id}/cancel` works on runs that are `queued`, `running` or `waiting_for_approval`. The step in progress is allowed to finish its current call, no further steps start, and the run ends as `cancelled`. Cancelling a run that has already finished returns `409 conflict`.

`POST /runs/{id}/retry`, added in 3.8, accepts a run that ended as `failed`, `timed_out` or `cancelled`. It starts a fresh run from the first step, with the original run's input on the workflow's currently published version, and sets `retry_of` on the new run to the original's id. A retry is a new run: it counts towards the monthly quota and gets its own `run_` id. It is not the same as the automatic step retries described in the Run Steps reference.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | The run id, prefixed `run_`. |
| `workflow_id` | string | The `wf_` id of the workflow that ran. |
| `workflow_version` | integer | The published version that was executed. |
| `environment` | string | `development` or `production`. |
| `status` | string | One of `queued`, `running`, `waiting_for_approval`, `succeeded`, `failed`, `cancelled`, `timed_out`. |
| `trigger_type` | string | `schedule`, `webhook`, `connector_event` or `manual`. |
| `started_by` | string or null | The `usr_` or `key_` id that started a manual run; null otherwise. |
| `input` | object | The trigger payload, as the first step received it. |
| `queued_reason` | string or null | `WF-310` while the run waits for a free concurrent-run slot. |
| `error` | object or null | `code` and `message` of the error that ended the run, e.g. `WF-210` or `CONN-401`. |
| `retry_of` | string or null | The `run_` id this run retries. |
| `created_at` | string | When the run was accepted. |
| `started_at`, `finished_at` | string or null | Start and end of execution. |
| `duration_ms` | integer or null | Execution time, once finished. |

A run still `running` after 60 minutes is stopped and ends as `timed_out` with `WF-210`. A run held by the concurrent-run limit stays `queued` with `queued_reason: "WF-310"`; that is a notice, not a failure, and the run starts on its own when a slot frees up.

## Example request and response

```http
POST /workflows/wf_7730/runs HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: crm-sync-2026-08-07T0900

{
  "input": {
    "account_id": "0015g00000QxT2A",
    "requested_by": "finance-portal"
  }
}
```

```json
{
  "id": "run_55120944",
  "workflow_id": "wf_7730",
  "workflow_version": 14,
  "environment": "production",
  "status": "queued",
  "trigger_type": "manual",
  "started_by": "key_3307",
  "input": {"account_id": "0015g00000QxT2A", "requested_by": "finance-portal"},
  "queued_reason": null,
  "error": null,
  "retry_of": null,
  "created_at": "2026-08-07T09:00:02Z",
  "started_at": null,
  "finished_at": null,
  "duration_ms": null
}
```

A few seconds later, `GET /runs/run_55120944` shows `"status": "succeeded"` with `started_at`, `finished_at` and `duration_ms` filled in.

## Filtering and pagination

`GET /runs` takes any combination of these filters:

- `workflow_id`: runs of one workflow.
- `status`: one status, or several separated by commas, such as `failed,timed_out`.
- `trigger_type`: `schedule`, `webhook`, `connector_event` or `manual`.
- `environment`: `development` or `production`.
- `from` and `to`: ISO 8601 timestamps compared with `created_at`; `from` is inclusive and `to` exclusive.

Lists are cursor-based, with `limit` (default 25, maximum 100) and `cursor`. To export every failed run of one workflow for last week:

1. Call `GET /runs?workflow_id=wf_7730&status=failed,timed_out&from=2026-07-27T00:00:00Z&to=2026-08-03T00:00:00Z&limit=100`.
2. Process the runs in `data`.
3. While `next_cursor` is not null, repeat the same call with `cursor=<next_cursor>`.
4. Stop when `next_cursor` comes back null.

Test runs from the builder are not listed and don't count towards the quota. For the console view of the same history, see [Searching and Exporting Run History](nimbus-admin-run-history.md).

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `input` isn't a JSON object, or a filter value is unknown. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 403 | `forbidden` | The monthly workflow runs are used up; the message carries `WF-300`. |
| 404 | `not_found` | No such workflow or run, or the run is older than the 90-day run history. |
| 409 | `conflict` | Cancel on a finished run, retry on a run that succeeded or is still in progress, a reused `Idempotency-Key` with a different body, or a start on an inactive workflow. |
| 429 | `rate_limited` | Too many API calls; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | A Nimbus fault. Repeat the start with the same `Idempotency-Key`. |
