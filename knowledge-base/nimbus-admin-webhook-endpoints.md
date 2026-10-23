---
id: nimbus-admin-webhook-endpoints
title: Registering Webhook Endpoints
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-08
owner: Workspace Administration Team
---

A webhook endpoint is an HTTPS URL in the client's own systems that OmniCorp Nimbus calls when something happens in the workspace: a run finishes or fails, a user is provisioned or suspended, a connector loses its authorisation. Registering one is an Admin task in the console, and most of the support questions about webhooks come down to a step in this guide being skipped, usually the test event or storing the signing secret.

This guide is about managing endpoints in the console and the API. How deliveries are signed and verified, and how failed deliveries are retried, is described in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Before you begin

- **Role:** Admin.
- **Plan Tier:** registering endpoints needs a tier with API access; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- **A receiver that is ready:** the client's developers should have deployed the receiving service before you register it. It must accept `POST` requests with a JSON body over HTTPS with a certificate from a public certificate authority, and answer with a 2xx status within 15 seconds.
- **Signature checking in place:** the receiver should verify every delivery with the endpoint's signing secret. Agree with the developers how you will pass them the secret, since you will copy it from the console.

## How it works

Each endpoint has a URL, a description, a list of subscribed events, a signing secret and an enabled flag. A workspace can register up to 20 endpoints, and the same event can go to several of them. The events to choose from are:

| Event | Typical use on the client's side |
|---|---|
| `workflow.run.completed` | Mark a downstream job as ready, or update a status board |
| `workflow.run.failed` | Open an incident in the client's own ticketing tool |
| `user.provisioned` | Add the new user to an internal access register |
| `user.suspended` | Remove the user from that register |
| `connector.disconnected` | Alert the integration team to reconnect the connection |

Subscribe each endpoint only to the events its receiver handles. Unwanted events still cost the receiver a request and fill the delivery log with noise. Clients with separate test and production receivers should register them as separate endpoints, each with its own signing secret, rather than switching one endpoint's URL back and forth.

Every attempt to call the endpoint is a delivery with its own `dlv_` id, which Nimbus also sends in the `X-Nimbus-Delivery` header. The endpoint's **Deliveries** tab keeps a log of them: the event, the time, the HTTP status the receiver returned, how long it took, the number of attempts, and the first 2 KB of the request and response bodies. Use it as the first place to look when a client says "we never got the event".

An endpoint that keeps failing can be disabled by Nimbus. A disabled endpoint receives nothing until an Admin switches it back on with the **Enabled** toggle, or with `PATCH /webhooks/endpoints/{id}` and `{"enabled": true}`.

## Step-by-step

To register an endpoint in the console:

1. Open **Settings > Developers > Webhooks** and click **Add endpoint**.
2. Enter the **Endpoint URL**, which must start with `https://`, and a **Description** such as "ServiceDesk incident bridge (prod)".
3. Under **Events**, tick the events to send.
4. Click **Create endpoint**. The page shows the endpoint's **Signing secret**; click **Copy** and hand it to the client's developers through their secrets manager. Admins can show it again later with **Reveal**.
5. Click **Send test event**, pick an event type and click **Send**. Nimbus sends a sample delivery marked `"test": true` and shows the receiver's response status in the dialog.
6. Check the **Deliveries** tab: the test should be listed with a 2xx status.

The same registration through the API:

```bash
curl -X POST https://api.nimbus.omnicorp.example/webhooks/endpoints \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://hooks.northwind.example/nimbus",
        "description": "ServiceDesk incident bridge (prod)",
        "events": ["workflow.run.failed", "connector.disconnected"]
      }'
```

The response holds the new `whk_` id and the `signing_secret`. `POST /webhooks/endpoints/{id}/test` sends a test event, and `GET /webhooks/endpoints/{id}/deliveries` reads the log.

### Redelivering and rolling the secret

To send a past delivery again, for example after the receiver was fixed, open it in the **Deliveries** tab and click **Redeliver**, or call `POST /webhooks/deliveries/{id}/redeliver`. The redelivery carries the same `X-Nimbus-Delivery` id as the original, so the receiver's duplicate check should only skip ids it actually processed.

To replace the signing secret, open the endpoint and click **Roll secret**, then confirm. The new secret is used from the next delivery onwards, so coordinate the moment with the developers: they deploy the new secret at the same time as you roll it.

## Verifying the change

A healthy endpoint shows **Enabled** and a recent delivery with a 2xx status on its **Deliveries** tab. `GET /webhooks/endpoints/{id}` returns `"enabled": true` and the subscribed `events`. After a secret roll, send a test event and confirm with the developers that the receiver accepted it rather than rejecting it as unsigned. Endpoint creation, changes and secret rolls are recorded in **Settings > Audit log**.

## Troubleshooting

| What the client sees | What to check |
|---|---|
| Test event shows "Connection failed" | The URL is wrong, the host doesn't resolve publicly, or the certificate isn't from a public authority. Fix the receiver and send the test again. |
| Test event shows HTTP 401 from the receiver | The receiver rejected the signature, usually because it has an old or mistyped secret. Copy the secret again with **Reveal**. |
| Deliveries show "Timed out" | The receiver took longer than 15 seconds. It should acknowledge at once and process the event afterwards. |
| No deliveries at all for an event | The endpoint isn't subscribed to it. Edit the endpoint and tick the event. |
| The endpoint shows **Disabled** | It failed for too long and Nimbus switched it off. Fix the receiver, turn **Enabled** back on, and redeliver what was missed. |
| Duplicate processing on the client's side | The receiver doesn't de-duplicate on `X-Nimbus-Delivery`. Ask the developers to store processed ids. |
