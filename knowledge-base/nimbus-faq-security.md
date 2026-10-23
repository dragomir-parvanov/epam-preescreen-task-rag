---
id: nimbus-faq-security
title: Security FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-03
owner: Customer Success Enablement
---

Security reviews are a routine part of onboarding and renewal, and the same questions come up in nearly every questionnaire. This FAQ gives CSMs the answers on encryption, compliance reports, two-factor authentication, session timeouts, where connection credentials and secrets live, and how to report a vulnerability.

Single sign-on and automated provisioning have their own Articles, [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) and [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md); send identity-provider questions there.

## General questions

**How is client data encrypted?**

In transit, every connection to the console, the API, inbound triggers and the private connector agent uses TLS 1.2 or later. At rest, data is encrypted with AES-256. Enterprise clients can also use customer-managed keys held in their own AWS KMS or Azure Key Vault, configured under Settings > Security > Encryption keys; revoking the key makes the workspace's data unreadable to Nimbus.

**Which compliance reports can a client see?**

OmniCorp holds a SOC 2 Type II report and an ISO/IEC 27001 certificate. Clients get them through their CSM under NDA; they are not published on a public page. The CSM requests the current copies through the compliance portal and sends them once the client's NDA is on file.

**Is there a data processing agreement?**

Yes. A data processing agreement (DPA) is part of every contract, with OmniCorp as the processor and the client as the controller. If a personal-data breach is confirmed, clients are notified without undue delay and within 72 hours.

**Where are connection credentials stored, and can anyone read them back?**

Connection credentials (OAuth tokens, API keys, passwords, private keys) are encrypted when saved and never shown again, not even to Admins. Values a workflow needs outside a connection, such as a partner's API token used in an HTTP Request step, belong in the secrets vault under Settings > Secrets. A workflow reads a secret by name and the value never appears in run history.

## Setup questions

**How long can a console session stay idle?**

Console sessions end after an idle timeout, 8 hours by default. An Admin can set any value from 15 minutes to 24 hours under Settings > Security > Sessions. The new value applies to existing sessions from their next request.

**How is a secret stored and used?**

An Admin or Builder adds it under Settings > Secrets, or an Admin adds it through the API. A workflow then references it by name inside an expression:

```http
PUT /secrets/PARTNER_API_TOKEN HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"value": "<token-from-partner>"}
```

In the step, set the header to `Bearer {{secrets.PARTNER_API_TOKEN}}`. `GET /secrets` returns names only, never values.

### How do I require two-factor authentication?

Admins can require an authenticator app (TOTP) as a second factor for everyone who signs in with a password:

1. Go to Settings > Security > Two-factor authentication.
2. Switch on Require two-factor authentication for password sign-in.
3. Click Save. Users who haven't enrolled yet are asked to scan a QR code with their authenticator app at their next sign-in.
4. Check Settings > Users, where the 2FA column shows who has enrolled.

Users who sign in through SSO are not affected; their second factor is handled by the identity provider.

## Limits and edge cases

These are the console security settings and their fixed values:

| Setting | Value |
|---|---|
| Minimum password length | 12 characters |
| Failed sign-in attempts before lock | 10 |
| Lock duration | 15 minutes |
| Idle session timeout | 8 hours by default; 15 minutes to 24 hours |
| Second factor | Authenticator app (TOTP) only |
| Encryption in transit | TLS 1.2 or later |
| Encryption at rest | AES-256 |

**Are SMS codes or hardware keys supported as a second factor?**

No. The only second factor for password sign-in is an authenticator app using TOTP.

**How many secrets can a workspace store?**

25 on Starter, 250 on Business and unlimited on Enterprise. See [Secrets Vault Limits](nimbus-tier-secrets-vault.md).

**Does the session timeout apply to API keys?**

No. API keys don't have sessions; they stay valid until their optional expiry date or until an Admin revokes them.

## Troubleshooting questions

**A user is locked out after too many wrong passwords.**

After 10 failed attempts the account is locked for 15 minutes and unlocks on its own. If the user has forgotten the password, they use Forgot password on the sign-in page once the lock has ended.

**A user lost the phone with their authenticator app.**

An Admin opens Settings > Users, selects the user and clicks Reset two-factor. The user enrols a new device at their next sign-in. Check the request with the user through a second channel first, since a reset is a common social-engineering target.

**Users complain about being signed out during the day.**

The idle timeout under Settings > Security > Sessions is probably set short. Raise it within the 15 minutes to 24 hours range, or explain that it is a deliberate policy.

**A client's security team found a vulnerability.**

Ask them to email security@omnicorp.example with the details and steps to reproduce. Reports are acknowledged within 2 business days. The CSM shouldn't collect technical details in the support ticket.

## Where to find more

- [Encryption in Transit and at Rest](nimbus-security-encryption.md) and [Customer-Managed Encryption Keys](nimbus-tier-customer-managed-keys.md).
- [Compliance Reports and Certifications](nimbus-security-compliance-reports.md) and [GDPR and Data Processing](nimbus-security-gdpr.md).
- [Password and Two-Factor Policy](nimbus-security-password-policy.md) and [Session Management](nimbus-security-session-management.md).
- [Vulnerability Reporting and Security Fixes](nimbus-security-vulnerability-disclosure.md).
