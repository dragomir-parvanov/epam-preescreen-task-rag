---
id: nimbus-release-3-6
title: Nimbus 3.6 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2026-04-06
owner: Release Management
---

Nimbus 3.6.0 was released on 2026-04-06 for every v3 workspace. Both of its new features are for Enterprise workspaces: customer-managed encryption keys, which let a client protect its Nimbus data with a key held in its own AWS KMS or Azure Key Vault, and audit-log streaming, which sends audit events to Splunk, Datadog or an HTTPS endpoint as they happen.

Starter and Business workspaces receive the improvements and fixes in these notes only. Questions from security teams about either feature are usually answered by [Customer-Managed Encryption Keys](nimbus-tier-customer-managed-keys.md) and [Audit Log Streaming](nimbus-tier-audit-log-streaming.md).

## Highlights

- Enterprise workspaces can wrap their data keys with a customer-managed key in AWS KMS or Azure Key Vault, configured under **Settings > Security > Encryption keys**.
- Enterprise workspaces can stream audit events continuously to Splunk, Datadog or any HTTPS endpoint, configured under **Settings > Audit log > Streaming**.
- Encryption in transit (TLS 1.2 or later) and at rest (AES-256) is unchanged for every workspace.

## New features

### Customer-managed encryption keys

Nimbus encrypts each workspace's data with AES-256 data keys. With a customer-managed key, those data keys are themselves encrypted (wrapped) by a key the client controls, so revoking Nimbus's access to that key makes the workspace's stored data unreadable to Nimbus. The key protects connection credentials, secrets in the secrets vault, and run inputs, outputs and step logs.

An Admin sets it up in three parts: choose the provider, enter the key reference (an AWS KMS key ARN, or an Azure Key Vault key identifier), and grant the Nimbus service principal shown on the page permission to use the key. **Verify access** then performs a test wrap and unwrap before the key can be activated. Activation re-wraps existing data keys in the background, and the page shows progress; workflows keep running throughout.

Key rotation in AWS KMS or Azure Key Vault needs no action in Nimbus, as the provider keeps earlier key versions available for unwrapping. If the key is disabled, deleted, or Nimbus's permission is removed, Nimbus stops starting new runs, scheduled runs are skipped, and every user sees an **Encryption key unavailable** banner; nothing is deleted, and the workspace resumes once access is restored. An Admin can also switch back to OmniCorp-managed keys from the same page. Background on encryption is in [Encryption in Transit and at Rest](nimbus-security-encryption.md).

### Audit-log streaming

Audit-log streaming forwards each audit event to an external system shortly after it is recorded, in the same JSON shape returned by `GET /audit-log/events`. An Enterprise workspace can configure up to three destinations:

| Destination | What the Admin enters | Notes |
|---|---|---|
| Splunk | HTTP Event Collector URL and HEC token; optional index and source type | Events arrive with source type `nimbus:audit` unless overridden |
| Datadog | Datadog site (for example `datadoghq.eu`) and an API key | Events arrive as logs with `source:nimbus` |
| HTTPS endpoint | URL and an optional header name and value for authentication | Nimbus sends batches as `POST` with a JSON array body |

Each destination has a **Send test event** button and a status of **Active**, **Failing** or **Paused**. When a destination rejects deliveries, Nimbus retries with backoff and marks it **Failing** on the page; events that could not be delivered remain searchable and exportable under **Settings > Audit log**. Streaming copies events; it doesn't change how long Nimbus keeps them in the console, which is set by the Plan Tier (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)). The event types are listed in [Audit Log Event Catalogue](nimbus-security-audit-events.md).

## Improvements

- Configuring, verifying, activating and removing a customer-managed key are recorded as audit events.
- **Settings > Audit log** search accepts a list of actions, not just one.
- `GET /audit-log/events` accepts several `action` values separated by commas.
- The step log viewer loads large logs in pages instead of all at once.
- Run detail pages show which connection each step used.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-5046 | The usage dashboard's daily chart showed runs in the browser's time zone instead of UTC. |
| NIM-5049 | `GET /workspace/usage` returned `percent_of_quota` as a string on some workspaces. |
| NIM-5053 | The 80% quota alert could be sent twice if two runs started in the same second. |
| NIM-5058 | Audit-log CSV exports wrapped long user-agent strings across two rows. |
| NIM-5062 | The Teams trigger stopped receiving channel messages after the channel was renamed. |
| NIM-5067 | A Snowflake connection test passed with an encrypted private key and a wrong passphrase. |

## Deprecations and breaking changes

Nothing breaks in 3.6. Neither feature is turned on by default. Clients that used to poll `GET /audit-log/events` to feed a security information and event management tool can keep doing so; streaming is an alternative, not a replacement. Clients that enable a customer-managed key take on responsibility for that key's availability, since removing Nimbus's access stops the workspace's runs.

## Upgrade notes

To enable a customer-managed key in AWS KMS:

1. Confirm the workspace is on the Enterprise tier under **Settings > Plan**.
2. In AWS KMS, create a symmetric key in the same geography as the workspace's data region.
3. Under **Settings > Security > Encryption keys**, choose **AWS KMS** and copy the Nimbus role ARN shown on the page.
4. Add a statement to the key policy that grants that role the operations below, replacing the placeholders:

```json
{
  "Sid": "AllowNimbusWorkspaceKeyUse",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::<nimbus-account-id>:role/nimbus-cmk-ws_4a1f9c"},
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
  "Resource": "*"
}
```

5. Paste the key ARN into Nimbus, select **Verify access**, then **Activate**.

For Azure Key Vault, grant the Nimbus service principal the **Get**, **Wrap Key** and **Unwrap Key** key permissions, or the Key Vault Crypto Service Encryption User role, before entering the key identifier. To start streaming, add a destination under **Settings > Audit log > Streaming**, send a test event, and check that it arrives before saving.
