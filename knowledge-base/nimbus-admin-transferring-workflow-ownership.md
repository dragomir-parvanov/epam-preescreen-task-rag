---
id: nimbus-admin-transferring-workflow-ownership
title: Transferring Workflow Ownership
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-05
owner: Workspace Administration Team
---

Every workflow in OmniCorp Nimbus has exactly one owner, a Builder or Admin who is answerable for it. Ownership doesn't restrict who can edit a workflow, since any Builder can, but it decides who hears about the workflow's problems and whose name stands against it. When the owner leaves, changes job or is suspended, an Admin moves their workflows to someone else.

Transfers are quick and don't interrupt the workflow, but they are easy to forget. A workflow whose owner was suspended months ago still runs, and its failure alerts still go to a mailbox nobody reads.

## Before you begin

- **Role:** only an Admin can transfer ownership. A Builder can see who owns a workflow but can't change it, even for workflows they own themselves.
- **Plan Tier:** available on every tier.
- **The new owner:** must be an active user with the Builder or Admin role. Viewers and suspended users can't own workflows, and a person with a pending invitation isn't a user yet.
- **Connections:** list the connections the workflows use (the **Connections** tab in each workflow shows them). If any were authorised with the outgoing owner's personal account in a third-party app, plan to reconnect them with an account that will stay active.

## How it works

The owner is the default recipient of a workflow's failure notifications, unless the workflow or **Settings > Notifications** names other recipients. The owner is also shown on the **Workflows** list and in run history, and is the person approvers and colleagues contact about the workflow.

Transferring ownership changes only the `owner_id`. What it does and doesn't touch:

| Aspect | After a transfer |
|---|---|
| Schedules, triggers and the published version | Unchanged; the next run starts as normal |
| Runs already queued or running | Finish as they would have |
| Failure notifications addressed to "the owner" | Go to the new owner from the next failure |
| Version history | Unchanged; earlier versions still show who published them |
| Connections used by the workflow | Unchanged; they keep the account they were authorised with |
| Folder | Unchanged |

The connections row matters most. A connection belongs to the workspace, not to the workflow owner, and a transfer doesn't re-authorise it. If the outgoing owner connected Salesforce or Microsoft Teams with their own account and that account is later disabled at the client, the connection's steps start failing with CONN-401 and the connection shows **Needs attention**. A Builder or Admin then opens it under **Connections** and clicks **Reconnect** with a service account or the new owner's account.

When an owner is suspended or deleted, Nimbus doesn't pick a new owner automatically. The workflows keep running in the meantime, and the **Workflows** list shows an **Owner suspended** badge on each one until an Admin transfers it. The same applies when an owner's role is lowered to Viewer: the role change asks for a new owner for each of their workflows before it is saved, because a Viewer can't own one; see [Changing a User's Role](nimbus-admin-changing-roles.md). Deleting a user is blocked until all of their workflows have a new owner; see [Suspending, Reactivating and Deleting Users](nimbus-admin-suspending-users.md).

## Step-by-step

### One workflow

1. Open **Workflows** and click the workflow.
2. Open the **⋯** menu at the top right of the builder and choose **Transfer ownership**.
3. Pick the new owner from the list, which only offers active Builders and Admins.
4. Click **Transfer**. The new owner receives an email naming the workflow and the Admin who made the change.

### All of a user's workflows

1. Open **Settings > Users** and find the outgoing owner.
2. Open the row menu (**⋯**) and choose **Transfer workflows**. The dialog lists every workflow the user owns.
3. Choose one new owner for all of them, or switch to **Assign individually** to split them between several people.
4. Click **Transfer all**. Nimbus sends each new owner a single email that lists the workflows they received.

The API has no bulk call; scripts send one `PATCH /workflows/{id}` per workflow with the new `owner_id`. To find them, list workflows filtered by owner first:

```http
GET /workflows?owner_id=usr_5mq81z&limit=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

PATCH /workflows/wf_7730 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"owner_id": "usr_2b9fta"}
```

The response is the updated workflow. Follow `next_cursor` if the user owns more than 100 workflows.

## Verifying the change

Filter **Workflows** by **Owner** and select the outgoing user: the list should be empty, and any **Owner suspended** badges should be gone. `GET /workflows?owner_id=<old-user-id>` should return an empty `data` array. Each transfer is recorded in **Settings > Audit log** as `workflow.ownership_transferred`, with the previous and the new owner. To confirm that notifications follow, open the workflow's **Notifications** tab: when it is set to "the owner", it now names the new owner.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| The person isn't offered as a new owner | They are a Viewer, suspended, or still invited. | Change their role to Builder, reactivate them, or wait until they accept. |
| `PATCH /workflows/{id}` returns 400 `invalid_request` with "Owner must be a Builder or Admin" | Same restriction through the API. | Choose an eligible user or change their role first. |
| `PATCH /workflows/{id}` returns 404 `not_found` | The workflow id or the user id is wrong, or the user was deleted. | Check both ids with `GET /workflows/{id}` and `GET /users/{id}`. |
| Steps fail with CONN-401 after the old owner left | A connection used the old owner's personal account, which the client disabled. | Reconnect it under **Connections** with an account that will stay active. |
| Failure alerts still go to the old owner | The workflow names that person explicitly as a recipient. | Edit the workflow's notification recipients; see [Configuring Failure Notifications](nimbus-admin-failure-notifications.md). |
| **Transfer ownership** isn't in the menu | You are signed in as a Builder. | Ask an Admin to make the transfer. |
