---
id: nimbus-security-password-policy
title: Password and Two-Factor Policy
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-02-02
owner: Security & Compliance
---

Security questionnaires ask for the password rules, the lockout behaviour and the multi-factor options of every system a client uses. For Nimbus the answers are short: passwords of at least 12 characters, a 15-minute lock after 10 failed attempts, and two-factor authentication with an authenticator app that an Admin can make mandatory. This note gives the detail behind each answer and the console steps a CSM may need to walk a client through.

Clients that sign in through their identity provider rely on the IdP's own password and multi-factor rules instead; this note applies only where people sign in to Nimbus with a Nimbus password.

## Scope

The note covers password sign-in to the v3 admin console: the password rules, failed-attempt lockout, two-factor authentication with a time-based one-time password (TOTP), and the Admin settings that control them. It applies to every workspace that doesn't use single sign-on, and to workspaces that have SSO configured but not enforced, where people may still choose to sign in with a password.

When SSO is enforced, password sign-in is switched off for everyone except one emergency account; that break-glass account and its own second-factor rule are described in [Configuring SSO with SAML 2.0](nimbus-sso-saml.md), not here. API keys don't use passwords at all and are covered in [API Key Security Practices](nimbus-security-api-key-hygiene.md). How long a signed-in session lasts is covered in [Session Management](nimbus-security-session-management.md).

## Controls in place

| Control | Nimbus behaviour |
|---|---|
| Minimum length | 12 characters |
| Maximum length | 128 characters; spaces and any Unicode characters are allowed, so passphrases work |
| Composition rules | None beyond length; new passwords are checked against a list of known breached passwords and rejected if found |
| Periodic expiry | None; a password is changed when the user chooses or when it is reset |
| Failed attempts | After 10 failed attempts the account is locked for 15 minutes |
| Second factor | TOTP from an authenticator app; optional for each user unless an Admin requires it |
| Storage | Passwords are stored only as salted Argon2id hashes; nobody at OmniCorp can read them |

The lockout counts consecutive failed attempts on one account, whichever device or browser they come from, and a successful sign-in resets the count. While an account is locked, the sign-in page shows "Too many failed attempts. Try again in 15 minutes." even if the correct password is entered, and the user is emailed that their account was locked. The lock lifts on its own after 15 minutes; there is no unlock button for Admins, so a client asking how to unlock a user should be told to wait or to reset the password once the lock has lifted.

Two-factor authentication uses standard TOTP codes (six digits, a new code every 30 seconds), so any authenticator app works, including Microsoft Authenticator, 1Password and Authy. SMS codes aren't offered. At enrolment Nimbus shows 10 single-use recovery codes, which the user stores somewhere safe and can use once each if their phone is lost. The 10-attempt lockout covers wrong TOTP codes as well as wrong passwords.

## Admin settings

Password length and lockout are fixed and have no settings. Two-factor authentication is controlled under **Settings > Security > Two-factor authentication**; the full walkthrough is in [Requiring Two-Factor Authentication](nimbus-admin-requiring-two-factor.md).

### Requiring two-factor

1. Sign in as an Admin and open **Settings > Security > Two-factor authentication**.
2. Check how many users are already enrolled; the page lists password users without two-factor so they can be warned before the change.
3. Turn on **Require two-factor authentication for password sign-in** and click **Save**.
4. From their next sign-in, users who aren't enrolled are taken straight to the enrolment screen and can't skip it. Users who are already enrolled see no change.

If a user loses their phone and their recovery codes, an Admin opens **Settings > Users**, selects the user and clicks **Reset two-factor**. The user signs in with their password and enrols a new authenticator app straight away.

To check enrolment across the workspace, for example before a security review, read the `two_factor_enabled` field from the Users API:

```http
GET /users?limit=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {
      "id": "usr_3Fh8Wq2Kd",
      "email": "priya.shah@acme.example",
      "role": "Admin",
      "sign_in_method": "password",
      "two_factor_enabled": true
    },
    {
      "id": "usr_9Lm1Vc6Rt",
      "email": "tom.berg@acme.example",
      "role": "Builder",
      "sign_in_method": "sso",
      "two_factor_enabled": false
    }
  ],
  "next_cursor": null
}
```

Users with `"sign_in_method": "sso"` authenticate through the IdP, so `two_factor_enabled` is expected to be false for them; their multi-factor rules live in the IdP. More fields and filters are described in [Users API](nimbus-api-users.md).

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Password rules | Enforces the 12-character minimum and the breached-password check; stores only salted hashes | Encourages a password manager and unique passphrases |
| Lockout | Locks an account for 15 minutes after 10 failed attempts and emails the user | Investigates repeated lock emails that the user didn't cause |
| Two-factor | Provides TOTP enrolment, recovery codes and the require setting | Decides whether to require two-factor, and turns it on |
| Lost devices | Provides **Reset two-factor** for Admins | Verifies the user's identity before an Admin resets their second factor |
| SSO users | Hands authentication to the IdP | Sets password and multi-factor policy in the IdP |
| Break-glass account | Keeps password sign-in available for that one account | Protects its credentials, as described in the SSO Article |

## Evidence for auditors

A client can show an auditor a screenshot of **Settings > Security > Two-factor authentication** with the require setting on, together with an export of `GET /users` showing `two_factor_enabled` for every password user. The audit log records `security.two_factor_policy_updated` when the setting changes, `user.two_factor_reset` when an Admin resets a user's second factor, and `auth.sign_in_failed` and `auth.account_locked` for failed sign-ins; these can be filtered and exported under **Settings > Audit log** as described in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md). The fixed controls (length, breached-password check, hashing and lockout) are covered by OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate, which the CSM can share under NDA.
