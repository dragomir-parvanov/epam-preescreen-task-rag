---
id: nimbus-faq-upgrading-from-v2
title: Upgrading from v2 FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-09-21
owner: Customer Success Enablement
---

Clients still on the legacy platform ask their CSM the same questions before agreeing an upgrade date: who arranges it, how long the workspace is unavailable, what comes across, and what their own developers and identity team have to change. This FAQ answers those questions for the move from v2 to v3.

The legacy platform itself, including its support timeline, is described in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md). For the exact values that differ on v3, such as webhook signature details, API limits and SAML attribute names, follow the links below rather than quoting them from this page.

## General questions

**Who books the upgrade?**

The client's CSM. Once the client has confirmed that their side is ready, the CSM books an upgrade window with OmniCorp support through the internal upgrade request form, giving the workspace id, the preferred date and time in the client's time zone, and a named technical contact on the client side. Clients can't start the upgrade themselves from the console.

**How long does it take, and what happens during it?**

The upgrade itself takes under an hour. During the window, workflow runs are paused and queued rather than dropped, and they start once the workspace is back. Book the window outside the client's busiest processing hours so the queue clears quickly afterwards.

**What carries over?**

Workflows, connectors and their connections, users and run history are carried over, and the workspace keeps its data region and Plan Tier. Users keep their roles and their passwords. Inbound webhook trigger URLs keep working.

**Why upgrade now rather than later?**

The legacy platform receives security fixes only, and every new feature and connector ships on v3. After upgrading, clients gain workflow version history, Development and Production environments, approval steps, the secrets vault, the usage dashboard, the `Idempotency-Key` header and, on Enterprise, SCIM provisioning. Run history is also kept for 90 days instead of 30.

## Setup questions

**What do the client's developers need to change?**

The table lists every change that touches the client's own systems:

| Area | What changes | Where it is documented |
|---|---|---|
| Webhook verification | New signature header and algorithm | [API Rate Limits and Webhooks](nimbus-api-webhooks.md) |
| API request limits | Limits depend on the Plan Tier; Starter has no API access | [Plan Tiers and Entitlements](nimbus-plan-tiers.md) |
| SAML sign-in | The email attribute name changes | [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) |
| API pagination | Page numbers are replaced by cursors | [Workflows API](nimbus-api-workflows.md) |
| API errors | Errors gain a machine-readable code | [API Error Format and Idempotency](nimbus-api-error-format.md) |
| Admin console | The Admin menu becomes Settings | [Managing Workspace Settings](nimbus-admin-workspace-settings.md) |

**How does pagination change?**

The legacy API pages with `page` and `per_page` and returns a `total`. v3 is cursor-based: pass `limit` (default 25, maximum 100), then the `next_cursor` from each response as `cursor`, until `next_cursor` is null. A loop that keeps incrementing `page` will simply receive the first page again, so update every list call:

```http
# Before the upgrade
GET /runs?page=3&per_page=100

# After the upgrade
GET /runs?limit=100
GET /runs?limit=100&cursor=eyJvZmZzZXQiOjEwMH0
```

### How do we prepare for the upgrade?

Work through these steps with the client before booking the window:

1. List every system that receives Nimbus webhooks, and have its owner prepare the new verification code from [API Rate Limits and Webhooks](nimbus-api-webhooks.md), ready to deploy straight after the upgrade.
2. Check the client's Plan Tier against [Plan Tiers and Entitlements](nimbus-plan-tiers.md). A Starter workspace that uses the API today must upgrade its tier, or its integrations stop.
3. Have the identity team prepare the attribute change from [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) and name someone to run a test sign-in right after the upgrade.
4. Update API clients for cursor pagination and the new error body.
5. Tell the client's Builders the date: workflows can't be edited or published while the window is open.
6. Ask the CSM to book the window, and share the date with everyone named above.

## Limits and edge cases

**Can a workspace go back to the legacy platform afterwards?**

No. The upgrade is one-way, which is why the preparation steps above matter.

**Do API keys change?**

Existing keys keep working. On v3 they can also be given an expiry date, and new keys are created under Settings > Developers > API keys.

**Do webhook endpoints keep their signing secrets?**

Yes, existing endpoints and their secrets carry over; only the signature format changes. On v3 the secret can also be rolled without deleting the endpoint.

**Does the upgrade change the data region?**

No. The workspace stays in the region it was created in, and the region still can't be changed later.

## Troubleshooting questions

**After the upgrade, the client's webhook receiver rejects every delivery.**

The receiver is still checking the legacy signature. Deploy the verification code prepared in step 1; until then, failed deliveries are retried as described in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

**SSO users can't sign in after the upgrade.**

The identity provider is still sending the email under the old attribute name. Apply the change from [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) and retry the test sign-in.

**An integration fails to parse error responses.**

v3 returns errors as an object with `code` and `message` instead of a plain message string:

```json
{"error": {"code": "not_found", "message": "No workflow with id wf_3Lx8Ra"}}
```

**A Starter client's integration now gets 403.**

The workspace's tier has no API access on v3. See [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Where to find more

- [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md) and [Legacy Platform FAQ (v2)](nimbus-v2-faq.md).
- [Nimbus 3.0 Release Notes](nimbus-release-3-0.md) for everything v3 introduced.
- [API Rate Limits and Webhooks](nimbus-api-webhooks.md), [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) and [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
