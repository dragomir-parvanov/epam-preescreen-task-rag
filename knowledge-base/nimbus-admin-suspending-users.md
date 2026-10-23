---
id: nimbus-admin-suspending-users
title: Suspending, Reactivating and Deleting Users
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-09
owner: Workspace Administration Team
---

When someone leaves a client's organisation, or should lose access for a while, an Admin removes them from the OmniCorp Nimbus workspace in one of two ways. Suspension is reversible: it blocks sign-in and frees the person's seat, but keeps their account, history and workflow ownership in place. Deletion is permanent and removes the account for good.

Most clients should suspend first and delete later, once the person's workflows have a new owner and nobody needs their account any more. This guide covers both, plus reactivation, for workspaces where an Admin manages users by hand.

## Before you begin

- **Role:** only Admins can suspend, reactivate or delete users.
- **Plan Tier:** available on every tier.
- **Who manages the account:** if the user was created by SCIM provisioning, their row on **Settings > Users** carries a **Provisioned by SCIM** badge. Don't suspend or delete those users in Nimbus; unassign or deactivate them in the identity provider instead, as described in [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md). A change made in the console would be reversed at the next sync.
- **Workflows they own:** open **Workflows** and filter by **Owner** to see what the person is responsible for. They keep running after a suspension or deletion, but an Admin must then transfer them to a new owner.
- **The last Admin:** a workspace must keep at least one Admin, so the only Admin can't be suspended or deleted.

## How it works

The three states of a user account behave as follows:

| | Active | Suspended | Deleted |
|---|---|---|---|
| Can sign in to the console | Yes | No | No |
| Takes a seat | Yes | No | No |
| Keeps role and profile | Yes | Yes | No |
| Owns workflows | Yes | Yes, until an Admin transfers them | Yes, until an Admin transfers them |
| Name kept on past runs and audit-log entries | Yes | Yes | Yes, shown as "Deleted user" with the `usr_` id; the email is removed |
| Can be undone | — | Yes, by reactivation | No |

Suspension takes effect at once. Any console session the person has open is ended, and their next request is refused with "Your account has been suspended. Contact your workspace Admin." A suspension made in the console has no end date: the account stays suspended until an Admin reactivates or deletes it.

The workflows a suspended user owns keep running on their schedules and triggers, and connections they created keep working. Failure notifications addressed to the owner, however, go to a mailbox nobody reads any more, which is why an Admin should transfer ownership soon after suspending someone; see [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md).

Reactivation puts the account back exactly as it was: the same role, the same `usr_` id and the same workflows. It needs a free seat, because a reactivated user takes a seat again. Deletion, by contrast, can't be reversed by the Admin or by OmniCorp support. To bring a deleted person back, invite them again; they get a new account with a new id.

API keys are not tied to the person who created them, so keys an Admin created keep working after that Admin is suspended or deleted. If the departing person ever saw a key's secret, rotate the key as described in [Creating and Rotating API Keys](nimbus-admin-api-keys.md).

Suspending a user sends the `user.suspended` webhook event to any endpoint subscribed to it, so client systems that mirror Nimbus users can react.

## Step-by-step

### Suspending and reactivating

1. Open **Settings > Users** and find the person.
2. Open the row menu (**⋯**) and choose **Suspend user**.
3. Read the summary, which lists the workflows the user owns, and click **Suspend**. The row shows the status **Suspended** and the seat count drops by one.
4. To undo it later, open the same menu and choose **Reactivate user**, then confirm.

### Deleting a user

1. Transfer every workflow the person owns to another Builder or Admin. Deletion doesn't wait for this and the workflows keep running, but until they are transferred their failure alerts reach nobody.
2. Open the row menu (**⋯**) and choose **Delete user**.
3. Type the user's email address into the confirmation box and click **Delete permanently**.

The API offers the same three actions. A typical offboarding script suspends at once and deletes later:

```http
POST /users/usr_5mq81z/suspend HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

POST /users/usr_5mq81z/reactivate HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

DELETE /users/usr_5mq81z HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

The suspend and reactivate calls return the updated user object with its new `status`. `DELETE` returns 204 with no body.

## Verifying the change

Filter **Settings > Users** by **Status: Suspended** to see everyone currently suspended. `GET /users/{id}` returns `"status": "suspended"` or `"status": "active"`; after deletion it returns 404 `not_found`. **Settings > Usage** shows the seat count going down after a suspension and up again after a reactivation. Every action is also written to **Settings > Audit log** as `user.suspended`, `user.reactivated` or `user.deleted`, together with the Admin who performed it.

## Troubleshooting

| Problem | Likely cause | What to do |
|---|---|---|
| **Delete user** is disabled | The person is the workspace's only Admin. | Promote another user to Admin first, then delete. |
| `DELETE /users/{id}` returns 409 `conflict` | Same cause through the API: the user is the last active Admin. | Promote another user to Admin with `PATCH /users/{id}`, then retry. |
| **Reactivate user** fails with "No free seats" | Reactivation needs a seat and the workspace is full. | Suspend someone else or upgrade the Plan Tier, then reactivate. |
| A suspended user is active again | The user is managed by SCIM and is still assigned in the identity provider. | Unassign or deactivate them in Okta or Microsoft Entra ID. |
| **Suspend user** is greyed out | The person is the workspace's only Admin. | Promote another user to Admin first. |
| A suspended user's workflows stopped sending failure alerts | Alerts still go to the suspended owner. | Transfer ownership so the new owner receives them. |
