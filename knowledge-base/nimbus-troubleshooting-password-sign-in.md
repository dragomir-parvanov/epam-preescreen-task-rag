---
id: nimbus-troubleshooting-password-sign-in
title: Troubleshooting Password Sign-in and Two-Factor Problems
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-09-28
owner: Support Engineering
---

This reference is for users who sign in to the Nimbus admin console at https://app.nimbus.omnicorp.example with an email address and password, with or without a second factor from an authenticator app. It covers lockouts, password resets, lost authenticator apps and recovery codes, and how an Admin resets another user's second factor.

Users whose workspace signs them in through the client's identity provider don't use a Nimbus password at all. Their sign-in problems, and the error codes shown on the single sign-on page, are covered in [Configuring SSO with SAML 2.0](nimbus-sso-saml.md). The policy side of passwords and two-factor authentication is described in [Password and Two-Factor Policy](nimbus-security-password-policy.md).

## Symptoms

- The sign-in page says "Too many failed attempts" and won't accept even the correct password.
- A user who has just set a new password can't save it.
- The six-digit code from the authenticator app is rejected every time.
- A user has a new phone and their authenticator app no longer has a Nimbus entry.
- A recovery code is refused.
- The password reset email doesn't arrive, or its link says it has expired.

## Common causes

**Repeated wrong passwords.** After 10 failed attempts the account is locked for 15 minutes. Password managers that autofill an old password, and scripts or browser extensions that retry silently, reach that count quickly. During the lock every attempt fails, including one with the right password.

**A password that doesn't meet the policy.** Passwords need at least 12 characters. A password chosen in another system, or generated with a shorter default, is refused when the user tries to set it.

**Phone clock drift.** Authenticator codes are time-based and each is valid for a short window. A phone whose time is set by hand, or that has drifted, produces codes Nimbus rejects even though the app looks fine.

**A lost or replaced authenticator.** Authenticator apps store their secrets on the device. Moving to a new phone without transferring the accounts leaves the user with no codes.

**Exhausted or used recovery codes.** When two-factor authentication is set up, Nimbus shows 10 single-use recovery codes. Each works once. Users often saved them once and have used them over time without noticing.

**Mail filtering or an old link.** Password reset emails come from `notifications@nimbus.omnicorp.example`, and each reset link works for 60 minutes and only once. Requesting a second reset makes the first link invalid.

## Diagnosing the problem

1. Ask the user which message the sign-in page shows, word for word, and match it to the table under Error reference.
2. As an Admin, open **Settings > Users** and select the user. The **Sign-in** panel shows whether the user signs in with a password, whether two-factor authentication is set up, and, while the lock lasts, **Locked until** with a time in UTC.
3. Check the audit log for the user's recent sign-in attempts. Under **Settings > Audit log**, filter by the user as actor, or use the API:

```http
GET /audit-log/events?actor=usr_5Kd2Mw8R&action=auth.sign_in_failed&from=2026-09-27T00:00:00Z
Authorization: Bearer <api-key>

{"data": [{"id": "evt_9Qa3Lt7V", "action": "auth.sign_in_failed",
  "actor": "usr_5Kd2Mw8R", "reason": "invalid_password",
  "occurred_at": "2026-09-27T07:58:41Z"}],
 "next_cursor": null}
```

4. Many `invalid_password` events in quick succession, at times the user wasn't at their desk, point to a password manager or a script retrying an old password. A run of `invalid_second_factor` reasons points to clock drift or the wrong authenticator entry.
5. For a missing reset email, ask the user to search all mail folders, including quarantine, for the sender address.

## Error reference

Sign-in messages carry no codes. The console shows the following:

| Message on the sign-in page | Meaning |
|---|---|
| "Incorrect email or password." | The password is wrong, or the email isn't a user in this workspace. Counts towards the lock. |
| "Too many failed attempts. Try again in 15 minutes." | The account is locked after 10 failed attempts. |
| "Password must be at least 12 characters." | The new password is too short. |
| "That code didn't work. Check the time on your device." | The authenticator code is wrong or out of its time window. |
| "This recovery code has already been used." | Each recovery code works once. |
| "This reset link has expired or was already used." | The link is older than 60 minutes, was used, or was replaced by a newer request. |

## Fixes

### Locked accounts and resets

Wait out the lock: it clears on its own after 15 minutes, and neither a password reset nor an Admin can shorten it. Before the user tries again, they should update the saved password in their password manager and close any tool that signs in on their behalf, or the account will lock again.

To reset a forgotten password, the user clicks **Forgot password?** on the sign-in page, enters their email and uses the newest link within 60 minutes. The new password must have at least 12 characters. A reset signs the user out of every other console session.

### Lost authenticator app

When the user still has an unused recovery code, they enter it in place of the six-digit code, then go to their profile and choose **Set up two-factor again** to enrol the new phone. Remind them to save the new set of 10 recovery codes.

When they have no codes left, an Admin resets their second factor:

1. Open **Settings > Users** and select the user.
2. In the **Sign-in** panel, click **Reset two-factor**.
3. Confirm. The user's authenticator registration and remaining recovery codes are deleted, and the reset is recorded in the audit log.
4. Ask the user to sign in with their password. If the workspace requires two-factor authentication, they are taken straight to enrolment; see [Requiring Two-Factor Authentication](nimbus-admin-requiring-two-factor.md).

An Admin can't reset their own second factor. Another Admin must do it, which is why workspaces should keep at least two Admins.

## Escalating to support

Escalate when the only Admin in a workspace has lost both their authenticator and their recovery codes, or when lockouts continue after the user has cleared saved passwords. OmniCorp support verifies the request with the client's CSM before acting. Collect:

- workspace id and the user id (`usr_...`) and email;
- the exact message from the sign-in page;
- the relevant audit log events (`auth.sign_in_failed` with their reasons);
- for missing reset emails, the client's mail gateway trace for the sender address.
