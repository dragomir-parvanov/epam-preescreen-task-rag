---
id: nimbus-admin-secrets-vault
title: Storing Credentials in the Secrets Vault
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-23
owner: Workspace Administration Team
---

The secrets vault, added in release 3.4.0, gives an OmniCorp Nimbus workspace one place to keep the values that workflows need but nobody should read: a partner's API token, a password for a legacy system called through the HTTP Request connector, a shared signing key. A secret is stored once under **Settings > Secrets** and referenced by name in any step, so the value never appears in the workflow definition, in exports or in version history.

Secrets complement connections rather than replace them. A connection keeps its own credentials, encrypted and never shown again after saving. Secrets are for everything else a step needs to send, such as a header value, a query parameter or a field in a request body.

## Before you begin

- **Role:** Admins and Builders can create, update and delete secrets. Viewers can't open **Settings > Secrets**.
- **Plan Tier:** the vault exists on every tier, with a limit on how many secrets a workspace can hold. The current count is on **Settings > Usage**.

| Plan Tier | Secrets per workspace |
|---|---|
| Starter | 25 |
| Business | 250 |
| Enterprise | Unlimited |

- **Release:** the vault arrived in 3.4.0 (1 December 2025). Workflows built before then may still carry tokens typed directly into step fields; moving those into the vault is a good first use.
- **The value itself:** have it ready from the client's own password manager. Nimbus can't show it to you again once it is saved.

## How it works

A secret is a name and a value. Values are write-only: they are encrypted with AES-256 when saved, the console shows only the name, who last changed it and when, and `GET /secrets` returns names only. Nobody, including the Admins and OmniCorp support, can read a value back out of Nimbus.

Names follow fixed rules: upper-case letters, digits and underscores only, starting with a letter, up to 64 characters. `PARTNER_API_TOKEN` and `SFTP_PASSPHRASE_2` are valid; `partner-token` and `2FA_SEED` are not. Names are case-sensitive in expressions and must be unique in the workspace. Secrets are workspace-wide: every workflow, in every folder, can reference any secret, so a client that wants to separate teams' credentials should agree a naming prefix per team, such as `FIN_` and `HR_`.

A step uses a secret through a double-brace expression, in any field that accepts expressions. For example, an HTTP Request step that calls a partner API sets its header like this:

```yaml
step: notify_partner
connector: HTTP Request
method: POST
url: https://api.partner.example/orders
headers:
  Authorization: "Bearer {{secrets.PARTNER_API_TOKEN}}"
  X-Client-Ref: "{{trigger.body.order_id}}"
body:
  status: "{{lower(steps.check_stock.output.result)}}"
```

The value is resolved when the step runs, not when the workflow is published. Two things follow from that. First, rotating a secret updates every workflow that uses it, without republishing anything: the next step that resolves the name gets the new value. Second, a step that references a secret which has been deleted fails with WF-400, because the expression resolved to empty.

Wherever a secret's value would appear in a step's input or output in run history, Nimbus replaces it with `••••••••`. This masking applies to the exact value, so a step that transforms the secret (for example, Base64-encoding it) can produce output that isn't masked. Avoid transforming secrets in steps whose output is logged.

## Step-by-step

To create a secret and use it:

1. Open **Settings > Secrets** and click **New secret**.
2. Enter the **Name**, for example `PARTNER_API_TOKEN`, and paste the **Value**.
3. Optionally add a **Description** that says what the secret is for and who owns it at the client.
4. Click **Save**. The value field empties and can't be shown again.
5. In the workflow builder, open the step that needs it and type `{{secrets.PARTNER_API_TOKEN}}` in the field. The builder suggests matching names as you type `{{secrets.`.
6. Publish the workflow.

To rotate a secret, open it on **Settings > Secrets**, click **Update value**, paste the new value and save. To find what depends on a secret before rotating or deleting it, open its **Used by** tab, which lists every workflow whose published version references it.

`PUT /secrets/{name}` creates a secret or replaces its value, so the same call serves for both creation and rotation:

```http
PUT /secrets/PARTNER_API_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"value": "<new-token>", "description": "Partner order API, owned by the integrations team"}
```

`DELETE /secrets/{name}` removes one. A client's own credential-rotation job can call `PUT` straight after it rotates the token at the partner.

## Verifying the change

The secret appears on **Settings > Secrets** with its name and an **Updated** time that matches your change. `GET /secrets` lists it with `updated_at` and `updated_by`, but never the value. To confirm a workflow picks it up, run the workflow with **Run now** in the builder and open the step in run history: the masked `••••••••` in the input shows that the secret resolved. Creating, updating and deleting secrets are recorded in **Settings > Audit log**, without the values.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| **Save** reports "Invalid name" | The name has lower-case letters, hyphens or spaces, or starts with a digit. | Use upper case, digits and underscores, starting with a letter. |
| **New secret** is disabled with "Secret limit reached" | The workspace holds as many secrets as its Plan Tier allows. | Delete unused secrets (check **Used by** first) or upgrade the tier. |
| A step fails with WF-400 mentioning `secrets.` | The secret was deleted or the name in the expression is misspelt. | Recreate the secret or correct the expression; names are case-sensitive. |
| The partner rejects the call after rotation | The new value was pasted with a trailing space or newline. | Update the value again, pasting it without surrounding whitespace. |
| A client asks to see a stored value | Values are write-only. | Retrieve it from the client's own password manager; Nimbus can't return it. |
| A token shows in run history | A step transformed the secret before using it, so masking didn't match. | Move the transformation out of logged output, then rotate the exposed token. |
