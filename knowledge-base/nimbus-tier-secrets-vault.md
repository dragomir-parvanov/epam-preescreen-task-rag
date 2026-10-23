---
id: nimbus-tier-secrets-vault
title: Secrets Vault Limits
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-05
owner: Product Operations
---

The secrets vault stores values that workflows need but that shouldn't sit in a workflow definition: API tokens for the HTTP Request connector, passwords for internal services, signing keys, partner account numbers. A workflow refers to a secret by name with `{{secrets.<NAME>}}`, and Nimbus resolves it at run time. The vault was introduced in release 3.4.0 and is managed under **Settings > Secrets**.

Every Plan Tier includes the vault; what differs is how many secrets a workspace can hold. This Article gives the limits, explains how secrets are stored, and covers what happens when a downgrade leaves a workspace with more secrets than its new tier allows. Day-to-day management is described in [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md).

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Secrets vault | Yes | Yes | Yes |
| Secrets per workspace | 25 | 250 | Unlimited |
| Manage secrets in the console | Yes | Yes | Yes |
| Manage secrets through the API | No API access | Yes | Yes |
| Secrets encrypted with a customer-managed key | No | No | Yes, when configured |

## How it works

A secret is a name and a value. The name is visible to anyone who can edit workflows; the value is write-only. Once a secret is saved, nobody can read its value back, in the console or through the API: the console shows the name, who last changed it and when, and the API returns names only. To change a value, overwrite it.

Values are encrypted with AES-256 before they are stored, and decrypted only inside the run that needs them. On Enterprise, a workspace that uses customer-managed encryption keys has its secrets encrypted under that key too, so revoking the key in AWS KMS or Azure Key Vault also makes the secrets unreadable to Nimbus; see [Customer-Managed Encryption Keys](nimbus-tier-customer-managed-keys.md).

At run time, an expression such as `{{secrets.ERP_API_TOKEN}}` in a step's field is replaced with the value just before the step runs. Nimbus masks secret values in run history and step logs, replacing them with `••••••••` wherever they would appear in inputs or outputs. A run that refers to a secret that doesn't exist fails at that step with WF-400, the code for a data-mapping expression that failed. Because values are resolved per step, rotating a secret takes effect for every step that starts after the new value is saved, with no need to republish the workflows that use it; a step that is already running keeps the value it started with.

Secrets are different from two related things:

- **Connection credentials** belong to a connection and are entered when it is authorised. They don't count as secrets.
- **Environment variables** (`{{env.<NAME>}}`) hold non-sensitive values that differ between Development and Production, such as a base URL, and are shown in clear text.

## Turning it on

The vault is always available. Admins and Builders can create and update secrets; Viewers see neither names nor values.

1. Go to **Settings > Secrets** and click **New secret**.
2. Enter a **Name** in capitals, digits and underscores, starting with a letter, for example `ERP_API_TOKEN`.
3. Paste the **Value** and click **Save**. The value is hidden from this point on.
4. In the workflow builder, refer to it in any field as `{{secrets.ERP_API_TOKEN}}`.
5. Test the workflow with **Run now** in the builder and check that the step's logged input shows the masked value.

Where the tier includes API access, an Admin can manage secrets with an API key. `PUT` creates the secret if the name is new and overwrites the value if it exists:

```http
PUT /secrets/ERP_API_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{ "value": "erp_live_7f3c91d2a8b44e0c9b1f" }
```

`GET /secrets` lists the names, with paging through `limit` and `cursor`, and `DELETE /secrets/{name}` removes one. Deleting a secret that a workflow still uses doesn't stop the workflow from being saved, but its next run fails at the step that needs it.

## Limits

| Limit | Starter | Business | Enterprise |
|---|---|---|---|
| Secrets per workspace | 25 | 250 | Unlimited |
| Maximum value size | 8 KB | 8 KB | 8 KB |
| Maximum name length | 64 characters | 64 characters | 64 characters |

The limit is per workspace and counts every secret, whether or not a workflow uses it. The current count appears on the **Secrets** meter on **Settings > Usage**, and Admins are emailed when it reaches 80% and 100% of the limit. When the limit is reached, **New secret** is disabled and creating a new name through the API returns an error, while existing secrets can still be updated:

```json
{
  "error": {
    "code": "conflict",
    "message": "This workspace has reached its limit of 25 secrets. Delete a secret or upgrade the Plan Tier to add more."
  }
}
```

The 8 KB value size is enough for a PEM-encoded private key or certificate chain. Larger material, such as a keystore file, belongs in the connector configuration rather than the vault.

## When the Plan Tier changes

**Upgrade.** An upgrade takes effect immediately, and the higher limit applies straight away, so a workspace that was blocked at its limit can add secrets again without any further step.

**Downgrade.** A downgrade takes effect at the end of the current billing period. Unlike seats or active connectors, secrets above the new limit don't hold the downgrade, and none are deleted. After the downgrade:

1. Every existing secret keeps working, and workflows that use them run as before.
2. Existing secrets can still be updated with a new value.
3. No new secret can be added until the count is below the new limit. A Business workspace with 120 secrets that moves to Starter has to delete at least 96 of them before it can create a new one.

Recommend that the client reviews **Settings > Secrets** before the downgrade and deletes secrets no workflow uses; the **Used by** column lists the workflows that refer to each one. A downgrade from Enterprise also ends the use of a customer-managed key, after which secrets are encrypted with Nimbus-managed keys.
