---
id: nimbus-release-2-16-3
title: Nimbus 2.16.3 Release Notes
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: release-notes
status: deprecated
last_updated: 2026-04-13
owner: Release Management
---

Nimbus 2.16.3 is a security-fix release for the legacy platform, applied to every workspace on 2026-04-13. It fixes four vulnerabilities, two of them in how stored credentials and signing secrets were handled in the console, and updates the components that had published security advisories. There are no new features.

This is also a reminder that the legacy platform is close to the end of its support period. Every client still on it should have an upgrade date agreed with their CSM; the timeline and the upgrade checklist are in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Highlights

- Saved connection passwords and tokens are no longer sent back to the browser when an Admin edits a connection.
- A webhook endpoint's signing secret is shown only once, at registration, and is no longer returned when the endpoint is read again.
- Inviting an address that already has an account returns the same response as any other invitation, so the Users API can't be used to discover who has an account.
- Clients that haven't planned their move to the current platform should do so now with their CSM.

## New features

There are no new features in 2.16.3, and none will follow: the 2.16.x line carries security fixes only. Every workflow, connector, API call and console page works exactly as it did after 2.16.2.

## Improvements

Apart from the fixes listed below, the release updates third-party components:

| Component | Where it runs | Reason |
|---|---|---|
| TLS library | Console, API, sign-in service | Published advisory affecting certificate checks |
| JSON parser | API and run workers | Excessive memory use on deeply nested input |
| HTTP client | Connectors and webhook delivery | Header injection through redirects |
| Base operating-system image | Run workers | Routine security updates |

No configuration or behaviour visible to clients changes because of these updates.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-2953 | Opening a connection for editing under Admin > Connections placed the saved password or token in the page's hidden form field. Credentials are now kept on the server only; to change one, type the new value into the connection. |
| NIM-2958 | Reading a webhook endpoint under Admin > Webhooks after registration returned its signing secret again. The secret is now shown once, when the endpoint is registered. |
| NIM-2961 | Inviting a user through the Users API returned a different error for addresses that already had an account, which allowed accounts to be discovered one address at a time. |
| NIM-2967 | A very large or deeply nested JSON body sent to the API could tie up a worker for several seconds before being rejected. Such bodies are now refused early with HTTP 400. |

None of these issues is known to have been exploited. Clients who want the full advisory for an issue can ask their CSM, who requests it from OmniCorp support.

## Deprecations and breaking changes

Nothing breaks for workflows, connectors or webhook receivers. Two console and API behaviours change slightly:

- The password and token fields of a connection now open empty instead of masked. Leaving a field empty keeps the stored value; typing into it replaces it.
- An invitation to an address that already has an account returns the same success response as a new invitation. No second account is created and no email is sent to the existing user, so scripts that relied on the old error to detect existing users must check `GET /users` first.

The legacy platform itself is deprecated. No new releases other than security fixes are planned before its end of support, and after that date nothing is fixed. The date and what happens to workspaces still on it afterwards are in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Upgrade notes

2.16.3 itself needs no action; OmniCorp has applied it to every workspace. What clients do need is a plan to leave the legacy platform. For each client account still on it, the CSM should:

1. Agree an upgrade date with the client, well before the end of support.
2. Go through the three preparation items in the "Upgrading to v3" section of [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md) with the client's technical contact: webhook verification code, API limits for their Plan Tier, and the identity provider's attribute statements.
3. Take an inventory of what the client runs, so nothing is missed after the move. The API calls below list users and workflows; Admin > Connections and Admin > Webhooks show the rest.
4. Book the upgrade window with OmniCorp support. The upgrade takes under an hour, during which runs are paused and queued.
5. After the upgrade, check sign-in, one webhook delivery and one run of each important workflow with the client.

The inventory calls use page-based pagination, so read `total` and keep increasing `page` until every item has been fetched:

```bash
curl -s -H "Authorization: Bearer <api-key>" \
  "https://api.nimbus.omnicorp.example/workflows?page=1&per_page=100"

curl -s -H "Authorization: Bearer <api-key>" \
  "https://api.nimbus.omnicorp.example/users?page=1&per_page=100"
```

A typical response ends with the count that tells the script when to stop:

```json
{"data": [{"id": "wf_3391", "name": "Nightly invoice sync", "active": true}], "page": 1, "per_page": 100, "total": 1}
```

For the legacy endpoints' full field lists, see [Workflows API (v2)](nimbus-v2-api-workflows.md) and [Users API (v2)](nimbus-v2-api-users.md).
