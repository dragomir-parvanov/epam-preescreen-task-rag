---
id: nimbus-security-encryption
title: Encryption in Transit and at Rest
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-06
owner: Security & Compliance
---

This note answers the encryption questions that come up in a client's security questionnaire: how Nimbus protects data on the wire, how it protects stored data, who holds the keys, and what changes when an Enterprise client brings its own key. Customer-managed keys arrived in release 3.6.0 (2026-04-06); everything else described here has been in place since v3 became generally available.

The short answer for a questionnaire is: TLS 1.2 or later in transit, AES-256 at rest, keys managed by OmniCorp by default, and customer-managed keys in AWS KMS or Azure Key Vault on the Enterprise tier.

## Scope

The note covers three paths. First, traffic between the client and Nimbus: browsers on the admin console, API clients, identity providers posting SSO responses, and apps calling inbound webhook triggers. Second, traffic that Nimbus starts: connector calls to third-party apps, webhook deliveries to the client's endpoints, and the link to a private connector agent. Third, everything Nimbus stores: workflow definitions and versions, run history, connection credentials, secrets, the audit log, and the backups of all of these.

It doesn't cover how a credential is decrypted and masked during a run, which is in [How Connection Credentials and Secrets Are Stored](nimbus-security-credential-storage.md), or where the data physically lives, which is in [Data Residency](nimbus-security-data-residency.md).

## Controls in place

### In transit

Every public Nimbus hostname accepts TLS 1.2 or later only: `app.nimbus.omnicorp.example`, `api.nimbus.omnicorp.example`, `login.nimbus.omnicorp.example` and `hooks.nimbus.omnicorp.example`. Connections that offer only TLS 1.0 and TLS 1.1 are refused during the handshake, and plain HTTP requests to the console are redirected to HTTPS with an HSTS header so the browser doesn't try HTTP again.

Outbound traffic follows the same floor. Connector steps call third-party APIs over HTTPS; the PostgreSQL, MySQL and Microsoft SQL Server connectors refuse to connect unless the database negotiates TLS; and a private connector agent opens an outbound TLS connection to Nimbus, so nothing on the client's network has to accept inbound traffic. Webhook endpoints must be registered with an `https://` URL; the console rejects `http://` addresses when the endpoint is saved.

### At rest

All stored data is encrypted with AES-256. Nimbus uses envelope encryption: each workspace has its own data-encryption keys, and those keys are themselves encrypted (wrapped) by a key-encryption key. By default the key-encryption key is held in OmniCorp's key management service, rotated by OmniCorp every year, and never leaves that service in plaintext; OmniCorp engineers have no way to export it.

| Data | Encrypted at rest | Wrapped by a customer-managed key (Enterprise) |
|---|---|---|
| Workflow definitions and version history | AES-256 | Yes |
| Run history, step inputs, outputs and logs | AES-256 | Yes |
| Connection credentials and OAuth tokens | AES-256, plus a separate per-workspace key | Yes |
| Secrets vault values | AES-256, plus a separate per-workspace key | Yes |
| Audit log | AES-256 | Yes |
| Backups | AES-256 | Yes |

With a customer-managed key, the client's key replaces OmniCorp's key-encryption key for that workspace. Nimbus asks the client's key service to unwrap the workspace's data keys when it needs them and holds the unwrapped keys in memory only.

## Admin settings

TLS and OmniCorp-managed encryption at rest are always on and have no settings. A customer-managed key is set up by an Admin of an Enterprise workspace under **Settings > Security > Encryption keys** (see [Customer-Managed Encryption Keys](nimbus-tier-customer-managed-keys.md) for the tier details):

1. Create the key in the client's own cloud account, in the same geography as the workspace's data region. In AWS KMS use a symmetric encryption key; in Azure Key Vault use an RSA key of 2048 bits or more.
2. Grant Nimbus access to the key. The **Encryption keys** page shows the Nimbus principal to grant: an IAM role ARN for AWS, or an application (client) ID for Azure. AWS needs `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` and `kms:DescribeKey`; Azure needs the **Get**, **Wrap Key** and **Unwrap Key** key permissions.
3. In Nimbus, click **Add key**, choose **AWS KMS** or **Azure Key Vault**, and paste the key ARN or the key identifier URL.
4. Click **Validate**. Nimbus wraps and unwraps a test value with the key and reports any missing permission by name.
5. Click **Activate**. Nimbus re-wraps the workspace's data keys with the new key in the background; workflows keep running while it does, and the page shows **Active** when it has finished.

A key-policy statement for AWS KMS looks like this:

```json
{
  "Sid": "AllowNimbusWorkspaceKeyUse",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::444455556666:role/nimbus-cmk-access" },
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
  "Resource": "*"
}
```

If the client disables the key, deletes it, or removes Nimbus's permissions, Nimbus can no longer unwrap the workspace's data keys. The console shows an **Encryption key unavailable** banner, no new runs start, and data can't be read until access is restored. OmniCorp can't recover a workspace whose customer-managed key has been permanently deleted.

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| TLS on Nimbus hostnames | Configures TLS 1.2 or later, certificates and HSTS | Uses clients and libraries that support TLS 1.2 or later |
| TLS to connected systems | Requires TLS for connector calls and database connectors | Keeps TLS enabled and certificates valid on their own databases, SFTP servers and webhook endpoints |
| Encryption at rest | Encrypts all stored data with AES-256 | Nothing, unless they use a customer-managed key |
| OmniCorp-managed keys | Generates, stores and rotates the key-encryption key | Nothing |
| Customer-managed keys | Calls the key only to wrap and unwrap data keys; reports failures in the console | Creates the key, grants and keeps Nimbus's permissions, rotates it, and never deletes it while the workspace is in use |

## Evidence for auditors

Clients usually ask for four things:

- **Independent assurance.** OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate both cover the encryption controls above. The CSM shares them under NDA; see [Compliance Reports and Certifications](nimbus-security-compliance-reports.md).
- **Proof of TLS settings.** The client can run any public TLS scanner against the four Nimbus hostnames and keep the result; it will show TLS 1.2 and 1.3 offered and older protocols refused.
- **Key-management events.** Adding, validating and activating a customer-managed key are recorded in the audit log as `encryption_key.added`, `encryption_key.validated` and `encryption_key.activated`, with the acting Admin. Export them from **Settings > Audit log**, as described in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).
- **Key usage on the client side.** With a customer-managed key, every wrap and unwrap request from Nimbus appears in the client's own AWS CloudTrail or Azure Key Vault logs, which is often the strongest evidence an auditor will accept.
