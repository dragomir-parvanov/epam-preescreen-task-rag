---
id: nimbus-api-inbound-webhook-triggers
title: Inbound Webhook Triggers
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-20
owner: Platform API Team
---

An inbound webhook trigger starts a workflow whenever another system sends it an HTTP request. Each workflow with this trigger gets its own URL of the form `https://hooks.nimbus.omnicorp.example/t/<trigger-token>`. A `POST` with a JSON body to that URL queues a run straight away and answers `202 Accepted` with the new run's id; the workflow reads the payload through `{{trigger.body.<field>}}` expressions.

The hook URL is not part of the REST API at `https://api.nimbus.omnicorp.example`. It needs no API key, which makes it easy to call from form tools, monitoring systems and partner platforms that can't manage bearer tokens, but it also means the URL itself is the credential. Treat it like a password.

## Endpoints

| Method | URL or path | Purpose |
|---|---|---|
| `POST` | `https://hooks.nimbus.omnicorp.example/t/<trigger-token>` | Send a JSON event and start a run. |
| `GET` | `/workflows/{id}` | Read the workflow, including its `trigger` object and hook URL (REST API, API key required). |
| `GET` | `/runs?workflow_id={id}` | Find the runs the hook has started (REST API, API key required). |

Only `POST` is accepted on the hook URL. Other methods answer `405 Method Not Allowed` with no body, so a browser opening the URL can't start a run.

### Sending an event

Send `Content-Type: application/json` and a JSON object of at most 1 MB. Top-level fields become `trigger.body` fields, so `{"order": {"id": "55871"}}` is read as `{{trigger.body.order.id}}`. Nimbus answers as soon as the run is queued, not when it finishes; a sender that needs the outcome should poll `GET /runs/{id}` with the returned id or subscribe to the `workflow.run.completed` webhook event.

The hook doesn't deduplicate requests and ignores the `Idempotency-Key` header. If the sending system retries on timeouts, include its own event id in the body and add a condition step that skips events it has already handled.

### Regenerating the trigger token

When a hook URL has leaked, for example in a support ticket or a shared screenshot, a Builder or Admin replaces it in the workflow builder:

1. Open the workflow under **Workflows** and select the trigger.
2. Click **Regenerate URL** and confirm.
3. Copy the new URL into the sending system.

The old token stops working the moment the new one is created, and requests to it get `404 not_found`. Plan the switch so the sending system is updated within minutes, or schedule it for a quiet period. Regenerating doesn't publish a new workflow version and doesn't affect runs already queued.

## Object fields

The workflow's `trigger` object, as returned by `GET /workflows/{id}`:

| Field | Type | Description |
|---|---|---|
| `type` | string | `webhook` for this trigger. |
| `url` | string | The full hook URL, including the token. Returned only to API keys, never in audit-log entries. |
| `token_hint` | string | The last four characters of the token, to identify a URL without exposing it. |
| `token_created_at` | string | When the current token was generated (ISO 8601, UTC). |

The `202 Accepted` response from the hook URL:

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Id of the queued run (`run_`). |
| `workflow_id` | string | The workflow the token belongs to (`wf_`). |
| `status` | string | Always `queued` at this point. |
| `received_at` | string | When Nimbus accepted the request. |

## Example request and response

A form tool posts a new trial sign-up:

```bash
curl -X POST "https://hooks.nimbus.omnicorp.example/t/htk_Q8m2Vx7rLp4Zc1Nw9sYb" \
  -H "Content-Type: application/json" \
  -d '{"email": "lena.fischer@example.org", "company": "Fischer Logistik", "plan_interest": "Business"}'
```

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "run_id": "run_2Rw9cN5j",
  "workflow_id": "wf_6Gk3sT8a",
  "status": "queued",
  "received_at": "2026-04-17T11:20:05Z"
}
```

The workflow's first step can then map `{{lower(trigger.body.email)}}` into a HubSpot contact. Nimbus doesn't check a sender's identity beyond the token. Where the sender can add a shared value to the body, store that value as a secret and add a condition step that compares `{{trigger.body.shared_key}}` with `{{secrets.SIGNUP_FORM_KEY}}` before doing any work.

## Filtering and pagination

The hook URL takes no query parameters; anything after `?` is ignored and isn't passed to the run. Runs started by the hook are listed with the cursor-paginated Runs API, filtered by `workflow_id` and `trigger_type=webhook`, plus `from` and `to` for a time window. To collect every hook-started run for a day:

1. Call `GET /runs?workflow_id=wf_6Gk3sT8a&trigger_type=webhook&from=2026-04-17T00:00:00Z&to=2026-04-18T00:00:00Z&limit=100`.
2. Read each run's `status` and `id` from `data`.
3. While `next_cursor` is not `null`, call the same URL with `cursor=<next_cursor>` added.
4. Stop at the page where `next_cursor` is `null`.

`limit` defaults to 25 and can be at most 100. The run's input, including the full JSON body that was posted, is kept with run history for 90 days; see [Runs API](nimbus-api-runs.md).

## Errors

The hook URL answers errors in the same `{"error": {"code": "...", "message": "..."}}` envelope as the REST API. No run is created for any of them.

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | The body isn't valid JSON, isn't a JSON object, is larger than 1 MB, or `Content-Type` isn't `application/json`. |
| 404 | `not_found` | The token doesn't exist or has been regenerated, or the workflow was deleted. |
| 403 | `forbidden` | The workspace has used its monthly workflow runs; the message starts `WF-300`. |
| 409 | `conflict` | The workflow is deactivated. |
| 500 | `internal_error` | An internal Nimbus error; the sender can retry. |

When the concurrent-run limit is reached the hook still answers `202`: the run waits as `queued` with the notice WF-310 and starts when a slot frees up; see [Concurrent Run Limits](nimbus-tier-concurrent-runs.md). An `Authorization` header is never needed, so `401` is never returned; a sender getting `401` is calling the REST API host by mistake.
