---
id: nimbus-v2-security-sessions
title: Password and Session Security (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-04-14
owner: Security & Compliance
---

This note describes how password sign-in, two-factor authentication and console sessions work on the legacy Nimbus platform. Clients usually ask about it during a security review of a workspace that hasn't been upgraded yet, and the honest answer has a few gaps an Admin can't close with a setting. Knowing them in advance lets a CSM answer the questionnaire accurately and explain what changes after the upgrade.

## Scope

The note covers:

- the password rules for users who sign in with an email address and password;
- the fixed lifetime of a console session;
- two-factor authentication with an authenticator app, and what an Admin can and can't do about it;
- the evidence a client can collect for an auditor.

Sign-in through SAML single sign-on is covered by [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md). Session behaviour is the same for both sign-in methods: once signed in, the session rules below apply. API keys aren't sessions and are covered in [Managing API Keys (v2)](nimbus-v2-admin-api-keys.md).

## Controls in place

The platform enforces these rules for every workspace, and none of them can be changed per workspace:

| Control | Behaviour |
|---|---|
| Password length | At least 10 characters; no composition rules beyond that |
| Password storage | Salted, one-way hashes; OmniCorp staff can't see or recover a password |
| Password reset | Self-service by email link from the sign-in page; the link works once |
| Session lifetime | 12 hours from sign-in, whatever the activity |
| Idle timeout | None; an idle session stays signed in until the 12 hours are up |
| Two-factor authentication | Optional per user, with an authenticator app (TOTP) |
| Two-factor enforcement | Not available; an Admin can't require it |

A session ends when the 12 hours are up, when the user signs out, when the user changes their password (which also ends their other sessions), or when an Admin removes the user. There is no setting to shorten or lengthen the lifetime. A user who leaves a browser signed in on a shared machine stays signed in until the lifetime runs out, so clients that need a shorter exposure should train users to sign out.

Two-factor authentication is chosen by each user under My account > Security. When it is on, the user enters a six-digit code from their authenticator app after their password and receives ten one-time recovery codes at enrolment. Because the setting belongs to the user, an Admin can see who has it and can reset it after a lost device, but can't turn it on for anyone or make it a condition of signing in.

## Admin settings

The Admin menu has no session or password settings. What an Admin can do is measure two-factor coverage and act on individual accounts:

1. Go to Admin > Users. The 2FA column shows Enabled or Off for each user.
2. Sort by the 2FA column and send the users marked Off a request to enrol under My account > Security, starting with every Admin.
3. When a user loses their authenticator device, open the user in Admin > Users and choose Reset two-factor. The user signs in with their password and enrols again.
4. When an account may be compromised, choose Sign out all sessions on the same page, then ask the user to change their password.
5. To remove a leaver, delete the user from Admin > Users, which ends their sessions immediately; see [Inviting and Removing Users (v2)](nimbus-v2-admin-managing-users.md).

For a larger workspace, the Users API gives the same coverage figure. Lists are page-based, with `page` from 1 and `per_page` up to 100, and every list response carries `total`:

```http
GET /users?page=1&per_page=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {"id": "usr_3Fk82Lq", "email": "lena.fischer@example.com", "role": "admin", "two_factor_enabled": true},
    {"id": "usr_7Rt41Wm", "email": "omar.haddad@example.com", "role": "builder", "two_factor_enabled": false}
  ],
  "page": 1,
  "per_page": 100,
  "total": 142
}
```

Counting the users with `two_factor_enabled` set to false gives the gap to report. More on the endpoint is in [Users API (v2)](nimbus-v2-api-users.md).

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Password rules | Enforces the 10-character minimum and stores hashes only | Sets a stronger internal policy and trains users |
| Sessions | Ends every session after 12 hours | Tells users to sign out on shared machines |
| Two-factor | Provides TOTP enrolment, recovery codes and Admin reset | Gets every user, Admins first, to enrol voluntarily |
| Compromised accounts | Provides Sign out all sessions and password reset | Spots the compromise and uses them promptly |
| Stronger controls | Provides them on the current platform | Agrees an upgrade date with the CSM |

## Evidence for auditors

A client can show an auditor a screenshot of Admin > Users with the 2FA column, or the API output above with the count of users who have two-factor enabled, and their own written policy asking users to enrol. Auditors should be told plainly that two-factor can't be enforced and that sessions have no idle timeout; trying to present voluntary enrolment as an enforced control usually becomes a finding.

When those gaps are a problem for the client, the fix is the upgrade, which the CSM books with OmniCorp support and which takes under an hour. After it, an Admin can require two-factor for everyone and set an idle timeout, as described in [Password and Two-Factor Policy](nimbus-security-password-policy.md) and [Session Management](nimbus-security-session-management.md).
