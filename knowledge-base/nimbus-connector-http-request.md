---
id: nimbus-connector-http-request
title: HTTP Request Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-07-27
owner: Integrations Team
---

The HTTP Request connector calls any HTTPS API from a workflow step. Clients use it for systems that have no dedicated Nimbus connector, such as an in-house ERP, a niche SaaS tool or a partner's order API, and for endpoints a dedicated connector doesn't cover. One connection holds a base URL and the authentication for one API; the **Send request** action then sends any method, headers and body to paths under that URL.

The connector has actions only. To start a workflow when another system calls Nimbus, pair it with the inbound webhook trigger described under Triggers and actions.

## Prerequisites

- **The API's documentation**, including its base URL, how it authenticates, and what it returns on errors.
- **Credentials for one of the supported authentication types:** none, an API key sent in a header, basic auth (username and password), or OAuth 2.0 client credentials (token URL, client ID, client secret and any scope or audience the API requires).
- **HTTPS.** Plain HTTP URLs are refused when the connection is saved.
- **Network reachability.** The API must be reachable from the internet. An internal API inside the client's network can be called through the private connector agent on Enterprise.
- **A Builder or Admin** to create the connection. Each HTTP Request connection used by an active workflow counts as an active connector; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Creating the connection

1. In the Nimbus admin console, open **Connections > New connection** and choose **HTTP Request**.
2. Enter a **Base URL**, for example `https://erp.client.example/api`. Steps add paths to it, so leave off the trailing slash.
3. Pick the **Authentication** type and fill in its fields:

| Authentication | Fields | What Nimbus sends |
|---|---|---|
| None | none | No credentials. |
| API key header | Header name, key | The key in the named header, e.g. `X-Api-Key: <key>`. |
| Basic auth | Username, password | `Authorization: Basic <base64 of username:password>`. |
| OAuth 2.0 client credentials | Token URL, client ID, client secret, scope, audience | Fetches an access token from the token URL and sends `Authorization: Bearer <token>`. |

4. Optionally add **Default headers** sent with every request, such as `Accept: application/json`.
5. Click **Save and test**, enter a harmless path to call (a health or "who am I" endpoint), and check the status Nimbus shows.

For OAuth 2.0 client credentials, Nimbus caches the access token until it expires and fetches a new one automatically. If the API answers 401 with a token Nimbus believed valid, Nimbus fetches a fresh token once and repeats the request before failing the step.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| Send request | Action | Sends one HTTPS request to a path under the base URL and returns `status`, `headers` and `body`. |

There are no triggers. When another system needs to start the workflow, use an **Inbound webhook** trigger: Nimbus gives the workflow a unique URL of the form `https://hooks.nimbus.omnicorp.example/t/<trigger-token>`, the sender POSTs JSON of up to 1 MB to it, and Nimbus answers `202 Accepted` with the run id. The workflow can then call back to the sender, or anywhere else, with **Send request**. For systems that should be polled rather than call in, use a **Schedule** trigger followed by a **Send request** step.

## Field mapping

**Send request** takes a method (GET, POST, PUT, PATCH or DELETE), a path, query parameters, headers and, for POST, PUT and PATCH, a JSON body. Every one of these fields accepts expressions. This step creates an order in the client's ERP from an inbound webhook and passes a per-environment API region plus a key from the secrets vault in extra headers:

```http
POST /orders?source=nimbus
Content-Type: application/json
X-Partner-Key: {{secrets.ERP_PARTNER_KEY}}
X-Region: {{env.ERP_REGION}}

{
  "external_ref": "{{trigger.body.order.id}}",
  "customer_email": "{{lower(trigger.body.customer.email)}}",
  "lines": "{{trigger.body.order.lines}}",
  "requested_at": "{{now()}}"
}
```

The response body is parsed according to its `Content-Type`. JSON responses are available field by field to later steps, for example `{{steps.create_order.output.body.order_number}}`; any other content type is returned as text in `body`, and binary responses as a file. Response headers are available as `{{steps.create_order.output.headers.location}}`, with header names in lower case.

## Limits and behaviour

**Non-2xx responses.** With **Fail on non-2xx** switched on (the default), any status outside 200-299 fails the step with the matching connector error, shown in the table below. Switch it off when the workflow should decide for itself, for example to treat a 404 as "not found, create it": the step then succeeds whatever the status, and a condition step can branch on `{{steps.<step-key>.output.status}}`.

**Retries.** A failed step is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes, configurable from 0 to 5 per step. Retries resend the same request, so for POST requests to APIs without idempotency support set retries to 0, or send an idempotency header the API recognises, to avoid creating duplicate records. When the API answers 429, Nimbus waits at least as long as the API's own `Retry-After` header asks before retrying.

**Timeouts and sizes.** Each request times out after 60 seconds by default; the timeout can be raised up to the 10-minute step limit, beyond which the step fails with WF-200. Request bodies and responses returned as files can be up to 100 MB.

**Redirects.** Redirects to another HTTPS URL are followed up to 5 times. Credentials are not forwarded when a redirect leaves the base URL's host.

## Troubleshooting

| Error | HTTP status from the API | Fix |
|---|---|---|
| CONN-401 | 401, or the OAuth token URL rejected the client ID and secret. | Check the credentials on the connection and click **Reconnect** after updating them. |
| CONN-403 | 403 | The credentials work but lack permission for this path or method; ask the API owner. |
| CONN-404 | 404 | Check the path against the base URL; a doubled or missing slash is a common cause. |
| CONN-429 | 429 | The API throttled Nimbus; the step is retried after a back-off. |
| CONN-503 | 500-599, a connection failure, or the private connector agent is offline. | Check the API's status, or the agent under **Settings > Agents**. |
| WF-400 | none (the request wasn't sent) | A body or header expression resolved to empty or produced invalid JSON. |
| WF-200 | none | The request ran past the 10-minute step limit. |

Other 4xx statuses, such as 400 or 422, fail the step with the API's response body in the step log, which usually names the field the API rejected.
