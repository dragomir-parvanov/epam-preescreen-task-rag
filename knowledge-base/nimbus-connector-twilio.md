---
id: nimbus-connector-twilio
title: Twilio Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-10-13
owner: Integrations Team
---

The Twilio connector sends SMS and WhatsApp messages and places voice calls from a workflow, and starts runs when Twilio reports something back: a reply from a customer, or a change in the delivery status of a message Nimbus sent. Clients use it for incident call-outs, appointment reminders and two-way confirmations ("Reply YES to confirm").

Unlike most polling connectors, Twilio triggers are push triggers. Twilio calls a Nimbus callback URL as soon as an event happens, and the run starts within seconds.

## Prerequisites

- **A Twilio account that can send.** A trial account can send only to phone numbers verified in the Twilio console, so test runs to unverified numbers fail. Production use needs an upgraded account.
- **A Twilio phone number or sender** that the workflow sends from: an SMS-capable number for SMS and calls, and a WhatsApp sender approved by Meta for WhatsApp.
- **Credentials.** Either the **Account SID** and **Auth Token** from the Twilio console dashboard, or an **API key pair** (an API key SID beginning `SK` and its secret) created under **Account > API keys & tokens**. An API key pair is better for production because it can be revoked without rotating the account's auth token, which other systems may also use.
- **The Builder or Admin role** in Nimbus to create the connection, and room for another active connector on the workspace's Plan Tier (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

## Creating the connection

1. In the Nimbus admin console, open **Connections** and click **New connection**.
2. Choose **Twilio**.
3. Under **Authentication**, pick **Auth token** or **API key**.
4. Enter the Account SID (it starts with `AC`). For **Auth token**, paste the auth token. For **API key**, paste the API key SID and secret, and paste the auth token into **Callback validation token** as well, because Twilio signs its callbacks with the account's auth token.
5. Click **Save and test**. Nimbus reads the account record and lists the phone numbers on the account, which then appear in the **From** picker of the send actions.

Nimbus checks the `X-Twilio-Signature` header on every callback it receives against the auth token on the connection, and drops any callback that doesn't match. If the client rotates their auth token in Twilio, update the connection straight away, or replies and status callbacks will stop starting runs.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| Incoming SMS | Push trigger | Starts a run for every SMS received on the chosen number. Output includes `From`, `To`, `Body` and `MessageSid`. |
| Message status changed | Push trigger | Starts a run when a message sent by this connection reaches one of the selected statuses: `sent`, `delivered`, `undelivered`, `failed` or `read` (WhatsApp only). |
| Call status changed | Push trigger | Starts a run when a call placed by this connection is `completed`, `busy`, `no-answer` or `failed`. |
| Send SMS | Action | Sends a text message, up to 1,600 characters, from a number on the account. |
| Send WhatsApp template message | Action | Sends an approved template, chosen by its Content SID (`HX…`), with its variables filled in. |
| Make a call | Action | Places a voice call and runs TwiML supplied in the step, or fetched from a URL. |

Activating a workflow with **Incoming SMS** points the number's **A message comes in** webhook at a callback URL on `hooks.nimbus.omnicorp.example` that is unique to that trigger. Any URL the client had there before is replaced, so check first whether another system relies on it. Numbers that belong to a Twilio Messaging Service take their webhook from the service instead; for those, set the Nimbus callback URL on the Messaging Service, which the trigger panel displays for copying.

Status triggers only receive callbacks for messages and calls that this connection sent, because Nimbus attaches its callback URL to each send.

## Field mapping

Every phone number, in **To** and **From** alike, must be in E.164 format: a plus sign, the country code and the number, with no spaces or punctuation, for example `+447700900123`. WhatsApp numbers take the `whatsapp:` prefix, for example `whatsapp:+447700900123`. Use an expression to tidy numbers that arrive in local formats before they reach the step.

A **Make a call** step that reads an incident summary aloud to the on-call engineer:

```xml
<Response>
  <Say voice="Polly.Amy" language="en-GB">
    Priority incident {{trigger.body.incident.id}}. {{trigger.body.incident.title}}.
  </Say>
  <Gather numDigits="1" timeout="10">
    <Say>Press 1 to acknowledge.</Say>
  </Gather>
</Response>
```

The template variables of a WhatsApp message are mapped by position, matching the numbered placeholders in the approved template:

```json
{
  "to": "whatsapp:{{steps.lookup_customer.output.mobile_e164}}",
  "contentSid": "HX5b7d1f2e8c4a4f0e9d3a6b1c2e7f8a90",
  "variables": { "1": "{{trigger.body.first_name}}", "2": "{{trigger.body.appointment_time}}" }
}
```

## Limits and behaviour

- **Push delivery.** Runs start within seconds of the callback. Every callback starts one run and counts towards the workspace's monthly workflow runs, so a **Message status changed** trigger watching every status can use several runs per message sent. Select only the statuses the workflow acts on.
- **WhatsApp session window.** Free-form WhatsApp messages can only be sent within 24 hours of the customer's last message, which is why the connector sends templates only. Templates must be approved in the Twilio console before they appear in the step.
- **Message length.** Long SMS bodies are split by Twilio into segments, each of which Twilio counts as a separate message; the step returns `numSegments`.
- **Retries.** A failed send is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Set retries to 0 on SMS steps where a duplicate message would be worse than a missing one, since a send that timed out may still have gone through.
- **Steps.** A **Make a call** step finishes when Twilio accepts the call, not when the call ends. Use **Call status changed** to act on the outcome.

## Troubleshooting

| Error | Twilio cause | Fix |
|---|---|---|
| CONN-401 | Auth token rotated, or the API key deleted (Twilio error 20003). | Update the credentials and click **Reconnect**. |
| CONN-403 | Trial account sending to an unverified number (21608), or the sender isn't enabled for the destination country. | Verify the number, upgrade the account, or enable the country under Twilio's messaging geographic permissions. |
| CONN-404 | The Content SID or the **From** number isn't on this account. | Check the template and number in the Twilio console. |
| CONN-429 | Twilio queued too many requests from the account. | Nimbus backs off and retries the step. |
| WF-400 | The **To** number is empty or not in E.164 (Twilio error 21211). | Normalise the number with an expression before the step. |
| No runs from Incoming SMS | Another system overwrote the number's webhook, or the auth token changed. | Deactivate and reactivate the workflow to reset the webhook; update the connection's token. |
