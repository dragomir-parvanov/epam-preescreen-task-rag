---
id: nimbus-sso-saml
title: Configuring SSO with SAML 2.0
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-14
owner: Identity Team
---

Single sign-on (SSO) lets a client's users sign in to OmniCorp Nimbus with their company identity provider (IdP) instead of a Nimbus password. Nimbus acts as a SAML 2.0 service provider and supports both sign-in from the Nimbus login page (SP-initiated) and sign-in from the IdP's app dashboard (IdP-initiated).

This guide covers the setup for Okta and Microsoft Entra ID, the attributes Nimbus reads from the SAML assertion, how users are created on first login, how to enforce SSO safely, and the errors users can hit while signing in.

## Before you begin

Check these points with the client before anyone opens the IdP console:

- The workspace is on the Business or Enterprise tier. Starter workspaces can't enable SSO; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- The person doing the setup is a Nimbus Admin in the workspace, and an administrator of the client's IdP.
- The client's IdP is Okta or Microsoft Entra ID. Those are the two identity providers this guide documents step by step.
- Every user has a unique email address in the IdP. Nimbus uses the email address as the login, so two IdP users with the same address can't both sign in.

You'll need two values from Nimbus. An Admin finds them under **Settings > Security > Single sign-on**:

```text
Assertion Consumer Service (ACS) URL:  https://login.nimbus.omnicorp.example/saml/acs/<workspace-id>
Entity ID (Audience URI):              https://login.nimbus.omnicorp.example/saml/metadata/<workspace-id>
Name ID format:                        EmailAddress
```

## Configuring Okta

1. In the Okta Admin Console, go to **Applications > Applications** and click **Create App Integration**.
2. Choose **SAML 2.0** and name the app "OmniCorp Nimbus".
3. Set **Single sign-on URL** to the Nimbus ACS URL, and **Audience URI (SP Entity ID)** to the Nimbus Entity ID.
4. Set **Name ID format** to `EmailAddress` and **Application username** to `Email`.
5. Under **Attribute Statements**, add the attributes listed in the attribute-mapping table below. Add `groups` as a **Group Attribute Statement** if the client wants roles assigned from Okta groups.
6. Finish the wizard, open the app's **Sign On** tab and copy the **Metadata URL**.
7. In Nimbus, paste the metadata URL into **IdP metadata** and click **Save**.
8. Assign a test user to the app in Okta and click **Test sign-in** in Nimbus.

## Configuring Microsoft Entra ID

1. In the Microsoft Entra admin center, go to **Enterprise applications** and click **New application**, then **Create your own application**.
2. Name it "OmniCorp Nimbus" and choose **Integrate any other application you don't find in the gallery**.
3. Open **Single sign-on** and choose **SAML**.
4. In **Basic SAML Configuration**, set **Identifier (Entity ID)** to the Nimbus Entity ID and **Reply URL (Assertion Consumer Service URL)** to the Nimbus ACS URL.
5. In **Attributes & Claims**, set the unique user identifier to `user.mail` and add the claims listed in the attribute-mapping table below. Add a group claim if the client wants roles assigned from Entra groups.
6. In **SAML Certificates**, copy the **App Federation Metadata Url**.
7. In Nimbus, paste the metadata URL into **IdP metadata** and click **Save**.
8. Under **Users and groups**, assign a test user to the app and click **Test sign-in** in Nimbus.

## Attribute mapping

Nimbus reads these attributes from the SAML assertion. Attribute names are case-sensitive and must match exactly.

| Nimbus attribute | Required | Okta value | Microsoft Entra ID claim | Used for |
|---|---|---|---|---|
| `email` | Yes | `user.email` | `user.mail` | Login and unique identity |
| `firstName` | Yes | `user.firstName` | `user.givenname` | Display name |
| `lastName` | Yes | `user.lastName` | `user.surname` | Display name |
| `groups` | No | Group filter | Group claim | Role assignment |

When `groups` is sent, Nimbus assigns the role mapped to the user's groups at each sign-in. When it is missing, new users get the Viewer role and existing users keep the role an Admin gave them.

## Just-in-time provisioning

Just-in-time (JIT) provisioning is on by default once SSO is saved. It creates the user on their first login: if a successful SAML assertion arrives for an email address Nimbus doesn't know, Nimbus creates the account from the assertion's attributes and signs the user in. Nobody has to invite users in advance, and seats are consumed only by people who actually sign in.

JIT provisioning never deprovisions. When someone leaves the client's company and is removed in the IdP, they can no longer sign in to Nimbus, but their Nimbus account stays active, keeps its seat and keeps ownership of its workflows until an Admin suspends it by hand. Clients who need leavers removed automatically use SCIM provisioning on the Enterprise tier; see [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md).

## Enforcing SSO

Once sign-in works for a few test users, an Admin can enforce SSO so that nobody signs in with a Nimbus password any more:

1. Go to **Settings > Security > Single sign-on**.
2. Confirm that **Test sign-in** succeeded within the last 24 hours. Nimbus won't enforce SSO otherwise.
3. Choose the break-glass admin account (see below).
4. Turn on **Require SSO for all users** and confirm.

Enforcement takes effect immediately. Users who are signed in with a password are signed out at their next request and are sent to the IdP.

### Break-glass admin account

When SSO is enforced, exactly one Admin is exempt: the break-glass admin account. It keeps a Nimbus password and must use an authenticator-app second factor. It exists so that the client can still get into Nimbus and fix the configuration if the IdP is down or a certificate expires.

Recommend that the client uses a shared, monitored mailbox for this account rather than a person's address, keeps its credentials in their password vault, and signs in with it only in an emergency. Every break-glass sign-in is recorded in the audit log.

## Troubleshooting

When a SAML sign-in fails, Nimbus shows an error code on the login page and records it in the audit log.

| Code | Meaning | Fix |
|---|---|---|
| AUTH-401 | The assertion is outside its validity window: a clock skew of more than 5 minutes between the IdP and Nimbus. | Sync the IdP server's clock with NTP. Cloud IdPs rarely drift, so also check the clock on any on-premises proxy in the sign-in path. |
| AUTH-403 | The user is not assigned to the Nimbus app in the IdP. | Assign the user, or a group they belong to, to the Nimbus app in Okta or Microsoft Entra ID. |
| AUTH-409 | Duplicate email: another Nimbus account in the workspace already uses this email address. | Ask an Admin to rename or remove the old account in **Settings > Users**, then sign in again. |

If the error page shows no code, the assertion didn't reach Nimbus at all. Check the ACS URL in the IdP for typos first.
