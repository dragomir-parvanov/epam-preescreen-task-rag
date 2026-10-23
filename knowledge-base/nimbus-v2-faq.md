---
id: nimbus-v2-faq
title: Legacy Platform FAQ (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-06-16
owner: Customer Success Enablement
---

Clients whose workspaces still run on the legacy platform ask a familiar set of questions: where a setting lives in the console, how to page through the API, why an older run has disappeared, how to change a stored password, and what they are missing. This FAQ answers them, and points to the legacy reference for API limits, webhook signatures, SAML attributes and the support timeline.

The legacy platform receives security fixes only. The most recent is 2.16.3, released on 2026-04-13; see [Nimbus 2.16.3 Release Notes](nimbus-release-2-16-3.md).

## General questions

**Where are the admin settings?**

Administration lives in the Admin menu in the top bar of the console. The pages CSMs are asked about most are:

| Page | What it is for |
|---|---|
| Admin > Users | Invite, change role and remove users |
| Admin > API keys | Create and delete API keys |
| Admin > Webhooks | Register and delete webhook endpoints |
| Admin > Connections | View, edit and delete connections |

There is no Settings menu, so instructions written for the current platform that start with "Settings >" don't apply to these workspaces.

**Is the platform still supported?**

It receives security fixes only, with no new features or connectors. The end-of-support date and what happens after it are set out in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md). Workspaces keep running after end of support, but nothing that breaks will be fixed.

**What isn't available, and why would a client upgrade?**

Several capabilities exist only on the current platform:

- No workflow version history: a published change overwrites the previous workflow.
- No Development and Production environments, and no approval steps.
- No secrets vault: credentials live only inside connections.
- No `Idempotency-Key` header on API requests.
- No SCIM provisioning; users are created by just-in-time provisioning or invited by an Admin.
- No APAC data region.
- No rate-limit headers on API responses.

Clients who need any of these should plan an upgrade with their CSM; see [Upgrading from v2 FAQ](nimbus-faq-upgrading-from-v2.md).

## Setup questions

**How do I change a password or token stored in a connection?**

Credentials are stored per connection. To change one, an Admin or Builder opens Admin > Connections, selects the connection, clicks Edit, enters the new value and clicks Save. Every workflow that uses the connection picks up the change on its next run. The saved value is never displayed again.

**How do I revoke an API key?**

API keys never expire. To revoke one, delete it under Admin > API keys; requests with that key are refused from then on. Create the replacement first and switch the integration over before deleting the old key.

### How do I page through API results?

List endpoints are page-based. Pass `page` (starting at 1) and `per_page` (default 50, maximum 100). Every list response carries `total`, the number of matching items across all pages:

```http
GET /runs?page=2&per_page=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {"id": "run_4Gm7Pz", "workflow_id": "wf_1Ck9Ds", "status": "succeeded"}
  ],
  "page": 2,
  "per_page": 100,
  "total": 412
}
```

To read a full list:

1. Request `page=1` with the largest useful `per_page`.
2. Divide `total` by `per_page` and round up to get the number of pages.
3. Request each remaining page in turn.
4. Stop early if a page comes back with an empty `data` array, since items can be deleted while the client is paging.

## Limits and edge cases

**How long is run history kept?**

Run history is kept for 30 days. Runs older than that, with their inputs, outputs and step logs, are removed and can't be restored. Clients who need longer records should export run details regularly through the Runs API.

**Do API errors have codes?**

No. An error response is `{"error": "<message>"}` with the HTTP status; there is no separate error code field. Integrations should branch on the status and log the message.

**Can a webhook signing secret be rolled?**

No. To replace a secret, delete the endpoint under Admin > Webhooks and register it again, then update the receiving system with the new secret it is shown. How deliveries are signed is described in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

**What happens to a webhook endpoint that keeps failing?**

There is no auto-disable. Delivery attempts continue until an Admin deletes the endpoint, so a decommissioned receiver should always be removed.

## Troubleshooting questions

**A client can't find a run from six weeks ago.**

Run history only goes back 30 days, so the run has been removed. If the client exported run details, the record is in that export.

**An integration's error handling expects error codes.**

Code written against the current platform's error format won't work here, because errors carry only a message. Branch on the HTTP status instead.

**The client's API calls are being refused with 429.**

The workspace has exceeded its API limit, which is shared by every key in the workspace. The limit and the `Retry-After` behaviour are documented in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

**A leaver can still sign in with a password.**

Users aren't removed automatically. An Admin removes the user under Admin > Users; see [Inviting and Removing Users (v2)](nimbus-v2-admin-managing-users.md).

## Where to find more

- [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md) for limits, webhooks, SAML and the support timeline.
- [Managing API Keys (v2)](nimbus-v2-admin-api-keys.md) and [Runs API (v2)](nimbus-v2-api-runs.md).
- [Troubleshooting Workflow Runs (v2)](nimbus-v2-troubleshooting-workflow-runs.md).
- [Upgrading from v2 FAQ](nimbus-faq-upgrading-from-v2.md) for moving to the current platform.
