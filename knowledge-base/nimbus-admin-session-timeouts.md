---
id: nimbus-admin-session-timeouts
title: Configuring Session Timeouts
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-10
owner: Workspace Administration Team
---

A console session ends after a period without activity, so an unattended laptop doesn't leave a Nimbus workspace open. The idle timeout is 8 hours by default. An Admin can shorten it to as little as 15 minutes or lengthen it to as much as 24 hours under **Settings > Security > Sessions**, and can sign a single user out of every session at once.

Clients usually ask about this after a security review asks for a shorter timeout, or when Builders complain about being signed out in the middle of editing a workflow. Both are covered below.

## Before you begin

- **Role:** Admin. Builders and Viewers can see their own sessions but can't change the timeout or sign out other users.
- **Plan Tier:** any. The setting works the same on Starter, Business and Enterprise.
- **Agree the value with the client's security team.** The timeout applies to every user in the workspace; there is no per-role or per-user value.
- **Know what isn't affected.** API keys aren't sessions and don't time out; they stay valid until they expire or are revoked (see [Creating and Rotating API Keys](nimbus-admin-api-keys.md)). Running workflows aren't affected either: a run continues whether or not its owner is signed in.

## How it works

The console tracks the time of each user's last activity in each browser session. When the gap since that activity reaches the idle timeout, the session ends and the next action asks the user to sign in again.

What counts as activity, and what doesn't:

| Counts as activity | Doesn't count |
|---|---|
| Opening a page or switching tabs inside the console | Moving the mouse or scrolling without clicking |
| Clicking a button, filter or link | Automatic refreshes, such as the live status on **Runs** |
| Typing in the builder (each autosave of the draft) | A browser tab left open in the background |
| Approving or rejecting in **Approvals** | Workflow runs, API calls with an API key, or webhook deliveries |

Allowed values run from 15 minutes to 24 hours, and a workspace that has never changed the setting uses the default of 8 hours. The console offers 15 minutes, 30 minutes, 1, 2, 4, 8, 12 and 24 hours.

A new value applies to existing sessions straight away. If the timeout is shortened from 8 hours to 30 minutes, anyone who has been idle for more than 30 minutes is signed out at their next action.

### Open builder tabs

The builder saves the draft automatically a few seconds after each change, and each autosave counts as activity, so someone actively editing isn't signed out. When an idle builder tab does time out, Nimbus shows a **Session expired** dialog over the builder instead of navigating away. Any change made after the last autosave is held in the browser tab; after the user signs in again in that dialog, the change is saved and they carry on. If they close the tab or sign in from a different tab first, that last unsaved change is lost.

Users who sign in with SSO are sent to their identity provider when the session ends. If their session with the identity provider is still valid, they come straight back without typing a password; see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md).

## Step-by-step

To change the idle timeout:

1. Go to **Settings > Security > Sessions**.
2. Under **Idle timeout**, choose a value between 15 minutes and 24 hours.
3. Click **Save**. The confirmation shows the old and new values.

To sign one user out of every session, for example when a laptop is lost or someone leaves the client's company:

1. Go to **Settings > Users** and open the user.
2. Open the **Sessions** tab. It lists each active session with its browser, operating system, when it started and when it was last active.
3. Click **Sign out all sessions** and confirm.

Signing out ends the user's console sessions only. It doesn't suspend the account or touch API keys, so for someone who has left, follow it with [Suspending, Reactivating and Deleting Users](nimbus-admin-suspending-users.md).

The timeout is a console setting with no API endpoint, but every change is written to the audit log, which an Admin can query:

```http
GET /audit-log/events?action=security.session_timeout_updated&limit=10 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "id": "evt_9aK3mX0p",
      "action": "security.session_timeout_updated",
      "actor": {"type": "user", "id": "usr_2Lw7eT5d"},
      "occurred_at": "2026-08-04T09:12:44Z",
      "details": {"previous_minutes": 480, "new_minutes": 30}
    }
  ],
  "next_cursor": null
}
```

## Verifying the change

1. Reload **Settings > Security > Sessions** and check the **Idle timeout** shows the new value.
2. Run a quick test with a short value: set 15 minutes in a test workspace, leave a console tab untouched for 16 minutes, then click anything. The sign-in prompt should appear.
3. After **Sign out all sessions**, the user's **Sessions** tab is empty, and the audit log has a `user.sessions_revoked` event naming the Admin.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Users are signed out sooner than the setting | Their browser blocks or clears cookies when closed, or a browser extension clears site data | Ask them to allow cookies for `app.nimbus.omnicorp.example`. |
| A Builder lost changes after timing out | They signed in from a new tab, or closed the timed-out tab, before signing in through the **Session expired** dialog | Sign in from the dialog in the same tab next time; reduce the gap with a longer timeout if the client agrees. |
| A user stays signed in although they were idle | A console page with clicks from an automated tool, such as a kiosk refresher, counts as activity | Remove the tool, or sign the user out with **Sign out all sessions**. |
| SSO users are never asked for a password after timing out | Their identity provider session is still valid | Expected. Shorten the session in the identity provider if the client wants a fresh sign-in. |
| An integration stopped after **Sign out all sessions** | Unrelated: signing out doesn't affect API keys | Check whether the key was revoked or expired in **Settings > Developers > API keys**. |
| A value under 15 minutes is requested | The minimum is 15 minutes | Explain the allowed range; it can't be lower. |
