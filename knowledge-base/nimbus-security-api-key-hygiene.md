---
id: nimbus-security-api-key-hygiene
title: API Key Security Practices
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-25
owner: Security & Compliance
---

A Nimbus API key is a powerful credential: whoever holds it can do anything an Admin can do in the workspace, from reading run history to deleting users. Clients reviewing their integrations want to know what Nimbus does to limit that risk and what they are expected to do themselves. This note sets out both, and gives CSMs the practices to recommend: keep keys in a secrets manager, give each integration its own key, set expiry dates, rotate, watch when each key was last used, and revoke at the first suspicion.

Creating and rotating keys step by step is covered in [Creating and Rotating API Keys](nimbus-admin-api-keys.md); the endpoints are in [API Keys API](nimbus-api-api-keys.md).

## Scope

The note covers the API keys an Admin creates under **Settings > Developers > API keys** for calls to `https://api.nimbus.omnicorp.example`. Which Plan Tiers include API access is set out in [Plan Tiers and Entitlements](nimbus-plan-tiers.md). It doesn't cover the SCIM token an identity provider uses, webhook signing secrets, or the credentials Nimbus holds for connected apps, which are in [How Connection Credentials and Secrets Are Stored](nimbus-security-credential-storage.md).

## Controls in place

An API key acts with Admin permissions in its workspace, and keys have no scopes. There is no read-only key and no key limited to one workflow, so the safeguards below are what stand between a leaked key and the whole workspace:

- **Shown once.** The key value is displayed only at creation. Nimbus stores a one-way hash of it, so neither the console, the API nor OmniCorp support can show it again. A lost key is replaced, not recovered.
- **Optional expiry date.** An Admin can give a key an expiry date at creation. After that date the key is rejected with 401 and the `unauthorized` error code.
- **Immediate revocation.** A revoked key gets 401 from the next request; there is no grace period and no cache to wait for.
- **Owned by the workspace.** A key belongs to the workspace, not to the Admin who created it, so suspending or deleting that Admin doesn't stop it. Only revocation, the key's expiry date or a downgrade to Starter does, which is why a leaver's keys are rotated rather than left to lapse.
- **Usage tracking.** Every key carries `created_by`, `created_at`, `expires_at` and `last_used_at`, shown in the console's **Last used** column and returned by `GET /api-keys`.
- **Audit trail.** Creating and revoking keys is logged as `api_key.created` and `api_key.revoked`, and every action taken with a key is logged with the key id (`key_…`) as the actor.

Keys are sent only in the `Authorization: Bearer <api-key>` header over TLS. Nimbus doesn't accept keys in query strings, which keeps them out of proxy and server access logs.

## Admin settings

To create a key that follows these practices:

1. Open **Settings > Developers > API keys** and click **Create API key**.
2. In **Name**, describe the one integration that will use it, for example `jira-sync-prod`, so the key's purpose is clear in the audit log.
3. Set **Expires on** to a date no further out than the client's rotation policy, for example 90 days ahead.
4. Click **Create**, copy the key, and paste it straight into the client's secrets manager (AWS Secrets Manager, Azure Key Vault or HashiCorp Vault). Don't send it by email or chat.
5. Before the expiry date, create the replacement key, deploy it, confirm its **Last used** time updates, then revoke the old key with **Revoke**.

### Reviewing keys

Review keys at least quarterly. The `last_used_at` field shows keys that nothing uses any more, which should be revoked:

```bash
curl -s "https://api.nimbus.omnicorp.example/api-keys?limit=100" \
  -H "Authorization: Bearer <api-key>" \
  | jq '.data[] | select(.last_used_at == null or .last_used_at < "2026-03-01") | {id, name, created_by, last_used_at}'
```

```json
{
  "id": "key_2Rn7Xb4Qe",
  "name": "bamboohr-onboarding-legacy",
  "created_by": "usr_3Fh8Wq2Kd",
  "last_used_at": "2026-01-14T06:00:12Z"
}
```

To revoke a key that may be exposed, for example one pushed to a public repository:

1. Revoke it at once from the console or with `DELETE /api-keys/{id}`; it gets 401 from the next request.
2. Create a replacement and deploy it to the integration.
3. Filter the audit log by the revoked key's id as actor to see what was done with it, and raise anything unexpected with the client's security team.

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Key generation | Generates random keys, shows them once and stores only a hash | Copies the key straight into a secrets manager |
| Permissions | Applies Admin permissions in the key's workspace, nothing beyond it | Limits who can create keys by limiting the Admin role |
| Expiry | Rejects keys after their expiry date | Sets an expiry date on every key |
| Rotation | Allows several keys at once so rotation needs no downtime | Rotates keys on a schedule and when staff with access leave |
| Monitoring | Records `last_used_at` and logs every action with the key id | Reviews unused keys and audit events regularly |
| Revocation | Rejects a revoked key from the next request | Revokes any key that may be exposed, without waiting |

### Practices to recommend

- One key per integration, never shared between systems, so revoking one doesn't break the others and the audit log shows which system acted.
- Keys live in a secrets manager or the CI system's secret store, never in source code, spreadsheets or tickets.
- When an Admin who saw a key's value leaves, rotate that key: suspending or deleting the Admin doesn't stop the key, because keys belong to the workspace.

## Evidence for auditors

A client can export the key inventory from `GET /api-keys`, showing every key's name, creator, expiry date and last use, and show that none is without an expiry date. The `api_key.created` and `api_key.revoked` events, exported from **Settings > Audit log** as described in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md), show rotation happening on schedule. If a key was revoked because of a suspected leak, the client should also keep the filtered audit export of that key's actions with its incident record. OmniCorp's handling of key hashes and revocation is covered by its SOC 2 Type II report and ISO/IEC 27001 certificate, available through the CSM under NDA.
