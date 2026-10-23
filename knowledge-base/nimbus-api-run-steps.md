---
id: nimbus-api-run-steps
title: Run Steps and Logs API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-27
owner: Platform API Team
---

When a run fails, the run object only says which error ended it. The steps endpoint shows the whole path: every step in the order it ran, how many attempts each one took, how long each attempt lasted, the WF- or CONN- error code of each failure, and the start of each step's input and output. With `include=logs` it also returns the step logs that Builders see in the run detail panel under **Runs**.

The endpoint is read-only and authenticated like the rest of the API, with `Authorization: Bearer <api-key>`. Step data belongs to the run, so it is kept exactly as long as the run history: 90 days on every Plan Tier. To find the run in the first place, use the [Runs API](nimbus-api-runs.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs/{id}/steps` | List the steps of one run in execution order, with attempts, timing, errors and truncated payloads. |
| `GET` | `/runs/{id}` | Read the run itself (status, trigger, overall error); documented in the Runs API. |

There are no write operations on steps. A step can't be re-run on its own; the whole run is started again instead.

### Reading step logs

Add `include=logs` to get each step's log lines, oldest first. A log line has `at`, `level` (`debug`, `info`, `warn` or `error`) and `message`. Connector actions log the outbound call they made (method, the third-party path and the response status), transforms log any expression that resolved to empty, and approval steps log who was asked and who decided. Values that came from `{{secrets.<NAME>}}` are replaced with `[redacted]` in both logs and payloads, so a log can be pasted into a support ticket without leaking a credential.

Logs make the response much larger. Fetch them for the failed step only by combining `include=logs` with `step_key`, for example `GET /runs/run_55120931/steps?step_key=update_invoice&include=logs`.

## Object fields

Each element of `data` is a step execution:

| Field | Type | Description |
|---|---|---|
| `key` | string | The step key from the workflow definition, as used in `{{steps.<step-key>.output.<field>}}`. |
| `name` | string | The label shown in the builder. |
| `position` | integer | Order in the run, starting at 1. |
| `type` | string | `action`, `transform`, `condition`, `loop`, `delay` or `approval`. |
| `connector` | string or null | For action steps, the connector slug, e.g. `netsuite`. |
| `connection_id` | string or null | The `con_` id the step used. |
| `status` | string | `pending`, `running`, `succeeded`, `failed`, `skipped`, `waiting_for_approval` or `cancelled`. |
| `max_retries` | integer | Retries configured on the step, 0 to 5; 3 unless changed. |
| `attempts` | array | One entry per attempt: `number`, `started_at`, `finished_at`, `duration_ms`, `error`. |
| `error` | object or null | `code` and `message` of the final failure. |
| `input`, `output` | object | The step's resolved input and its output, cut at 64 KB each. |
| `input_truncated`, `output_truncated` | boolean | True when the payload was cut. |
| `started_at`, `finished_at` | string or null | First attempt start and last attempt end. |

A step skipped by a condition branch has status `skipped` and no attempts. A loop step appears once, with `output.iterations` giving the number of items it processed.

## Example request and response

```http
GET /runs/run_55120931/steps HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Accept: application/json
```

```json
{
  "data": [
    {
      "key": "fetch_order", "name": "Get order", "position": 1, "type": "action",
      "connector": "netsuite", "connection_id": "con_6120", "status": "succeeded",
      "max_retries": 3,
      "attempts": [{"number": 1, "started_at": "2026-04-21T06:00:04Z", "finished_at": "2026-04-21T06:00:05Z", "duration_ms": 1180, "error": null}],
      "error": null,
      "input": {"internalId": "88214"}, "input_truncated": false,
      "output": {"tranId": "SO-10422", "total": 1840.5}, "output_truncated": false,
      "started_at": "2026-04-21T06:00:04Z", "finished_at": "2026-04-21T06:00:05Z"
    },
    {
      "key": "update_invoice", "name": "Update invoice", "position": 2, "type": "action",
      "connector": "netsuite", "connection_id": "con_6120", "status": "failed",
      "max_retries": 3,
      "attempts": [
        {"number": 1, "started_at": "2026-04-21T06:00:05Z", "finished_at": "2026-04-21T06:00:06Z", "duration_ms": 640, "error": {"code": "CONN-403", "message": "Role lacks the Invoice edit permission"}},
        {"number": 2, "started_at": "2026-04-21T06:00:36Z", "finished_at": "2026-04-21T06:00:37Z", "duration_ms": 610, "error": {"code": "CONN-403", "message": "Role lacks the Invoice edit permission"}},
        {"number": 3, "started_at": "2026-04-21T06:02:37Z", "finished_at": "2026-04-21T06:02:38Z", "duration_ms": 598, "error": {"code": "CONN-403", "message": "Role lacks the Invoice edit permission"}},
        {"number": 4, "started_at": "2026-04-21T06:12:38Z", "finished_at": "2026-04-21T06:12:39Z", "duration_ms": 603, "error": {"code": "CONN-403", "message": "Role lacks the Invoice edit permission"}}
      ],
      "error": {"code": "CONN-403", "message": "Role lacks the Invoice edit permission"},
      "input": {"internalId": "88214", "memo": "Synced by Nimbus"}, "input_truncated": false,
      "output": {}, "output_truncated": false,
      "started_at": "2026-04-21T06:00:05Z", "finished_at": "2026-04-21T06:12:39Z"
    }
  ],
  "next_cursor": null
}
```

The four attempts show the default retry schedule at work: the first try, then retries after 30 seconds, 2 minutes and 10 minutes. When the last retry failed, the run failed. Here the fix is on the client's side, granting the NetSuite role used by the connection permission to edit invoices, not in Nimbus.

## Filtering and pagination

| Parameter | Effect |
|---|---|
| `status` | Only steps with this status, e.g. `failed`. |
| `step_key` | Only the step with this key. |
| `include` | `logs` adds the `logs` array to each step. |
| `limit`, `cursor` | Page size (default 25, maximum 100) and position. |

Most runs fit on one page. Long workflows, or runs where `include=logs` makes each step heavy, need paging:

1. Request `GET /runs/{id}/steps?limit=100`.
2. Process `data`; steps arrive in `position` order.
3. If `next_cursor` is set, request the same URL with `cursor=<next_cursor>` and keep the same `include`, `status` and `step_key`.
4. Finish when `next_cursor` is null.

## Errors

The endpoint itself returns the standard API errors:

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | Unknown `status` or `include` value, or `limit` above 100. |
| 401 | `unauthorized` | Missing, expired or revoked API key. |
| 404 | `not_found` | No run with that id in this workspace, or the run is past the 90-day run history. |
| 429 | `rate_limited` | Too many requests; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |

### Step error codes

These codes appear in a step's `error` and in each attempt's `error`:

| Code | Meaning in a step |
|---|---|
| `WF-200` | The step ran for more than 10 minutes and was stopped. |
| `WF-400` | A data-mapping expression failed, e.g. a required field resolved to empty. |
| `WF-410` | An approval expired after 7 days without a decision. |
| `WF-500` | An internal Nimbus error; the run can be started again. |
| `CONN-401` | The connection's authorisation expired or was revoked; reconnect it. |
| `CONN-403` | The connected account lacks permission in the third-party app. |
| `CONN-404` | The record, file or object doesn't exist in the third-party app. |
| `CONN-429` | The third-party app throttled the connector; Nimbus backed off and retried. |
| `CONN-503` | The third-party app or the private connector agent was unavailable. |

For a timed-out run, `WF-210` is on the run object rather than on a step; the step that was running when the run hit 60 minutes shows `cancelled`.
