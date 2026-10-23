---
id: nimbus-security-session-management
title: Session Management
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-24
owner: Security & Compliance
---

Once someone has signed in to the Nimbus admin console, the session decides how long they stay signed in and what can end their access early. This note covers the idle timeout and its limits, how the session cookie is protected, the ways a session is ended, and why API keys follow different rules. It is written for CSMs answering the session questions in a client's security review.

The headline values: a console session ends after 8 hours without activity by default, and an Admin can set the idle timeout anywhere from 15 minutes to 24 hours.

## Scope

The note applies to browser sessions on the v3 admin console at `https://app.nimbus.omnicorp.example`, whether the user signed in with a password or through single sign-on. It doesn't cover how a user proves who they are at sign-in, which is in [Password and Two-Factor Policy](nimbus-security-password-policy.md) and [Configuring SSO with SAML 2.0](nimbus-sso-saml.md), nor sessions held by an identity provider, which the IdP controls. API keys are covered here only to explain how they differ from console sessions.

## Controls in place

A console session is tracked on the server; the browser holds only an opaque, random session identifier. The session ends after a period without activity, the idle timeout, which is 8 hours unless an Admin changes it. Any page load or console action counts as activity and restarts the clock. Two minutes before the timeout the console shows a **Stay signed in** prompt; if the user doesn't respond, the session ends and the next click goes to the sign-in page. A user who signed in through SSO is sent back to their IdP at that point and, if the IdP session is still valid, returns without typing a password.

The session cookie is set with the attributes browsers need to keep it away from scripts and other sites:

```http
Set-Cookie: nimbus_session=8f1c0a7e5d2b4c9aa31e6f04b7d29c58; Path=/; Secure; HttpOnly; SameSite=Lax
```

- `Secure` means the cookie is only sent over HTTPS.
- `HttpOnly` means page scripts can't read it, which limits the damage of a cross-site scripting bug.
- `SameSite=Lax` means it isn't sent on cross-site form posts; state-changing requests also carry a per-session CSRF token.
- The cookie has no `Domain` attribute, so it is sent only to `app.nimbus.omnicorp.example` and not to other OmniCorp hostnames.

A session ends before the idle timeout when any of these happens:

| Event | Effect on sessions |
|---|---|
| The user clicks **Sign out** | That browser's session ends |
| The user changes or resets their password | Every other session of that user ends; the current one continues |
| An Admin clicks **Sign out of all sessions** for the user | Every session of that user ends at their next request |
| The user is suspended or deleted | Every session of that user ends immediately |
| An Admin shortens the idle timeout | Existing sessions follow the new timeout from their next request |

### API keys versus console sessions

API keys aren't sessions and the idle timeout doesn't apply to them. A key stays valid until its optional expiry date or until an Admin revokes it, however long it goes unused; a revoked key gets 401 from the next request. A key can't be used to open the console, and signing out of the console has no effect on keys. Keys belong to the workspace, not to the Admin who created them, so suspending or deleting that Admin doesn't stop them; off-boarding an Admin therefore also means rotating any key they could have seen. Handling keys safely is covered in [API Key Security Practices](nimbus-security-api-key-hygiene.md).

## Admin settings

The idle timeout is one setting per workspace. The full walkthrough is in [Configuring Session Timeouts](nimbus-admin-session-timeouts.md).

1. Sign in as an Admin and open **Settings > Security > Sessions**.
2. In **Idle timeout**, choose a value between 15 minutes and 24 hours. The list offers 15 minutes, 30 minutes, 1, 2, 4, 8, 12 and 24 hours.
3. Click **Save**. The new value applies to every session in the workspace from its next request.
4. To end one user's sessions straight away, for example after a lost laptop, open **Settings > Users**, select the user and click **Sign out of all sessions**.

Both actions are written to the audit log, and a client can pull the history of timeout changes through the API:

```http
GET /audit-log/events?action=security.session_timeout_updated HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {
      "id": "evt_5Tg2Hn8Lx",
      "action": "security.session_timeout_updated",
      "actor": {"type": "user", "id": "usr_3Fh8Wq2Kd", "display": "it.admin@client.example"},
      "occurred_at": "2026-08-11T09:42:17Z",
      "changes": {"idle_timeout_minutes": {"from": 480, "to": 60}}
    }
  ],
  "next_cursor": null
}
```

Ending a user's sessions is recorded as `user.sessions_revoked`. Filters and paging for this endpoint are in [Audit Log API](nimbus-api-audit-log.md).

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Session identifiers | Generates random, server-side session ids and protects the cookie with `Secure`, `HttpOnly` and `SameSite=Lax` | Uses a supported browser and doesn't copy cookies between machines |
| Idle timeout | Enforces the timeout on the server and defaults it to 8 hours | Chooses a timeout that matches its own policy |
| Ending access | Ends sessions on sign-out, password change, suspension and deletion | Suspends leavers promptly and uses **Sign out of all sessions** after a lost or stolen device |
| SSO users | Sends users back to the IdP when the Nimbus session ends | Sets the IdP's own session length and multi-factor rules |
| API keys | Rejects revoked and expired keys from the next request | Sets expiry dates, rotates keys and revokes any key that may be exposed |

## Evidence for auditors

The quickest evidence is a screenshot of **Settings > Security > Sessions** showing the configured idle timeout, dated on the day of the review. For changes over time, the client exports `security.session_timeout_updated` and `user.sessions_revoked` events from **Settings > Audit log**, as described in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md). An auditor who wants to see the cookie attributes can inspect them in the browser's developer tools after signing in. The underlying session controls are covered by OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate, which the CSM shares under NDA; see [Compliance Reports and Certifications](nimbus-security-compliance-reports.md).
