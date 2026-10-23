---
id: nimbus-release-3-0
title: Nimbus 3.0 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2025-04-07
owner: Release Management
---

Nimbus 3.0.0 was released on 2025-04-07 and marks the general availability of Platform Version v3. Every new workspace created from that date runs on v3, and existing v2 workspaces move across when their CSM books the upgrade with OmniCorp support. v2 is now deprecated and receives security fixes only; its end-of-support date and the full list of legacy behaviour are in the [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

These notes list what is new, what changed shape, and what a client has to adjust before or during the upgrade. Where a change has fixed values (limits, header names, attribute names), the notes point to the reference Article that owns those values rather than repeating them here.

## Highlights

- Per-tier API rate limits with a short burst allowance, and rate-limit headers on every API response.
- A new webhook signature scheme, plus automatic disabling of endpoints that keep failing.
- The SAML email attribute is now `email`.
- SCIM 2.0 user provisioning for Enterprise workspaces.
- A third data region, APAC, for Enterprise workspaces.
- A redesigned admin console built around the **Settings** menu, cursor-based API pagination and structured API error codes.

## New features

### API and webhooks

The API now applies a sustained request limit per Plan Tier, with a burst allowance on top for short spikes. Each tier's values are listed in [API Rate Limits and Webhooks](nimbus-api-webhooks.md). Responses carry `X-RateLimit-Limit` and `X-RateLimit-Remaining`, so a client can slow down before it is throttled, and a throttled request comes back with a `Retry-After` header.

Webhook deliveries use a new, stronger signature in a new header. Receivers that verify signatures need new verification code; the header name, digest format and a verification example are in the same Article. An endpoint that keeps failing is now switched off automatically instead of being retried indefinitely, and an Admin re-enables it under **Settings > Developers > Webhooks** once the receiver is fixed. Each delivery also carries its delivery id in `X-Nimbus-Delivery`, which receivers can use to discard duplicates.

API keys created under **Settings > Developers > API keys** can now be given an optional expiry date, and webhook signing secrets can be rolled without deleting the endpoint.

### Identity and data residency

SCIM 2.0 provisioning arrives for Enterprise workspaces: users are created, updated and suspended from the identity provider rather than by hand. Setup for Okta and Microsoft Entra ID is in [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md). SAML group attributes are now read and mapped to Nimbus roles; see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md).

APAC joins EU and US as a data region for Enterprise workspaces. The region is chosen when a workspace is created and can't be changed afterwards, so a client that wants its data in APAC creates a new Enterprise workspace there and migrates its workflows. Residency details are in [Data Residency](nimbus-security-data-residency.md).

The connector catalogue at general availability covers Salesforce, HubSpot, Slack, Jira Cloud, Zendesk, Amazon S3, PostgreSQL, MySQL, SharePoint Online, Box, Dropbox, GitHub, Asana, BambooHR, Twilio, SFTP and the generic HTTP Request connector.

## Improvements

- Run history (inputs, outputs and step logs) is now kept for 90 days on every Plan Tier.
- Run statuses are standardised as `queued`, `running`, `succeeded`, `failed`, `cancelled` and `timed_out`, and every failure carries a WF- or CONN- error code in run history and in `GET /runs/{id}/steps`.
- A failed connector step is retried 3 times by default after 30 seconds, 2 minutes and 10 minutes; the count can be set from 0 to 5 per step.
- Schedule triggers accept a cron expression in the workspace time zone or in any chosen IANA time zone.
- All API ids are prefixed by type (`wf_`, `run_`, `usr_`, `con_` and so on), which makes log lines easier to read.
- Console sessions have an idle timeout an Admin can set under **Settings > Security > Sessions**.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-4102 | The run history filter by status ignored runs that had been cancelled from the API. |
| NIM-4109 | A cron expression with a step value in the day-of-week field was saved but never fired. |
| NIM-4115 | Renaming a connection did not update its name in the step picker until the builder was reloaded. |
| NIM-4121 | Invitation emails were sent in the inviting Admin's browser language instead of English. |
| NIM-4128 | Large step outputs were truncated in the run detail view without any notice. |
| NIM-4133 | The SFTP connector failed to list directories whose names contained a space. |
| NIM-4140 | Exporting run history while a run was in progress could produce a file with a duplicated header row. |

## Deprecations and breaking changes

Workflows, connections and run history move across unchanged, but several client-facing interfaces change shape. Each item below needs action on the client's side if the client uses it.

- **Admin console.** The **Admin** menu is replaced by **Settings**. Users are under **Settings > Users**, API keys under **Settings > Developers > API keys**, webhooks under **Settings > Developers > Webhooks**, and connections under **Connections**.
- **Pagination.** List endpoints switch from page numbers to cursors. Requests use `limit` (default 25, maximum 100) and `cursor`; responses carry `data` and `next_cursor`, which is null on the last page. `page`, `per_page` and `total` are no longer accepted or returned.
- **Error bodies.** Errors are returned as `{"error": {"code": "...", "message": "..."}}` with codes such as `invalid_request`, `not_found` and `rate_limited`. Clients that matched on message text should match on `code` instead.
- **Webhook verification.** The old signature header is not sent by v3 workspaces. Receivers must verify the new header before the upgrade.
- **SAML attribute.** The identity provider must send the user's address in the `email` attribute; see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md).

## Upgrade notes

1. Ask the client's CSM to book the upgrade with OmniCorp support. The switch itself takes under an hour, and workflows keep their schedules.
2. Before the booked slot, update every webhook receiver to verify the new signature header, following [API Rate Limits and Webhooks](nimbus-api-webhooks.md).
3. In Okta or Microsoft Entra ID, change the Nimbus app's attribute statement so the address is sent as `email`.
4. Update API clients to use cursor pagination and to read `error.code`. A paged request looks like this:

```http
GET /runs?limit=100&cursor=eyJpZCI6InJ1bl84ZjJhIn0 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json
X-RateLimit-Limit: <tier limit>
X-RateLimit-Remaining: <remaining>

{"data": [{"id": "run_8f2b", "status": "succeeded"}], "next_cursor": null}
```

5. After the upgrade, open **Settings > Plan** to confirm the Plan Tier and effective limits, and send a test delivery from **Settings > Developers > Webhooks** to each endpoint.
6. Enterprise clients that want SCIM provisioning set it up only after SAML single sign-on is working with the same identity provider.
