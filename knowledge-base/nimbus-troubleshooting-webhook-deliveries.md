---
id: nimbus-troubleshooting-webhook-deliveries
title: Troubleshooting Webhook Deliveries
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-20
owner: Support Engineering
---

Outgoing webhooks are the events Nimbus sends to an endpoint on the client's side, such as `workflow.run.failed` or `user.suspended`. A delivery fails when that endpoint doesn't answer with a 2xx status within 15 seconds, and from the client's point of view the event simply never arrives, or arrives twice. Almost every failed delivery is caused by the receiving endpoint, so this reference looks at the problem from the client's server outwards.

For how often Nimbus retries a failed delivery and when it disables an endpoint, see [API Rate Limits and Webhooks](nimbus-api-webhooks.md); those rules aren't repeated here. Calls going the other way, into a workflow's trigger URL, are covered in [Troubleshooting Inbound Webhook Triggers](nimbus-troubleshooting-inbound-triggers.md).

## Symptoms

- The client's system is missing events that Nimbus shows as sent, for example a run that failed with no matching alert in their ticketing tool.
- Events arrive late, sometimes hours after the run finished, because they only succeeded on a later retry.
- The same event arrives two or more times, each with the same `X-Nimbus-Delivery` id.
- The client's endpoint logs show requests from Nimbus that it rejected, most often with 401 from its own signature check.
- Under **Settings > Developers > Webhooks**, the endpoint shows a run of failed deliveries or has the status **Disabled**.

Duplicate deliveries are the least intuitive symptom. They happen when the endpoint does the work but answers after 15 seconds: Nimbus records a timeout and retries, and the endpoint processes the event again.

## Common causes

**A non-2xx answer.** Nimbus treats anything other than 2xx as a failure. Common examples are a 404 after the client moved the endpoint's path, a 401 or 403 from an API gateway that expects its own credentials, a 500 from an unhandled exception in the client's handler, and a 301 or 302 redirect from `http` to `https` or to a new host. Nimbus doesn't follow redirects, so a redirect counts as a failure even if the final URL would have worked.

**Answering after 15 seconds.** Handlers that call other systems, write to a slow database or run a report before replying will time out under load, even if they are fast in testing.

**TLS certificate problems.** Endpoints must be HTTPS with a certificate that a public certificate authority issued and that is valid for the endpoint's hostname, served over TLS 1.2 or later. An expired certificate, a self-signed or internal-CA certificate, a hostname mismatch, or a server that doesn't send its intermediate certificate all fail the TLS handshake before any HTTP status is exchanged.

**Signature verification failing on the client's side.** The client's code rejects genuine deliveries because it checks the signature against something other than the raw request body. Many web frameworks parse the JSON automatically; if the handler then re-serialises the parsed object and computes the HMAC over that, the key order, spacing or number formatting differs from what Nimbus signed, and the comparison against the `X-Nimbus-Signature-256` header fails. The other frequent cause is a signing secret that an Admin rolled while the endpoint still verifies with the old one.

## Diagnosing the problem

1. Open **Settings > Developers > Webhooks**, select the endpoint and open its **Deliveries** tab. Each delivery shows its id (`dlv_...`), the event, every attempt with its timestamp, the response status or failure reason, the response time, and the first 2 KB of the response body.
2. To pull the same data for many deliveries, use the API. Filter on failed deliveries and read the `attempts` of each:

```http
GET /webhooks/endpoints/whk_3RT9LC/deliveries?status=failed&limit=50 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

3. Click **Send test event** on the endpoint page, or call `POST /webhooks/endpoints/{id}/test`, while someone on the client's side watches their server log. A test event is signed like a real one.
4. If the failure reason is a TLS error, check the certificate chain from any machine outside the client's network:

```bash
openssl s_client -connect hooks.client.example:443 -servername hooks.client.example -showcerts < /dev/null
```

The output should end with `Verify return code: 0 (ok)` and list the intermediate certificate as well as the server certificate.

5. If the endpoint answers 401 to genuine deliveries, ask the client to log the length of the raw body and the digest they compute, and compare them with the delivery's body in the delivery log.

## Error reference

These are the results the delivery log shows for an attempt. Webhook deliveries have no Nimbus error codes of their own.

| Delivery log result | Meaning | Where to look |
|---|---|---|
| `2xx` | Delivered. | Nothing to fix. |
| `301`, `302`, `307`, `308` | The endpoint redirected; Nimbus doesn't follow redirects. | Register the final URL. |
| `401`, `403` | The endpoint, or a gateway in front of it, refused the request. | Signature check or gateway authentication. |
| `404`, `405` | The path or method isn't handled. | Endpoint URL and routing. |
| `5xx` | The client's application failed. | The client's application logs. |
| `Timeout after 15 s` | No answer in time; the request may still have been processed. | Handler speed. |
| `TLS handshake failed` | The certificate is expired, untrusted, for another host, or missing its chain. | Certificate and server TLS configuration. |
| `Connection refused` | Nothing is listening on the host and port. | The client's hosting or DNS. |

## Fixes

- **Acknowledge first, process later.** The handler should verify the signature, put the event on a queue, answer 200 or 202, and do the work afterwards. Use the `X-Nimbus-Delivery` id to ignore an event already processed.
- **Verify against the raw body.** Read the body as bytes before any JSON parsing, as in this Flask example:

```python
import hashlib
import hmac

from flask import Flask, abort, request

app = Flask(__name__)
SIGNING_SECRET = b"<endpoint-signing-secret>"


@app.post("/nimbus/events")
def nimbus_events():
    raw = request.get_data()  # raw bytes, not request.json
    expected = "sha256=" + hmac.new(SIGNING_SECRET, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Nimbus-Signature-256", "")):
        abort(401)
    enqueue(raw)
    return "", 202
```

- **Fix the certificate.** Renew it, serve the full chain, and use a publicly trusted certificate on the exact hostname registered.
- **Register the final URL** when the endpoint moved, with **Edit** on the endpoint page or `PATCH /webhooks/endpoints/{id}`; see [Registering Webhook Endpoints](nimbus-admin-webhook-endpoints.md).
- **Resend what was missed.** Once the endpoint works, click **Redeliver** on a delivery in the log, or call `POST /webhooks/deliveries/{id}/redeliver`. A redelivery keeps the original `X-Nimbus-Delivery` id, so the client's de-duplication still applies. See [Webhook Deliveries API](nimbus-api-webhook-deliveries.md) for redelivering in bulk.
- **Re-enable a disabled endpoint** as described in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Escalating to support

Escalate only after a test event has been tried against a fixed endpoint and still fails, or when the delivery log disagrees with the client's server log. Collect:

- the endpoint id (`whk_...`) and the URL it is registered with;
- two or three delivery ids (`dlv_...`) and their event ids (`evt_...`), with the attempt timestamps in UTC;
- the client's server or load-balancer log lines for those timestamps;
- the result of **Send test event** and, for TLS failures, the `openssl s_client` output.

Never include the endpoint's signing secret in the ticket.
