---
id: nimbus-admin-api-keys
title: Creating and Rotating API Keys
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-05-18
owner: Workspace Administration Team
---

An API key is how a client's own systems authenticate to the OmniCorp Nimbus REST API: a CI pipeline that deploys workflows, a script that offboards users, a data warehouse job that reads run results. Admins create keys in the admin console, and each key is a long random secret that the calling system sends with every request.

This guide covers creating a key, naming it so that it can be traced, rotating it without an outage and revoking it. For the limits the API enforces and the headers it returns, see [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Before you begin

- **Role:** you need the Admin role. Builders and Viewers don't see **Settings > Developers**.
- **Plan Tier:** the workspace must be on a tier that includes API access. On other tiers the API keys page shows an upgrade notice in place of the **Create API key** button; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- **A safe place for the key:** the key is shown once. Decide before you start where it will live, for example the client's own secrets manager or their CI system's protected variables, and who will paste it there.
- **One key per integration:** agree with the client which system the key is for. A key shared between several systems can't be rotated or revoked for one of them alone.

## How it works

A key belongs to the workspace, not to the Admin who created it, so it keeps working when that Admin is suspended or leaves. It is sent as a bearer token:

```http
GET /runs?status=failed&limit=50 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

Keys have no scopes. Every key acts with Admin permissions in its workspace, so a key for a reporting script can also delete users or change webhook endpoints. Treat every key as an Admin credential: store it in a secrets manager, never in source code or a shared spreadsheet, and give each integration its own.

Each key has these properties:

| Property | Notes |
|---|---|
| Name | Free text up to 80 characters, shown in the key list and the audit log. |
| ID | A `key_` id used in the API and the audit log. Not secret. |
| Last four | The last four characters of the secret, shown so a key found in a config file can be matched to its entry. |
| Expiry date | Optional. After this date the key is rejected with 401 `unauthorized`. Admins are emailed 7 days before it. |
| Created by, Created | The Admin who created it and when. |
| Last used | The time of the most recent authenticated request. |

The secret itself is shown once, when the key is created. Nimbus stores only a hash, so neither the client's Admins nor OmniCorp support can show it again; a lost key is replaced, not recovered.

Revoking a key takes effect immediately: the next request that uses it gets HTTP 401. There is no way to restore a revoked key.

## Step-by-step

To create a key:

1. Open **Settings > Developers > API keys** and click **Create API key**.
2. Enter a **Name** that says which system uses the key and where, for example `ci-deploy-prod (GitHub Actions)` or `warehouse-run-export`.
3. Optionally set an **Expiry date**. Many clients' security policies call for keys that expire within a year.
4. Click **Create**. Copy the key from the dialog with **Copy** and store it before you close the dialog.

The API equivalent, made with an existing key, is:

```http
POST /api-keys HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <existing-api-key>
Content-Type: application/json

{"name": "warehouse-run-export", "expires_at": "2027-06-30T23:59:59Z"}
```

The response includes the `id` and, this once, the full `key`. `GET /api-keys` lists keys without their secrets, and `DELETE /api-keys/{id}` revokes one.

### Rotating a key without downtime

Several keys can be valid at once, which makes rotation a matter of overlap:

1. Create a new key named for the same integration, for example `warehouse-run-export 2026-11`.
2. Put the new key in the client's secrets manager and deploy or restart the integration so that it picks it up.
3. Watch **Last used** on both keys. When the old key has shown no use for at least one full cycle of the integration (a nightly job needs a day), it is safe to remove.
4. Revoke the old key with **Revoke** in its row menu, or `DELETE /api-keys/{id}`.

## Verifying the change

A new key works when a harmless read such as `GET /workspace` returns 200 with it. In the key list, **Last used** updates within a minute of that request. After revoking, the same request returns 401 `unauthorized`, and the key shows **Revoked** with the revocation time. Creations and revocations appear in **Settings > Audit log** as `api_key.created` and `api_key.revoked`, with the key's name and the Admin who acted; see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every request returns 401 `unauthorized` | The key was revoked, has expired, or was copied with a missing character. | Check its status and expiry in the list; compare its last four characters; create a new key if needed. |
| 401 after it worked for months | The key reached its expiry date. | Rotate to a new key and set a later expiry, or none. |
| The key was pasted into a ticket or chat | It is exposed. | Rotate it at once and revoke the exposed key. |
| Nobody knows which system uses an old key | It was named vaguely. | Note **Last used**, revoke it during a quiet period and see what breaks, or ask the client to search their configs for a key ending in its last four characters. |
| 401 right after an Admin left the client | Not caused by the departure; keys belong to the workspace. | Look for an expiry or a revocation in the audit log. |
| No **Create API key** button | The Plan Tier doesn't include API access. | Discuss an upgrade with the client. |
