---
id: nimbus-security-credential-storage
title: How Connection Credentials and Secrets Are Stored
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-23
owner: Security & Compliance
---

Every Nimbus workflow that touches another system needs a credential for it: an OAuth token for HubSpot, a key pair for Snowflake, a password for a PostgreSQL database, an API token kept in the secrets vault. Clients reviewing Nimbus want to know who can see those credentials, where they are decrypted and whether they can leak into logs. This note answers those questions for v3.

In one sentence: credentials are encrypted per workspace, write-only in both the console and the API, decrypted only inside the run that uses them, and masked in step logs.

## Scope

The note covers two kinds of stored credential. Connection credentials are what a Builder or Admin enters, or what an OAuth flow returns, when creating a connection under **Connections**: access and refresh tokens, API tokens, usernames and passwords, private keys and SSH keys. Secrets are named values kept in the secrets vault under **Settings > Secrets** and used in workflow steps as `{{secrets.<NAME>}}`, typically for the HTTP Request connector or for values a transform needs.

Nimbus API keys are a different kind of credential, created by an Admin to call Nimbus itself; they are covered in [API Key Security Practices](nimbus-security-api-key-hygiene.md). The ciphers and key management behind the encryption are covered in [Encryption in Transit and at Rest](nimbus-security-encryption.md).

## Controls in place

Credentials and secrets are encrypted with AES-256 under a key that belongs to the workspace, separate from the key used for the rest of the workspace's data. A credential saved in one workspace can't be decrypted in another, and a client's sandbox workspace has its own key, separate from production. On Enterprise, a customer-managed key in AWS KMS or Azure Key Vault wraps the workspace's keys, so revoking Nimbus's access to that key also makes the credentials unreadable; see [Customer-Managed Encryption Keys](nimbus-tier-customer-managed-keys.md).

### Write-only access

Connection credentials and secrets are never shown again after saving, to anyone:

| Where | What is shown |
|---|---|
| **Connections**, connection detail | Account name, auth method, status and **Last used**; secret fields show **Saved** with a **Replace** button |
| **Settings > Secrets** | Secret names, who last updated each one and when; no values |
| `GET /connections/{id}` | Connection metadata only; no credential fields are returned |
| `GET /secrets` | Names only |
| OmniCorp support tools | Metadata only; support staff can't decrypt credentials |

Builders can use a secret in a step by name without ever seeing its value, which lets a client keep a production password with its owner while Builders maintain the workflows.

### Use during a run

A credential is decrypted only inside the run that needs it. The worker executing a connector step decrypts the credential in memory immediately before calling the third-party app and discards it when the step ends; it is never written to disk, to a queue, or to a log. For steps routed through a private connector agent, the decrypted credential travels to the agent over its outbound TLS connection and is held in the agent's memory for that step only. When an OAuth access token expires, Nimbus uses the refresh token to get a new one and stores it the same way.

Step logs, step inputs and outputs in **Runs**, and the response of `GET /runs/{id}/steps` are masked: wherever a stored credential or secret value appears verbatim, it is replaced with `••••••••`. Masking matches exact values, so a value that a transform has changed, such as a secret that has been base64-encoded or split into parts, isn't recognised and would appear in the log.

## Admin settings

To store a value in the secrets vault and use it in a workflow:

1. Open **Settings > Secrets** and click **New secret**.
2. Enter a **Name** in capitals, digits and underscores, for example `ZENDESK_API_TOKEN`. The name is what workflows refer to and appears in the audit log, so don't put sensitive information in it.
3. Paste the value and click **Save**. The value field clears and can't be shown again.
4. In the workflow builder, reference the secret in a step field as `{{secrets.ZENDESK_API_TOKEN}}`.
5. To rotate the value, click **Replace** next to the secret and save the new value. The next run picks it up; workflows don't need to be republished.

To replace a connection's credentials instead, open **Connections**, select the connection and click **Reconnect**, which repeats the OAuth flow or asks for the new password or key. How many secrets each Plan Tier allows is in [Secrets Vault Limits](nimbus-tier-secrets-vault.md).

Secrets can be written through the API, but never read back:

```http
PUT /secrets/ZENDESK_API_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{ "value": "r8K2mQ7vXz1Lp4Nc9Tb6Hw3Ys5Fd0Ge" }

HTTP/1.1 200 OK
Content-Type: application/json

{ "name": "ZENDESK_API_TOKEN", "updated_at": "2026-03-19T14:05:31Z", "updated_by": "usr_9Lm1Vc6Rt" }
```

The full set of secret endpoints is in [Secrets API](nimbus-api-secrets.md).

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Storage | Encrypts every credential and secret with a per-workspace key | Stores credentials in Nimbus rather than in workflow fields or expressions |
| Visibility | Makes credentials write-only in the console, the API and support tools | Gives each connection a dedicated integration account with only the permissions the workflows need |
| Use in runs | Decrypts only in memory, inside the run, and discards after the step | Runs the private connector agent on a host it secures, where the agent is used |
| Logs | Masks exact credential and secret values in step logs and outputs | Avoids transforms that encode or split secrets, and doesn't map secrets into step outputs |
| Rotation | Applies a replaced value from the next run | Rotates passwords, tokens and keys on its own schedule and after staff changes |
| Deletion | Erases a deleted connection's credentials immediately | Deletes connections and secrets that are no longer used |

## Evidence for auditors

A client can show that credentials are write-only by opening any connection or the **Settings > Secrets** page with the auditor present, or by sharing a `GET /secrets` response, which lists names only. Changes to stored credentials are recorded in the audit log as `secret.created`, `secret.updated`, `secret.deleted`, `connection.created`, `connection.reconnected` and `connection.deleted`, with the acting user, and can be exported from **Settings > Audit log**. A run's step log showing `[masked]` in place of a token is a simple demonstration of log masking. For the controls behind all this, the CSM can share OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate under NDA; see [Compliance Reports and Certifications](nimbus-security-compliance-reports.md).
