---
id: nimbus-api-webhook-deliveries
title: Webhook Deliveries API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-13
owner: Platform API Team
---

Every time Nimbus sends an event to a webhook endpoint it records a delivery: which event it was, every attempt to send it, what the receiver answered and how long it took. The Webhook Deliveries API reads that log for one endpoint and lets a client send a delivery again by hand. It is the quickest way to answer a client who says "we never got the webhook".

Endpoints themselves are managed with the [Webhook Endpoints API](nimbus-api-webhook-endpoints.md). The automatic retry schedule, the signature on each request and the disabling of endpoints that keep failing are covered in [API Rate Limits and Webhooks](nimbus-api-webhooks.md). Authenticate with an API key in `Authorization: Bearer <api-key>`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/webhooks/endpoints/{id}/deliveries` | List one endpoint's deliveries, newest first, with every attempt. |
| `POST` | `/webhooks/deliveries/{id}/redeliver` | Send one delivery again now. |

### Redelivering

`POST /webhooks/deliveries/{id}/redeliver` takes no body and makes one extra attempt straight away, outside the automatic schedule. Nimbus sends the original payload again, with a fresh signature and the same delivery id in the `X-Nimbus-Delivery` header, and waits for the answer. The response is the updated delivery, with the new attempt at the end of `attempts` marked `"trigger": "manual"`.

If the manual attempt succeeds, the delivery becomes `succeeded` and any automatic retries still scheduled for it are cancelled. If it fails, the automatic schedule carries on as before; a manual attempt doesn't reset it or use up one of its retries.

Because the delivery id doesn't change, a receiver that ignores ids it has already processed will also ignore a redelivery of a delivery it handled successfully. That is intended: redelivering is for deliveries the receiver never accepted. To process an event twice on purpose, the receiver has to forget the id first.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Delivery id, prefixed `dlv_`; also sent as `X-Nimbus-Delivery`. |
| `endpoint_id` | string | The `whk_` id of the endpoint. |
| `event_id` | string | The `evt_` id of the event, the `id` in the payload envelope. |
| `event` | string | Event type, e.g. `workflow.run.failed`. |
| `status` | string | `pending` (first attempt not sent yet), `retrying`, `succeeded` or `failed` (no automatic retries left). |
| `test` | boolean | True for sample events sent with the test endpoint. |
| `attempts` | array | Every attempt, oldest first (see below). |
| `next_attempt_at` | string or null | When the next automatic retry is due; null once the delivery is final. |
| `created_at` | string | When the event was queued for this endpoint. |

Each attempt in `attempts` has:

| Field | Description |
|---|---|
| `number` | 1 for the first send, counting up. |
| `trigger` | `automatic` or `manual`. |
| `sent_at` | When the request left Nimbus. |
| `response_status` | The receiver's HTTP status, or null if there was none. |
| `duration_ms` | Time until the answer, or until Nimbus gave up. |
| `error` | Null on success; otherwise `non_2xx`, `timeout`, `connection_failed` or `tls_error`. |

An attempt counts as failed unless the receiver answers with a 2xx status within 15 seconds. A `timeout` shows a `duration_ms` of about 15000 and no `response_status`. A `tls_error` usually means an expired or self-signed certificate on the receiver.

Deliveries to one endpoint are independent of each other. A delivery that is still retrying doesn't hold back the next event, so a receiver can get events out of order and should rely on `created_at` in the payload rather than on arrival order.

## Example request and response

Listing the deliveries to an endpoint that is struggling:

```http
GET /webhooks/endpoints/whk_5108/deliveries?status=retrying,failed&limit=1 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "id": "dlv_8MQ27XK4",
      "endpoint_id": "whk_5108",
      "event_id": "evt_01JA3PZ6WY5C",
      "event": "workflow.run.failed",
      "status": "retrying",
      "test": false,
      "attempts": [
        {"number": 1, "trigger": "automatic", "sent_at": "2026-07-09T10:00:00Z", "response_status": 502, "duration_ms": 311, "error": "non_2xx"},
        {"number": 2, "trigger": "automatic", "sent_at": "2026-07-09T10:01:00Z", "response_status": null, "duration_ms": 15000, "error": "timeout"},
        {"number": 3, "trigger": "automatic", "sent_at": "2026-07-09T10:06:00Z", "response_status": 503, "duration_ms": 204, "error": "non_2xx"}
      ],
      "next_attempt_at": "2026-07-09T10:21:00Z",
      "created_at": "2026-07-09T10:00:00Z"
    }
  ],
  "next_cursor": "c2Vxbm86ZGx2XzhNUTI3WEs0"
}
```

The receiver is returning 502 and 503 from its load balancer, so the problem is on the client's side. Once they have fixed it, a manual redelivery confirms it without waiting for the next retry:

```http
POST /webhooks/deliveries/dlv_8MQ27XK4/redeliver HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

## Filtering and pagination

The deliveries list takes these query parameters:

- `status`: one or more of `pending`, `retrying`, `succeeded`, `failed`, comma-separated.
- `event`: one event type.
- `event_id`: the deliveries of one `evt_` event, useful when the client quotes the payload id.
- `from`, `to`: ISO 8601 bounds on `created_at`.
- `test`: `false` to leave out test events.
- `limit` (default 25, maximum 100) and `cursor`.

After an outage on the client's side, this pattern resends everything that ran out of retries:

1. Call `GET /webhooks/endpoints/{id}/deliveries?status=failed&from=<outage start>&test=false&limit=100`.
2. For each delivery in `data`, call `POST /webhooks/deliveries/{dlv_id}/redeliver` and check its new `status`.
3. If `next_cursor` is not null, fetch the next page with `cursor=<next_cursor>` and the same filters.
4. Stop when `next_cursor` is null.

Pause briefly between redeliveries so that the receiver, just recovered, isn't flooded.

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | Unknown `status` or `event` value, or a malformed timestamp. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 404 | `not_found` | No such endpoint or delivery in this workspace, or the endpoint was deleted. |
| 409 | `conflict` | Redelivering to an endpoint whose `status` is `disabled`; enable it first. |
| 409 | `conflict` | Redelivering a delivery that is still `pending`. |
| 429 | `rate_limited` | Too many API calls; see the rate-limit section of API Rate Limits and Webhooks. |

The redeliver call itself answers `200 OK` even when the receiver fails again; the outcome is in the last attempt.
