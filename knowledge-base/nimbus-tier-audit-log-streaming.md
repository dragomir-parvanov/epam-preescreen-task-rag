---
id: nimbus-tier-audit-log-streaming
title: Audit Log Streaming
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-01
owner: Product Operations
---

Audit log streaming sends every audit-log event from a Nimbus workspace to the client's own security tooling as it happens, instead of waiting for someone to export a CSV. The supported destinations are Splunk (through the HTTP Event Collector), Datadog Logs and any HTTPS endpoint the client runs. Streaming was introduced in release 3.6.0 and is configured under **Settings > Audit log > Streaming**.

Clients usually ask for it when their security team wants Nimbus sign-ins, role changes and API key activity correlated with other systems in a SIEM, or when they need to hold audit events for longer than the workspace keeps them. Streaming doesn't change what the audit log records or how long Nimbus keeps it; for retention by tier, see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Availability by Plan Tier

| Capability | Starter | Business | Enterprise |
|---|---|---|---|
| Audit log in the console (search, CSV export) | Yes | Yes | Yes |
| Audit log streaming | No | No | Yes |
| Destinations | – | – | Splunk, Datadog, HTTPS endpoint |

On Starter and Business, the **Streaming** tab is visible but greyed out with an "Available on Enterprise" label. Those clients can still search the log and export it by hand or on a schedule, as described in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## How it works

Every time Nimbus writes an event to the workspace audit log, it also places a copy on the stream for each enabled destination. Events are batched and delivered in near real time: a batch is sent as soon as it holds 100 events or 5 seconds after its first event, whichever comes first, so an event normally reaches the destination within a few seconds of the action that caused it.

Each event is a JSON object with the same fields that `GET /audit-log/events` returns, plus the `workspace_id` it came from. Splunk receives one HEC event per audit event with the sourcetype `nimbus:audit`; Datadog receives log entries tagged `source:nimbus` and `service:nimbus-audit`; an HTTPS endpoint receives a JSON array of events in the request body.

```json
{
  "id": "evt_8KQ2M4D7XN",
  "occurred_at": "2026-05-18T09:42:11Z",
  "workspace_id": "ws_4TR9QK2L",
  "action": "api_key.created",
  "actor": {
    "type": "user",
    "id": "usr_7HD2PL0C",
    "display": "jana.novak@client.example"
  },
  "target": { "type": "api_key", "id": "key_3XW8VN1B", "display": "ERP sync" },
  "changes": null,
  "source": "console",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
```

The `action` values match the action filter in the console, for example `auth.sign_in_succeeded`, `user.role_changed`, `user.suspended`, `sso.configuration_updated`, `webhook_endpoint.created` and `audit_stream.updated`. Changes to the stream configuration are themselves audit events, so a security team can see who pointed the stream somewhere else.

### Delivery failures

If a destination rejects a batch or doesn't answer with a 2xx status within 10 seconds, Nimbus keeps the batch and retries it with exponential backoff for up to 24 hours. Events stay in order per destination: newer batches wait behind the failing one. While retries are running, the destination's status on the Streaming tab changes from **Healthy** to **Retrying**, and every Admin receives an email after the first hour of failures. If a batch still fails after 24 hours it is dropped from the stream, the status becomes **Failing**, and the destination keeps trying with new events. Dropped events are never lost from Nimbus itself: they remain in the workspace audit log, so the gap can be filled with a CSV export for the affected time range.

## Turning it on

Only an Admin can configure streaming. Have the destination details ready before starting: a Splunk HEC URL and token, a Datadog API key and site, or an HTTPS URL and the header value the endpoint expects.

1. Go to **Settings > Audit log > Streaming** and click **Add destination**.
2. Choose **Splunk**, **Datadog** or **HTTPS endpoint**.
3. Fill in the destination fields. For Splunk: **HEC URL**, **HEC token** and an optional **Index**. For Datadog: **Site** (for example `datadoghq.eu`) and **API key**. For an HTTPS endpoint: **URL** (must start with `https://`) and an optional **Authorization header** value, sent with every request.
4. Click **Send test event**. Nimbus sends one event with the action `audit_stream.tested` and shows the destination's response code.
5. Click **Enable stream**. Streaming starts with the next event; past events aren't replayed, so export the existing log as CSV if the destination needs history.

Before enabling a Splunk destination, it helps to confirm that the HEC token accepts events at all. The client's Splunk administrator can run this from any machine that can reach their Splunk instance:

```bash
curl -s https://splunk.client.example:8088/services/collector/event \
  -H "Authorization: Splunk 6f1c2a90-4e1b-4d0a-9d3e-2b7c55a1f0de" \
  -d '{"sourcetype": "nimbus:audit", "event": {"action": "audit_stream.tested"}}'
```

A response of `{"text":"Success","code":0}` means the token and index are valid. Credentials typed into a destination are encrypted and never shown again after saving; to change them, edit the destination and enter new values.

## Limits

| Limit | Value |
|---|---|
| Destinations per workspace | 2 |
| Events per batch | Up to 100 |
| Maximum batch body size | 1 MB |
| Batch wait before sending | Up to 5 seconds |
| Destination response timeout | 10 seconds |
| Retry window for a failed batch | 24 hours |

Two destinations let a client send the same events to a SIEM and to a long-term archive behind their own HTTPS endpoint. Both destinations receive every event; there is no per-destination filtering by action. Pausing a destination with the **Pause** toggle stops delivery without deleting its settings, and events written while it is paused are not sent when it resumes.

## When the Plan Tier changes

An upgrade to Enterprise takes effect immediately, so the **Streaming** tab becomes available as soon as the change is applied. Only events written after a destination is enabled are streamed.

A downgrade from Enterprise takes effect at the end of the current billing period. At that moment every destination is disabled and streaming stops; the destination settings are kept but can't be edited, and the tab returns to its greyed-out state. If the workspace is upgraded to Enterprise again later, an Admin re-enters the credentials and enables each destination; events from the period without streaming are not sent retroactively. The same downgrade also shortens how long the console keeps audit events, and older events are deleted when it takes effect, so recommend a final export before the date. Those retention values are listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
