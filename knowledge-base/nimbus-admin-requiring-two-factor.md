---
id: nimbus-admin-requiring-two-factor
title: Requiring Two-Factor Authentication
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-07-13
owner: Workspace Administration Team
---

Two-factor authentication adds a one-time code from an authenticator app to every password sign-in. An Admin turns the requirement on for the whole workspace under **Settings > Security > Two-factor authentication**; after that, nobody who signs in with a password can reach the console without a second factor.

Nimbus supports time-based one-time passwords (TOTP) from any standard authenticator app, such as Microsoft Authenticator, 1Password or Authy. Text-message and email codes aren't offered.

## Before you begin

Confirm these points before switching the requirement on:

- You are an **Admin**. Builders and Viewers can enrol themselves voluntarily but can't change the workspace requirement.
- The workspace can be on **any Plan Tier**.
- **Your own authenticator app is ready.** Admins are asked to enrol before the setting saves, so the Admin turning it on is never locked out.
- **Users have been told.** Everyone affected is asked to enrol the next time they sign in, and they'll need their phone at hand. A short notice to the client's users avoids a wave of support tickets.
- **You know who signs in with SSO.** Users who sign in through the workspace's SAML identity provider aren't affected, because their second factor is handled by the identity provider; see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md).

## How it works

The requirement applies to password sign-in only. Once it is on:

| User | What happens at their next sign-in |
|---|---|
| Signs in with a password and hasn't enrolled | After the password, they see **Set up two-factor authentication** and can't continue until they finish enrolment. |
| Signs in with a password and has enrolled | After the password, they enter the 6-digit code from their app. |
| Signs in with SSO | No change. Nimbus doesn't ask for a second code. |
| Is already signed in | Their current session continues until it ends; the requirement applies at the next sign-in. Use **Sign out all sessions** on a user to apply it sooner, as described in [Configuring Session Timeouts](nimbus-admin-session-timeouts.md). |

Enrolment takes about a minute. The user scans a QR code with their app (or types the setup key shown under it), enters the first code to prove the app works, and is then shown 10 recovery codes.

### Recovery codes

Recovery codes are for when the phone is lost. Each code is 10 characters, works once, and can be typed instead of the 6-digit app code. Users should store them in a password manager. A user can generate a new set under their avatar menu > **Account > Two-factor authentication > Regenerate recovery codes**, which invalidates the old set.

Codes from the app change every 30 seconds. Nimbus accepts the current code and the one either side of it, which covers small clock differences on the user's phone. Wrong codes count towards the same limit as wrong passwords: after 10 failed attempts the account is locked for 15 minutes.

Turning the requirement off later doesn't remove anyone's enrolment. Users who enrolled keep being asked for a code until they remove their own second factor.

## Step-by-step

To require two-factor authentication for the workspace:

1. Go to **Settings > Security > Two-factor authentication**.
2. If you haven't enrolled yourself, click **Set up for my account** and complete enrolment with your authenticator app. Save your recovery codes.
3. Switch **Require two-factor authentication for password sign-in** on.
4. Read the confirmation, which shows how many active users sign in with a password and haven't enrolled yet, and click **Require**.

To reset a user's second factor, for example after they lose their phone and their recovery codes:

1. Confirm the user's identity through a channel the client trusts, such as a call to a known number. A reset is exactly what an attacker would ask for.
2. Go to **Settings > Users** and open the user.
3. Click **Reset two-factor authentication** and confirm.
4. Tell the user to sign in again. They'll go through enrolment as if for the first time.

The requirement itself is set only in the console, but the API shows who has enrolled. Each user returned by `GET /users` and `GET /users/{id}` carries the sign-in method and enrolment state:

```json
{
  "id": "usr_4Hn8cQ2v",
  "email": "j.moreau@client.example",
  "role": "builder",
  "status": "active",
  "sign_in_method": "password",
  "two_factor_enrolled": false
}
```

Filter the list on `sign_in_method` and `two_factor_enrolled` to produce a list of users who still need to enrol.

## Verifying the change

1. Open **Settings > Security > Two-factor authentication**. The status line reads **Required for password sign-in** with the date and the Admin who turned it on.
2. Open **Settings > Users** and add the **Two-factor** column. Password users show **Enrolled** or **Pending**; SSO users show **Not applicable**.
3. Ask a test user who signs in with a password to sign out and back in. They should be asked to enrol, or for a code if already enrolled.
4. The change and every reset are recorded in the audit log under the actions `security.two_factor_policy_updated` and `user.two_factor_reset`; see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| "Invalid code" every time, with the right app | The phone's clock is wrong, so its codes are out of step | Turn on automatic date and time on the phone, then try again. |
| User lost their phone and their recovery codes | No second factor left | An Admin resets their two-factor authentication after confirming who they are. |
| The only Admin lost both | Nobody in the workspace can reset them | The client contacts OmniCorp support through their CSM; support verifies the request with the account owner before resetting. |
| An SSO user is asked for a code | They used the email-and-password form instead of **Sign in with SSO**, so they have a password as well | Have them use **Sign in with SSO**. |
| Account locked after code attempts | 10 failed attempts lock the account for 15 minutes | Wait 15 minutes, or use a recovery code once the lock ends. |
| Setting won't save | The Admin making the change hasn't enrolled | Complete **Set up for my account** first. |
