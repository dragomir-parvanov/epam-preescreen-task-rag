---
id: nimbus-faq-user-management
title: User Management FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-10-19
owner: Customer Success Enablement
---

User management questions come from Admins at almost every client: how invitations behave, which role to give whom, how seats are counted, what the difference is between suspending and deleting someone, how to load many users at once, and what happens to a leaver's workflows. This FAQ answers them for workspaces that manage users in the Nimbus console.

Clients who sign people in through their identity provider should also read [Configuring SSO with SAML 2.0](nimbus-sso-saml.md), and Enterprise clients who provision users automatically should read [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md). Identity-provider behaviour is described there, not here.

## General questions

**What do the three roles allow?**

Admins manage users, roles, SSO, SCIM, API keys, webhooks and the Plan Tier. Builders create, edit and run workflows and connectors. Viewers see workflows, runs and run history but can't change anything. Someone invited without a role gets Viewer.

**How are seats counted?**

Every active user takes a seat, whatever their role. A pending invitation doesn't take one until it is accepted, and a suspended user doesn't take one at all. The seat count is on Settings > Usage, and the limit for each Plan Tier is in [Seat Limits and How Seats Are Counted](nimbus-tier-seat-limits.md).

**What is the difference between suspending and deleting a user?**

| | Suspend | Delete |
|---|---|---|
| Can sign in | No | No |
| Takes a seat | No | No |
| Account and settings kept | Yes | No |
| Can be undone | Yes, with Reactivate | No |
| Workflows they own | Keep running; an Admin transfers ownership | Keep running; an Admin transfers ownership |
| Shown in audit history | Yes, under their name | Yes, under their name |

Suspend is the safer choice for leavers and long absences. Delete only once the client is sure the account won't be needed again.

## Setup questions

**How do I change someone's role?**

In Settings > Users, open the user, choose the new role in the Role field and click Save. The change applies at the user's next page load. The API equivalent is `PATCH /users/{id}` with a `role` field.

**How do I resend or cancel an invitation?**

Pending invitations are listed in Settings > Users > Pending invitations. Resend issues a new link and restarts the 7-day validity; Revoke cancels it, and the old link stops working at once.

### How do I import users in bulk?

Bulk import loads users from a CSV file of up to 500 rows per file. The file needs a header row and one user per line:

```csv
email,first_name,last_name,role
priya.nair@client.example,Priya,Nair,Builder
tom.becker@client.example,Tom,Becker,Viewer
ana.ribeiro@client.example,Ana,Ribeiro,Admin
```

To import it:

1. Go to Settings > Users and click Import CSV.
2. Upload the file. Nimbus validates every row and lists errors such as an unknown role or a malformed email address before anything is sent.
3. Fix any rows with errors, or untick them, and click Send invitations.

Each row becomes an ordinary invitation, so it expires after 7 days and the person takes a seat only when they accept. A row with an empty role gets Viewer.

## Limits and edge cases

**What happens to workflows owned by someone who leaves?**

Every workflow has an owner, who must be a Builder or Admin. When the owner is suspended or deleted, their workflows keep running, and an Admin must transfer ownership: in Workflows, filter by Owner, select the workflows and choose Transfer ownership. The same is needed if the owner is changed to Viewer.

**Can the workspace run out of seats while invitations are pending?**

Yes. Pending invitations don't take seats, so a workspace can have more outstanding invitations than free seats. The first people to accept take the remaining seats, and the rest see a "No seats available" message until a seat is freed or the tier is upgraded.

**Can an Admin remove their own Admin role?**

Only if another active Admin exists. A workspace always keeps at least one active Admin, so the last one can't be demoted, suspended or deleted.

**Can invitations be sent through the API?**

Yes, with an API key: `POST /invitations` with an email address and a role sends an invitation, `GET /invitations` lists the pending ones, and `DELETE /invitations/{id}` revokes one. Accepting still happens through the link in the email, and the response's `inv_` id is what the client should store to track it.

**Can a user belong to two workspaces?**

Yes, with the same email address. They are invited to each separately and take a seat in each.

## Troubleshooting questions

**An invitation shows "Expired".**

It wasn't accepted within 7 days. Click Resend in Pending invitations.

**The CSV import rejects every row.**

Check that the header row is exactly `email,first_name,last_name,role`, that the file is UTF-8, and that it has no more than 500 data rows. Split larger lists into several files.

**A suspended user still appears in the user list.**

That is expected. Suspended users stay listed with the status Suspended so they can be reactivated; filter by Status: Active to hide them.

**A user's email address changed after a rename or a domain move.**

The email address is the user's Nimbus login. An Admin opens the user in Settings > Users, edits Email and clicks Save; the user confirms the new address from a verification email, and their role, workflows and run history stay with the account. Don't invite the new address as a second user, which would take a second seat.

**A leaver was removed in the identity provider but still shows as active.**

How Nimbus reacts depends on how users are provisioned. See [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) for sign-in-only setups and [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md) for automatic deprovisioning on Enterprise.

## Where to find more

- [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md) and [Changing a User's Role](nimbus-admin-changing-roles.md).
- [Importing Users in Bulk from CSV](nimbus-admin-bulk-user-import.md).
- [Suspending, Reactivating and Deleting Users](nimbus-admin-suspending-users.md).
- [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md) and [Running User Access Reviews](nimbus-security-access-reviews.md).
