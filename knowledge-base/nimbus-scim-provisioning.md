---
id: nimbus-scim-provisioning
title: Automated User Provisioning with SCIM 2.0
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-21
owner: Identity Team
---

SCIM provisioning keeps a client's Nimbus users in step with their identity provider (IdP). The IdP becomes the source of truth: people the client assigns to the Nimbus app get an account, changes to their name or groups flow through, and people who are unassigned or leave the company lose access without anyone touching the Nimbus admin console.

This guide explains what SCIM does in Nimbus, what has to be in place first, how to connect Okta or Microsoft Entra ID, how groups become Nimbus roles, and what happens when a user is deprovisioned.

## Overview

Nimbus implements the SCIM 2.0 protocol for users and groups. Once connected, the IdP sends Nimbus every change to the users and groups assigned to the Nimbus app, and the changes are synced every 40 minutes. A change made in the IdP therefore reaches Nimbus within one sync cycle, not instantly.

Each sync can:

- **create** an account for a newly assigned user, before that user has ever signed in;
- **update** the user's name, email address and role when they change in the IdP;
- **deprovision** a user who is unassigned from the app or deactivated in the IdP.

That last point is the main difference from just-in-time (JIT) provisioning, which comes with single sign-on. JIT creates an account only when a user first signs in and never removes one. SCIM covers the whole life of the account, including the leaver case. See [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) for how JIT behaves. Both can stay switched on together: SCIM-managed users are simply created before their first sign-in.

## Prerequisites

Before you start, confirm all of the following with the client:

1. **The workspace is on the Enterprise tier.** SCIM provisioning isn't available on Starter or Business; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md). A Business-tier client must upgrade first.
2. **SAML single sign-on must be configured first**, with the same IdP, and a test sign-in must have succeeded. Follow [Configuring SSO with SAML 2.0](nimbus-sso-saml.md). SCIM creates the accounts; SSO is how those users sign in to them.
3. **The IdP is Okta or Microsoft Entra ID**, the two IdPs whose SCIM connection this guide documents.
4. **The person doing the setup is a Nimbus Admin** and an administrator of the IdP.

## Generating a SCIM token

The IdP authenticates to Nimbus with a bearer token that a Nimbus Admin creates:

1. Go to **Settings > Security > User provisioning**.
2. Click **Generate SCIM token**.
3. Copy the token. Nimbus shows it only once; if it is lost, generate a new one.
4. Note the SCIM base URL shown on the same page.

```text
SCIM base URL:  https://api.nimbus.omnicorp.example/scim/2.0
Authentication: HTTP header  Authorization: Bearer <scim-token>
```

A SCIM token expires after 365 days. Nimbus emails the workspace's Admins 14 days before it expires. When a token expires, sync stops until a new token is entered in the IdP, and changes made in the meantime are applied at the first sync after that.

### Rotating the token

Rotate the token before it expires, or straight away if it may have leaked:

1. Generate a new token in Nimbus. The old token keeps working until step 3.
2. Paste the new token into the IdP's provisioning settings and run **Test connection**.
3. Back in Nimbus, click **Revoke** next to the old token.

## Connecting your identity provider

In **Okta**, open the Nimbus SAML app created for SSO, go to the **Provisioning** tab, click **Configure API Integration**, enter the SCIM base URL and the token, and run **Test API Credentials**. Then, under **To App**, turn on **Create Users**, **Update User Attributes** and **Deactivate Users**.

In **Microsoft Entra ID**, open the Nimbus enterprise application, go to **Provisioning**, set **Provisioning Mode** to **Automatic**, enter the SCIM base URL as the **Tenant URL** and the token as the **Secret Token**, and click **Test Connection**. Then set **Provisioning Status** to **On**.

In both IdPs, only users and groups assigned to the Nimbus app are provisioned. Assign groups rather than individual users wherever possible, so that new joiners are picked up automatically.

## Mapping groups to roles

Nimbus maps the IdP groups pushed over SCIM to Nimbus roles. An Admin sets the mapping under **Settings > Security > User provisioning > Role mapping**. A typical mapping looks like this:

| IdP group | Nimbus role |
|---|---|
| `nimbus-admins` | Admin |
| `nimbus-builders` | Builder |
| `nimbus-viewers` | Viewer |

The rules are:

- A user in several mapped groups gets the highest of their roles (Admin, then Builder, then Viewer).
- A user in no mapped group gets the Viewer role.
- A role change in the IdP replaces any role an Admin set by hand in Nimbus at the next sync.

## Deprovisioning

Deprovisioning happens when a user is unassigned from the Nimbus app or deactivated in the IdP. At the next sync, Nimbus suspends the user. It does not delete them straight away.

| Stage | What happens |
|---|---|
| Next sync after the change | Nimbus suspends the user: they can't sign in, their API keys stop working and their seat is freed. |
| Days 1–30 | The user's data (workflows, run history, connector credentials) is kept for 30 days. Reassigning the user in the IdP reactivates the account with its data. |
| After 30 days | The user's data is then permanently deleted and can't be restored. Assigning the user again later creates a new, empty account. |

Workflows the suspended user owned keep running during those 30 days. To keep them beyond that, an Admin transfers their ownership in **Settings > Users** before the data is deleted. Audit-log events about the user are not affected; they follow the workspace's audit-log retention.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Test connection fails with 401 | The token is wrong, revoked or expired. | Generate a new token and enter it in the IdP. |
| A user got the Viewer role unexpectedly | The user isn't in any mapped group. | Add the user's group to the role mapping. |
| A leaver can still sign in | The change hasn't reached Nimbus yet. | Wait for the next sync, up to 40 minutes, or trigger a manual provisioning run in the IdP. |
| **User provisioning** is missing from the settings | The workspace isn't on the Enterprise tier. | Check the prerequisites above. |
