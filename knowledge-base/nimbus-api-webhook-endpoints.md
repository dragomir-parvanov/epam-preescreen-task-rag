---
id: nimbus-api-webhook-endpoints
title: Webhook Endpoints API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-06
owner: Platform API Team
---

A webhook endpoint is an HTTPS URL on the client's side that Nimbus calls when a subscribed event happens. This resource registers endpoints, lists them, changes the events they receive, enables or disables them, sends a test event and deletes them. It is the API counterpart of **Settings > Developers > Webhooks**, described for Admins in [Registering Webhook Endpoints](nimbus-admin-webhook-endpoints.md).

How a delivery is signed, how the receiver verifies it, the event payloads, and the retry and disable rules for failing endpoints are all in [API Rate Limits and Webhooks](nimbus-api-webhooks.md); they are not repeated here. The delivery log of an endpoint has its own resource, the [Webhook Deliveries API](nimbus-api-webhook-deliveries.md). As everywhere in the API, authenticate with `Authorization: Bearer <api-key>`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/webhooks/endpoints` | List registered endpoints. |
| `POST` | `/webhooks/endpoints` | Register an endpoint; the response carries its signing secret, once. |
| `GET` | `/webhooks/endpoints/{id}` | Read one endpoint. |
| `PATCH` | `/webhooks/endpoints/{id}` | Change `url`, `description`, `events` or `status`. |
| `DELETE` | `/webhooks/endpoints/{id}` | Remove the endpoint; nothing more is sent to it. |
| `POST` | `/webhooks/endpoints/{id}/test` | Send a sample event now and return the receiver's answer. |
| `GET` | `/webhooks/endpoints/{id}/deliveries` | The endpoint's delivery log (see the Webhook Deliveries API). |

### Registering an endpoint

`POST /webhooks/endpoints` takes a `url`, which must start with `https://`, an `events` array with at least one of the five event types, and an optional `description`. The new endpoint starts `enabled` and receives events from the moment it is created; events that happened earlier are not replayed.

The response is the only place the endpoint's `signing_secret` appears. Store it in the receiving system's secret store straight away. Later reads return the endpoint without the secret, and if it is lost the secret has to be rolled under **Settings > Developers > Webhooks**, which the API doesn't offer. Rolling takes effect from the next delivery, so plan the switch on the receiving side first.

### Sending a test event

`POST /webhooks/endpoints/{id}/test` sends one sample event to the URL and waits for the answer, which is useful straight after registering or after fixing a receiver. Pick the event type with `{"event": "workflow.run.failed"}`; without a body Nimbus sends `workflow.run.completed`. The sample has the normal envelope and signature, plus `"test": true` at the top level so the receiver can ignore it. The call returns the delivery id, the HTTP status the receiver gave and how long it took. The test shows up in the delivery log with `"test": true` and is never retried.

An endpoint that Nimbus disabled because its deliveries kept failing can only be set back to `enabled` after a test event has succeeded, just as the console asks for **Send test event** before **Enable**.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Endpoint id, prefixed `whk_`. |
| `url` | string | The HTTPS URL that receives `POST` requests. |
| `description` | string or null | A note for Admins, e.g. "Finance data warehouse loader". |
| `events` | array | Subscribed event types (list below). |
| `status` | string | `enabled` or `disabled`. |
| `disabled_reason` | string or null | `manual` when an Admin or API call disabled it; `failing` when Nimbus did. |
| `signing_secret` | string | Only in the `POST` response; starts with `whsec_`. |
| `last_delivery_at` | string or null | Time of the most recent delivery attempt. |
| `last_success_at` | string or null | Time of the most recent 2xx answer. |
| `created_by` | string | The `usr_` or `key_` id that registered it. |
| `created_at`, `updated_at` | string | Lifecycle timestamps. |

The five event types are `workflow.run.completed`, `workflow.run.failed`, `user.provisioned`, `user.suspended` and `connector.disconnected`. An endpoint may subscribe to any subset.

Deleting an endpoint stops everything at once, including retries already scheduled, and removes its delivery log. To pause deliveries but keep the log, `PATCH` the endpoint with `{"status": "disabled"}` instead. Events that happen while an endpoint is disabled are not queued for later.

## Example request and response

```http
POST /webhooks/endpoints HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: register-ops-alerts-01

{
  "url": "https://hooks.clientco.example/nimbus/ops",
  "description": "Ops channel alerts",
  "events": ["workflow.run.failed", "connector.disconnected"]
}
```

```json
{
  "id": "whk_5108",
  "url": "https://hooks.clientco.example/nimbus/ops",
  "description": "Ops channel alerts",
  "events": ["workflow.run.failed", "connector.disconnected"],
  "status": "enabled",
  "disabled_reason": null,
  "signing_secret": "whsec_7Hq2mV9cXr4LpT8eZk1NwB6s",
  "last_delivery_at": null,
  "last_success_at": null,
  "created_by": "key_3307",
  "created_at": "2026-07-01T11:48:20Z",
  "updated_at": "2026-07-01T11:48:20Z"
}
```

To add an event later, send the full list in a `PATCH`; `events` is replaced, not merged:

```http
PATCH /webhooks/endpoints/whk_5108 HTTP/1.1
Content-Type: application/json

{"events": ["workflow.run.failed", "connector.disconnected", "user.suspended"]}
```

## Filtering and pagination

`GET /webhooks/endpoints` accepts `status` (`enabled` or `disabled`), `event` (endpoints subscribed to that event type) and `disabled_reason`. It pages with `limit`, 25 by default and 100 at most, and `cursor`. To find every endpoint that Nimbus has switched off:

1. Call `GET /webhooks/endpoints?status=disabled&disabled_reason=failing`.
2. For each endpoint in `data`, check `last_success_at` to see how long it has been failing.
3. Repeat with `cursor=<next_cursor>` while `next_cursor` isn't null.
4. Fix each receiver, send a test event, then `PATCH` it with `{"status": "enabled"}`.

## Errors

| HTTP status | Code | Reason |
|---|---|---|
| 400 | `invalid_request` | The URL isn't `https://`, `events` is empty, or it names an unknown event type. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 404 | `not_found` | No endpoint with that id in the workspace. |
| 409 | `conflict` | Another endpoint is already registered with the same URL. |
| 409 | `conflict` | Enabling an endpoint with `disabled_reason: failing` before a test event succeeded. |
| 429 | `rate_limited` | The workspace's API limit was reached. |

A failing test is not an API error: `POST /webhooks/endpoints/{id}/test` answers `200 OK` and reports the receiver's status, such as `500` or `timeout`, in the body. The receiver has 15 seconds to answer with a 2xx status.
