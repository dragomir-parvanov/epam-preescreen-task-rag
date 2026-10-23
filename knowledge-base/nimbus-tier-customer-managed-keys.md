---
id: nimbus-tier-customer-managed-keys
title: Customer-Managed Encryption Keys
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-05-11
owner: Product Operations
---

Every Nimbus workspace is encrypted at rest with AES-256. By default OmniCorp manages the keys. With customer-managed encryption keys, an Enterprise client keeps the top-level key in their own AWS KMS or Azure Key Vault, and Nimbus can only read the workspace's data while the client lets it use that key. The client can audit every use of the key in their own cloud account and can cut Nimbus off by revoking access.

The feature arrived in release 3.6.0 (2026-04-06) and is managed under **Settings > Security > Encryption keys**. This guide is for CSMs supporting the set-up and the conversations that follow it, especially around rotation and revocation.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Encryption at rest (AES-256, OmniCorp-managed keys) | Yes | Yes | Yes |
| Customer-managed key in AWS KMS | No | No | Yes |
| Customer-managed key in Azure Key Vault | No | No | Yes |
| **Settings > Security > Encryption keys** page | Hidden | Hidden | Yes |

Encryption in transit (TLS 1.2 or later) is the same on every tier and doesn't depend on this feature.

## How it works

Nimbus uses envelope encryption. Workspace data is encrypted with data keys that Nimbus generates, and those data keys are themselves encrypted ("wrapped") with the client's key. Nimbus never holds the client's key material: to unwrap a data key it asks the client's AWS KMS or Azure Key Vault to do it, using the access the client has granted.

The customer-managed key protects:

- workflow definitions, version history and environment variables;
- run history, including run inputs, outputs and step logs;
- connection credentials and secrets in the secrets vault;
- uploaded files passed between steps.

Unwrapped data keys are cached in memory for a short time, so Nimbus doesn't call the client's key service on every read. Each call it does make shows up in the client's AWS CloudTrail or Azure Monitor logs with the Nimbus principal as the caller.

### Rotation and revocation

Rotation inside the client's key service is supported without any action in Nimbus. AWS KMS automatic rotation keeps the same key ARN, and Nimbus picks up the new key material transparently. In Azure Key Vault, a new key version is used for wrapping once an Admin selects **Re-wrap with latest version** on the Encryption keys page; older versions must stay enabled until the page shows the status **Active** again.

To move to a different key altogether (a new ARN or a key in another vault), an Admin enters the new key and selects **Switch key**. Nimbus re-wraps every data key with the new key, shown as **Re-wrapping** on the page; the old key must stay usable until that finishes.

Revoking access works immediately and is the client's control, not OmniCorp's. If the key is disabled, its grant or role assignment is removed, or it is deleted, Nimbus can no longer unwrap data keys and the workspace becomes unreadable:

1. The console shows "Encryption key unavailable" to every user, and no workflows, connections or run history can be opened.
2. No new runs start; scheduled firings and incoming events are dropped, and runs in progress fail once their cached data keys expire.
3. API calls return `403` with code `forbidden` and the message "Workspace encryption key unavailable".
4. Restoring access to the same key brings the workspace back within minutes, with no data loss.

If the key is permanently deleted, the workspace's data can't be recovered by anyone, including OmniCorp support. Make sure the client's key administrators understand this before they schedule a key for deletion.

## Turning it on

An Admin switches the feature on; it also needs someone with administrative rights over the client's key service.

1. Go to **Settings > Security > Encryption keys** and select **Use a customer-managed key**.
2. Choose **AWS KMS** or **Azure Key Vault**. The page shows the Nimbus principal to grant: an IAM role ARN for AWS, or the enterprise application **OmniCorp Nimbus Key Access** for Azure.
3. In the client's cloud account, create or choose a key in a cloud region inside the workspace's data region. For AWS, use a symmetric KMS key; for Azure, an RSA key with soft delete and purge protection turned on in the vault.
4. Grant the Nimbus principal access. For AWS, add the policy statement below to the key policy. For Azure, grant admin consent for the enterprise application in Microsoft Entra ID, then assign it the **Key Vault Crypto Service Encryption User** role on the key.
5. Back in Nimbus, paste the key ARN or key identifier URL and select **Verify**. Nimbus performs a test wrap and unwrap.
6. Select **Enable**. Nimbus re-wraps existing data keys; the workspace stays in use throughout, and the status changes from **Re-wrapping** to **Active** when it finishes.

The AWS key policy statement:

```json
{
  "Sid": "AllowNimbusWorkspaceEncryption",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::<nimbus-account-id>:role/nimbus-cmk-<workspace-id>"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:GenerateDataKey",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}
```

Copy the exact role ARN from the Encryption keys page; it is specific to the workspace.

## Limits

| Item | Limit |
|---|---|
| Customer-managed keys per workspace | 1 active key |
| Supported key services | AWS KMS and Azure Key Vault only |
| AWS key type | Symmetric encryption key (`SYMMETRIC_DEFAULT`) |
| Azure key type | RSA 2048, 3072 or 4096, software or HSM-protected |
| Key location | A cloud region inside the workspace's data region |
| Encryption algorithm for workspace data | AES-256 |

The key must stay in the same data region as the workspace, so a workspace in the EU data region can't use a key held in a US cloud region. The sandbox workspace that comes with Enterprise has its own Encryption keys page and is set up separately; it can use the same key with a second grant.

## When the Plan Tier changes

Upgrading to Enterprise makes the Encryption keys page available immediately. Existing data stays on OmniCorp-managed keys until an Admin completes the steps above.

A downgrade from Enterprise takes effect at the end of the current billing period. At that point Nimbus re-wraps the workspace's data keys with OmniCorp-managed keys and the Encryption keys page is hidden. The client must keep the key enabled and the grant in place until the downgrade has taken effect and the re-wrap has finished; revoking it earlier makes the workspace unreadable and can block the downgrade. Once **Settings > Plan** shows the new tier, the client can remove the grant. A workspace in the APAC data region can't be downgraded below Enterprise, so this case doesn't arise there. For the other effects of leaving Enterprise, see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
