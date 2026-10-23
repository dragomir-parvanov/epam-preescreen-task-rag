---
id: nimbus-v2-api-runs
title: Runs API (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-02-24
owner: Platform API Team
---

The Runs API starts workflows on demand and reads the results of runs, whatever started them: a schedule, an inbound webhook, a connector event or a person clicking **Run now**. Clients typically use it to start a workflow from their own scheduler or ERP and then poll until the run finishes, or to pull failed runs into their monitoring.

This is the legacy platform's Runs API. It has no retry endpoint and no step-level log endpoint, and run history is kept for 30 days. Authentication, base URL and the plain-message error format are the same as for the [Workflows API (v2)](nimbus-v2-api-workflows.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/workflows/{id}/runs` | Start a run of an active workflow, optionally with input. |
| `GET` | `/runs` | List runs in the workspace, newest first, one page at a time. |
| `GET` | `/runs/{id}` | Read one run, including the status of each step. |
| `POST` | `/runs/{id}/cancel` | Cancel a run that is `queued` or `running`. |

### Starting a run

`POST /workflows/{id}/runs` takes an optional JSON body `{"input": {...}}`. The object becomes the run's trigger data, so a step reads `input.order_id` as `{{trigger.body.order_id}}`, exactly as if the data had arrived on the workflow's inbound webhook. The call answers `202 Accepted` with the new run in status `queued`; the run then proceeds without the caller.

The workflow must be active. The endpoint doesn't accept an `Idempotency-Key` header, so a request that timed out may still have started a run: list the workflow's recent runs before sending it again.

### Re-running a failed run

There is no retry endpoint. To run the same work again, read the failed run with `GET /runs/{id}`, take its `input`, and send it to `POST /workflows/{workflow_id}/runs`. The result is a new run with its own id, starting from the first step; steps that succeeded the first time run again, so check that the workflow's actions are safe to repeat (for example, that a create step won't produce a duplicate record).

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Run id, prefixed `run_`. |
| `workflow_id` | string | The workflow that ran (`wf_`). |
| `status` | string | `queued`, `running`, `succeeded`, `failed`, `cancelled` or `timed_out`. |
| `trigger_type` | string | `schedule`, `webhook`, `connector_event`, `manual` (console) or `api`. |
| `input` | object or null | The trigger data the run started with. |
| `started_at` | string or null | When the first step began (ISO 8601, UTC); `null` while queued. |
| `finished_at` | string or null | When the run ended; `null` until then. |
| `error` | string or null | For a failed run, the message from the step that failed. |
| `steps` | array | One entry per step: `key`, `status`, `started_at`, `finished_at` and `error`. Present on `GET /runs/{id}` only. |

Step entries carry the step's status and error message but not its full input and output. Detailed step output is visible in the console's run view for as long as the run is kept.

## Example request and response

Start a stock-sync workflow for a single warehouse, then read the result:

```http
POST /workflows/wf_9Hs4mC2r/runs HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"input": {"warehouse": "LEEDS-02", "full_resync": false}}
```

```http
GET /runs/run_6Kd1wQ8z HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "id": "run_6Kd1wQ8z",
  "workflow_id": "wf_9Hs4mC2r",
  "status": "failed",
  "trigger_type": "api",
  "input": {"warehouse": "LEEDS-02", "full_resync": false},
  "started_at": "2025-02-20T07:41:13Z",
  "finished_at": "2025-02-20T07:41:58Z",
  "error": "NetSuite rejected the request: insufficient permission for Inventory Adjustment",
  "steps": [
    {"key": "read_stock", "status": "succeeded", "started_at": "2025-02-20T07:41:13Z", "finished_at": "2025-02-20T07:41:40Z", "error": null},
    {"key": "post_adjustment", "status": "failed", "started_at": "2025-02-20T07:41:40Z", "finished_at": "2025-02-20T07:41:58Z", "error": "insufficient permission for Inventory Adjustment"}
  ]
}
```

The `error` text comes from the third-party app. Here the NetSuite role behind the connection needs the Inventory Adjustment permission; once a NetSuite administrator grants it, re-run with the same `input` as described above.

## Filtering and pagination

Run history is kept for 30 days. `GET /runs` never returns older runs, and `GET /runs/{id}` for a run older than that answers `404`. Clients that need a longer record must copy runs out of Nimbus before they age out.

The list is page-based: `page` starts at 1, `per_page` defaults to 50 and can be at most 100, and the response carries `total`. Filters:

| Parameter | Effect |
|---|---|
| `workflow_id` | Runs of one workflow. |
| `status` | One status, e.g. `failed`. |
| `trigger_type` | How the run was started. |
| `from`, `to` | `started_at` window, ISO 8601 in UTC. |

A nightly job that archives the previous day's failed runs:

1. Call `GET /runs?status=failed&from=2025-02-19T00:00:00Z&to=2025-02-20T00:00:00Z&per_page=100&page=1`.
2. Divide `total` by 100 and round up to get the number of pages.
3. Fetch each remaining page by increasing `page`.
4. For each run in `data`, call `GET /runs/{id}` to get its `steps`, and store the result in the client's own system.

Because the window is in the past, no new runs join it while the job pages through, so the page positions stay stable.

## Errors

Errors are a plain message with the HTTP status, such as `{"error": "run not found"}`. There are no error codes.

| HTTP status | Typical message | Why |
|---|---|---|
| 400 | `input must be a JSON object` | The body isn't JSON, or `input` is an array or a string. |
| 401 | `invalid API key` | The key is missing or has been deleted. |
| 404 | `workflow not found` / `run not found` | Unknown id, or the run is older than 30 days and has been removed. |
| 409 | `workflow is inactive` | A run was started for an inactive workflow; activate it first. |
| 409 | `run is not in progress` | `cancel` was sent for a run that has already finished. |
| 429 | `rate limit exceeded` | Too many requests; wait for the seconds in `Retry-After`. Polling loops are the usual cause. |
| 500 | `internal error` | An internal Nimbus error. Retry `GET` calls; list recent runs before retrying a start. |

When polling a run, wait a few seconds between calls and stop as soon as `status` is `succeeded`, `failed`, `cancelled` or `timed_out`. The [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md) gives the workspace's request limit.
