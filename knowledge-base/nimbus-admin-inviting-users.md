---
id: nimbus-admin-inviting-users
title: Inviting Users and Assigning Roles
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-04-27
owner: Workspace Administration Team
---

New people join an OmniCorp Nimbus workspace by invitation. An Admin enters their email address, picks the role they will have, and Nimbus emails them a link to set a password and sign in. This guide covers sending invitations from the admin console and the API, what happens to an invitation until it is accepted, and how to deal with the ones that never are.

Invitations are the right tool for adding a handful of people. To add a whole team at once, use [Importing Users in Bulk from CSV](nimbus-admin-bulk-user-import.md); if the workspace creates users from its identity provider, see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) instead.

## Before you begin

Check the following before you start:

- **Role:** you need the Admin role. Builders and Viewers can see the Users page but not the **Invite users** button.
- **Plan Tier:** invitations work on every Plan Tier, but each tier has a seat limit. Check the remaining seats on **Settings > Usage**; the limits themselves are listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- **Email delivery:** invitations come from `notifications@nimbus.omnicorp.example`. If the client's mail gateway quarantines unknown senders, ask their IT team to release messages from that address before you invite anyone.
- **The role to give:** decide in advance. A user invited without a role gets Viewer, which is often not what the client expects.

## How it works

An invitation is a record with its own id (`inv_`), separate from the user it will become. While it is pending, the person shows on **Settings > Users** with the status **Invited**, and the invitation can be resent or revoked. When they click the link in the email and set a password (or sign in through single sign-on, if it is configured), the invitation becomes an active user with a `usr_` id and the role chosen on the invitation.

The three roles do different things:

| Role | What the invited user can do |
|---|---|
| Admin | Manage users, roles, SSO, SCIM, API keys, webhooks and the Plan Tier, as well as everything a Builder can do |
| Builder | Create, edit and run workflows and connectors |
| Viewer | View workflows, runs and run history, without editing anything |

Invitations expire after 7 days. An expired invitation stays in the list with the status **Expired** so that you can see who never joined; the link in the email stops working, and the person sees "This invitation has expired" if they click it.

An invited user takes a seat once they accept, not when the email is sent. Nimbus won't send a new invitation while active users already fill the seat limit. Pending invitations don't count, so a workspace can have more open invitations than free seats; the first people to accept take the remaining seats.

## Step-by-step

To invite one or more people from the console:

1. Sign in to `https://app.nimbus.omnicorp.example` and open **Settings > Users**.
2. Click **Invite users**.
3. In **Email addresses**, enter one address per line, or paste a comma-separated list of up to 20 addresses.
4. Pick a **Role**: Admin, Builder or Viewer. Everyone in the same batch gets the same role, so invite Admins separately from Builders.
5. Optionally add a **Personal message**. It appears above the link in the invitation email.
6. Click **Send invitations**. Each address appears in the user list with the status **Invited** and an expiry date.

To resend an invitation that has expired or been lost, find the person in **Settings > Users**, open the row menu (**⋯**) and choose **Resend invitation**. Resending sends a fresh link, invalidates the old one and starts a new 7-day period. **Revoke invitation** in the same menu cancels it.

The API equivalent is `POST /invitations`, one invitation per request:

```http
POST /invitations HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 4f1c2e0a-onboarding-priya

{
  "email": "priya.nair@client.example",
  "role": "builder",
  "message": "Welcome to the finance automation workspace."
}
```

The response is the invitation, with `"status": "pending"` and an `expires_at` timestamp in UTC. `role` takes `admin`, `builder` or `viewer` and defaults to `viewer` when left out. `GET /invitations` lists invitations with cursor-based pagination, and `DELETE /invitations/{id}` revokes one. To resend through the API, delete the old invitation and post a new one for the same address.

## Verifying the change

On **Settings > Users**, filter by **Status: Invited** to see every pending invitation with its role and expiry date. Once a person accepts, their row switches to **Active**, shows a last sign-in time, and the seat count on **Settings > Usage** goes up by one.

Through the API, `GET /invitations` shows each invitation's `status`: `pending`, `accepted`, `expired` or `revoked`. An accepted invitation carries the `user_id` of the user it created, which you can read with `GET /users/{id}` to confirm the role. Every invitation sent, resent and revoked is also recorded in the audit log under **Settings > Audit log**, with the Admin who did it.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| **Send invitations** reports "No free seats" | Active users already fill the seat limit; pending invitations don't count. Suspend people who have left, or upgrade the Plan Tier. |
| The invitee never received the email | The message was filtered or quarantined. Ask them to check spam, have IT release mail from `notifications@nimbus.omnicorp.example`, then use **Resend invitation**. |
| The link says "This invitation has expired" | More than 7 days passed, or a newer invitation replaced it. Resend the invitation and ask them to use the newest email. |
| `POST /invitations` returns 409 `conflict` | The address already has a pending invitation or belongs to an existing user. Resend the pending one, or change the existing user's role instead. |
| The new user has Viewer instead of Builder | The invitation was sent without a role. Change it as described in [Changing a User's Role](nimbus-admin-changing-roles.md). |
| `POST /invitations` returns 400 `invalid_request` | The email address is malformed or `role` isn't one of the three values. Correct the body and send it again. |
