---
id: nimbus-release-3-4
title: Nimbus 3.4 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2025-12-01
owner: Release Management
---

Nimbus 3.4.0 was released on 2025-12-01 for every v3 workspace. It adds the secrets vault, a workspace-wide store for credentials and other sensitive values that workflows reference by name, and the Snowflake connector.

Both features are available on every Plan Tier; only the number of secrets a workspace can hold depends on the tier.

## Highlights

- **Secrets vault.** Admins and Builders store API tokens, passwords and keys once under **Settings > Secrets**, and workflows use them with `{{secrets.<NAME>}}` instead of pasting values into steps.
- **Secrets API.** `GET /secrets`, `PUT /secrets/{name}` and `DELETE /secrets/{name}` manage the vault from deployment scripts.
- **Snowflake connector.** Run SQL statements and load rows into Snowflake from a workflow, authenticated with key-pair authentication.

## New features

### Secrets vault

Before 3.4, a value such as a partner's API token had to be typed into each HTTP Request step or transform that needed it, where any Builder could read it. The vault removes that: a secret is created by an Admin or Builder, its value is encrypted and is never shown again after saving, and Builders refer to it only by name. At run time Nimbus resolves `{{secrets.PARTNER_TOKEN}}` just before the step executes, and masks the value as `••••••••` in step logs, run history and `GET /runs/{id}/steps`.

Secret names use upper-case letters, digits and underscores, start with a letter, and are at most 64 characters. Updating a secret's value takes effect for the next step that reads it, so a rotated token is picked up without republishing any workflow. Deleting a secret that a published workflow still references is allowed, but the step then fails with WF-400 because the expression resolves to empty; the delete dialog lists the workflows that reference it.

The vault's size depends on the Plan Tier:

| Plan Tier | Secrets per workspace |
|---|---|
| Starter | 25 |
| Business | 250 |
| Enterprise | Unlimited |

On Business and Enterprise workspaces, secrets are workspace-wide and shared by the Development and Production environments. Values that differ between environments and aren't sensitive, such as a partner's base URL or a queue name, belong in `{{env.<NAME>}}` variables instead; credentials that differ between a test account and a production account are best held on the separate connections each environment already uses. See [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md), [Secrets Vault Limits](nimbus-tier-secrets-vault.md) and [Secrets API](nimbus-api-secrets.md). How vault values are encrypted is described in [How Connection Credentials and Secrets Are Stored](nimbus-security-credential-storage.md).

### Snowflake connector

The Snowflake connector authenticates with key-pair authentication: the client generates an RSA key pair, assigns the public key to a Snowflake service user, and pastes the private key (optionally encrypted with a passphrase) into the Nimbus connection along with the account identifier, user, role and warehouse. The connector has no triggers; it provides actions only:

1. **Execute statement** runs a SQL statement and returns the result rows as a list for later steps.
2. **Insert rows** writes a list of records into a table, mapping fields to columns.
3. **Copy into table** loads files that are already in a named stage.

Result sets above 100 MB are rejected, in line with the per-file limit between steps. See [Snowflake Connector](nimbus-connector-snowflake.md).

## Improvements

- The HTTP Request connector's API key header and OAuth 2.0 client secret fields accept `{{secrets.<NAME>}}`.
- Builders see a warning in the builder when a transform contains a value that looks like a token or a password.
- **Settings > Secrets** shows when each secret was last updated and by whom, and which workflows use it.
- Creating, updating and deleting a secret are recorded in the audit log by name; values are never logged.
- Expression autocomplete suggests secret names but never their values.
- `GET /workspace/entitlements` now returns a `secrets_limit` field, which is null on Enterprise workspaces, so scripts can check headroom before writing a new secret.
- `PUT /secrets/{name}` returns 409 `conflict` when the workspace is already at its secrets limit and the name is new.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-4733 | Approval request emails showed raw expressions when the approval title used a nested field. |
| NIM-4738 | The Microsoft Teams **Post message** action dropped Adaptive Card actions with an empty title. |
| NIM-4742 | A loop over more than 1,000 items rendered slowly in the run detail view. |
| NIM-4745 | `GET /approvals` ignored the `cursor` parameter when filtered by status. |
| NIM-4751 | The MySQL polling trigger failed on tables whose names were reserved words. |
| NIM-4756 | Promoting a workflow with an unchanged trigger re-registered its connector event subscription. |

## Deprecations and breaking changes

Nothing breaks in 3.4. Values typed directly into steps keep working, but storing credentials in step fields is now discouraged: OmniCorp recommends moving them into the vault, because the vault masks values in logs and step fields don't. A future release may warn on publish for workflows that still hold credentials in plain step fields; any such change will be announced in advance.

## Upgrade notes

To move existing credentials into the vault:

1. Under **Settings > Plan**, check how many secrets the workspace's Plan Tier allows, and list the credentials currently pasted into steps; a search for `Authorization` or `token` in the builder's step search is a quick start.
2. As an Admin or Builder, create one secret per credential under **Settings > Secrets > New secret**, or with the Secrets API.
3. In each workflow, replace the pasted value with `{{secrets.<NAME>}}`, test the workflow, and publish (or promote) it.
4. Rotate the old credential in the third-party app, since it was previously visible in the step.
5. For Snowflake, create the service user and assign its public key before creating the connection:

```sql
CREATE USER NIMBUS_SVC
  DEFAULT_ROLE = NIMBUS_LOADER
  DEFAULT_WAREHOUSE = INTEGRATION_WH
  RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv3...';
GRANT ROLE NIMBUS_LOADER TO USER NIMBUS_SVC;
```

A secret can be written from a deployment pipeline like this:

```http
PUT /secrets/PARTNER_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"value": "<new-token>", "description": "Partner portal token, rotated quarterly"}
```

`GET /secrets` returns names, descriptions and update times only, never values.
