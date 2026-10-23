---
id: nimbus-v2-admin-managing-users
title: Inviting and Removing Users (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: guide
status: deprecated
last_updated: 2025-01-27
owner: Workspace Administration Team
---

Users on the legacy console are managed under **Admin > Users**. From there an Admin invites people by email, sets each user's role, suspends users who should lose access for a while, and deletes users who have left for good.

Workspaces that use single sign-on have one more thing to keep in mind: users created through SSO stay active in Nimbus after they leave the client's company, until an Admin suspends or deletes them here. This guide covers both the invitation route and that leaver routine.

## Before you begin

- **Role:** Admin. Only Admins see **Admin > Users**; Builders and Viewers can see their own profile only.
- **Plan Tier:** any. Inviting, suspending and deleting users work the same on every tier.
- **Roles to choose from:** Admin, Builder and Viewer. Admins manage users, SSO, API keys and webhooks; Builders create, edit and run workflows and connections; Viewers see workflows and runs but can't change them.
- **For API work:** an API key from **Admin > API keys**, as described in [Managing API Keys (v2)](nimbus-v2-admin-api-keys.md).
- **Know how the client signs in.** If the workspace uses SSO, most users arrive by signing in rather than by invitation, and the leaver steps below matter more than the invitation steps.

## How it works

Users get into a workspace in one of two ways.

**By invitation.** An Admin enters an email address and a role, and Nimbus emails an invitation link. The user sets a password when they accept. An invitation that isn't accepted expires after 7 days and must be sent again. A user invited without a role chosen gets Viewer.

**Through SSO.** When the workspace has SAML single sign-on, a user who signs in through the identity provider for the first time is created on the spot with the Viewer role. Group information in the assertion isn't read, so an Admin raises the role by hand afterwards where needed. There is no SCIM provisioning, so nothing in Nimbus changes when the user is removed from the identity provider. That removal stops them signing in through SSO, but their Nimbus account stays active, keeps its role and still appears in **Admin > Users**. See [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md) for the SAML details.

The states a user can be in:

| State | Can sign in | Takes a seat | Reversible |
|---|---|---|---|
| Invited | Not yet | No | The invitation can be cancelled or resent |
| Active | Yes | Yes | n/a |
| Suspended | No | No | Yes, with **Reactivate** |
| Deleted | No | No | No |

Suspending is the safe default for a leaver: access stops at once and the account can come back if the person returns or the suspension was a mistake. Deleting removes the user permanently. Workflows the deleted user created keep running and show "Deleted user" as their creator.

## Step-by-step

To invite a user:

1. Go to **Admin > Users** and click **Invite user**.
2. Enter the email address and pick **Admin**, **Builder** or **Viewer**.
3. Click **Send invitation**. The user appears with the state **Invited** until they accept.

To change a role, open the user, choose the new role under **Role** and click **Save**. The change applies at the user's next page load.

To handle a leaver who signed in through SSO:

1. Remove or unassign the user in the identity provider, as the client's own process requires.
2. In Nimbus, go to **Admin > Users** and search for the user's email address.
3. Open the user and click **Suspend**. Confirm the dialog. Their open console sessions end immediately.
4. Later, once the client confirms the person won't return, open the user again and click **Delete user**.

The same tasks through the API. Lists are paged with `page` and `per_page` and return a `total`:

```bash
# Invite a Builder
curl -s -X POST https://api.nimbus.omnicorp.example/invitations \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"email": "r.okafor@client.example", "role": "builder"}'

# Find a user by email, then suspend them
curl -s "https://api.nimbus.omnicorp.example/users?email=r.okafor@client.example&page=1&per_page=50" \
  -H "Authorization: Bearer <api-key>"
curl -s -X POST https://api.nimbus.omnicorp.example/users/usr_7Gk2dM4x/suspend \
  -H "Authorization: Bearer <api-key>"
```

An error comes back as the HTTP status with a message only, for example `{"error": "user is already suspended"}`; there are no error codes to match on.

## Verifying the change

- **Invitation:** the user shows **Invited** in **Admin > Users** with the date sent. After they accept, the state changes to **Active**.
- **Role change:** the **Role** column shows the new role. Ask the user to reload the console; a new Builder should see **New workflow**.
- **Suspension:** the user shows **Suspended**, and a test sign-in with their account is refused with "Your account has been suspended. Contact your workspace administrator." `GET /users/{id}` returns `"status": "suspended"`.
- **Deletion:** the user no longer appears in the list or in `GET /users`, and `total` drops by one.

For workspaces using SSO, a monthly check is worthwhile: export the client's leaver list from their HR system and compare it with the **Active** users in **Admin > Users**.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| User says the invitation link doesn't work | Invitations expire after 7 days | Click **Resend invitation** on the user, or invite them again. |
| No invitation email arrived | It was filtered as spam, or the address has a typo | Check the address in **Admin > Users**, then resend. Ask the client to check mail rules. |
| A leaver still appears as **Active** | They were removed in the identity provider only; nothing reaches Nimbus automatically | Suspend them in **Admin > Users**. |
| A new SSO user has Viewer, but should be a Builder | Roles aren't taken from identity-provider groups | An Admin changes the role by hand after the first sign-in. |
| **Delete user** is greyed out | It is the workspace's last Admin | Make another user an Admin first. |
| The client wants automatic leaver handling | Not available on this platform | Suspend users by hand, or plan the upgrade covered in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md). |
