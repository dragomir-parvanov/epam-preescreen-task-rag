---
id: nimbus-release-3-3
title: Nimbus 3.3 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2025-10-06
owner: Release Management
---

Nimbus 3.3.0 was released on 2025-10-06 for every v3 workspace. It introduces approval steps, which pause a run until a person approves or rejects it, on the Business and Enterprise tiers, and adds the Microsoft Teams connector for all tiers.

Approval steps add a run status, an inbox in the console and an Approvals API, so integrations that read run statuses should be checked against the notes under Deprecations and breaking changes.

## Highlights

A workflow can now stop at a human decision: a purchase over a threshold, an access request, a customer refund. The approver sees the request in the new **Approvals** inbox, by email, and through the API, and the run continues down the approved or rejected branch. Microsoft Teams joins the catalogue with push triggers and actions for channels and chats, so approval requests and run results can be posted where teams already work. Starter workspaces get the Teams connector but not approval steps.

## New features

### Approval steps

An approval step is added in the builder like any other step (**Add step > Approval**) on Business and Enterprise workspaces. Its settings are:

| Setting | What it does |
|---|---|
| Approvers | One or more users, or everyone with a given role. Any one approver's decision completes the step. |
| Title and details | The text shown in the inbox, with expressions such as `{{trigger.body.amount}}` resolved at run time. |
| Approved branch / Rejected branch | The steps that run after each decision. A rejected branch can be left empty to end the run. |
| Notify by email | On by default; sends each approver a link to the request. |

When a run reaches the step, its status becomes `waiting_for_approval` and the request appears under **Approvals** for each approver. Once one approver decides, the request leaves every other approver's inbox and the email links show it as already decided. The approver can add a comment, which is available to later steps as `{{steps.<step-key>.output.comment}}`, along with `decision` and `decided_by`. Time spent waiting doesn't count towards the 60-minute run timeout. A request that gets no decision within 7 days expires, and the run fails with WF-410.

Approvals are also available through `GET /approvals`, `POST /approvals/{id}/approve` and `POST /approvals/{id}/reject`, with `apr_` ids; see [Approvals API](nimbus-api-approvals.md). An API key acts with Admin permissions, so a decision made by API is recorded against the key. Setup in the console is covered in [Adding Approval Steps to a Workflow](nimbus-admin-approval-steps.md), and tier availability in [Approval Steps](nimbus-tier-approval-steps.md).

### Microsoft Teams connector

The Microsoft Teams connector signs in with OAuth 2.0 through Microsoft Entra ID. Because it reads and posts channel messages across the tenant, a Microsoft Entra ID administrator must grant admin consent once before other users can create connections. The consent screen lists these Microsoft Graph delegated permissions:

- `ChannelMessage.Send` and `Chat.ReadWrite` to post in channels and chats.
- `Team.ReadBasic.All` and `Channel.ReadBasic.All` to list teams and channels in the step picker.
- `ChannelMessage.Read.All` for the **New channel message** trigger.

Push triggers fire on new channel messages and new replies within seconds. Actions post a message (plain text or an Adaptive Card), reply in a thread, send a chat message to a user, and create a channel. See [Microsoft Teams Connector](nimbus-connector-microsoft-teams.md).

## Improvements

- The run list has a **Waiting for approval** filter, and run history shows who decided an approval and when.
- Failure notifications can now include runs that end with WF-410, configurable under **Settings > Notifications**.
- The Slack connector's **Post message** action accepts Block Kit JSON directly.
- `GET /runs` accepts `status=waiting_for_approval`.
- Builders get a warning when a workflow with an approval step uses a schedule more often than hourly, as requests can pile up in the inbox.

## Fixed issues

| Issue | Area | Description |
|---|---|---|
| NIM-4572 | Environments | Promotion was blocked when a variable was defined in Production but unused in Development. |
| NIM-4575 | Connectors | NetSuite polling triggers missed records created in a subsidiary the role could read but not edit. |
| NIM-4581 | Builder | Deleting a step inside a loop removed the loop's other steps from the undo history. |
| NIM-4586 | Runs | `POST /runs/{id}/cancel` on a queued run returned 409 even though the run was cancelled. |
| NIM-4590 | Connectors | The Intercom trigger fired twice for conversations created through the Messenger. |
| NIM-4594 | Console | The user list sorted names case-sensitively. |

## Deprecations and breaking changes

Existing workflows are not affected; a run only enters the new state if its workflow has an approval step. However, `waiting_for_approval` is a new value in the run `status` field, returned by `GET /runs` and `GET /runs/{id}` and shown in run history. Client code that treats any status other than the known ones as an error, or that polls a run until it reaches a final status with a short deadline, should be updated to recognise the new value and to allow for runs that wait for up to 7 days. The run status list is otherwise unchanged.

## Upgrade notes

To start using approvals and the Teams connector:

1. Confirm the workspace is on Business or Enterprise under **Settings > Plan**.
2. Make sure each intended approver has an active account; approvers can have any role, including Viewer.
3. Add the approval step in Development, test it with **Run now**, and promote it to Production.
4. For Teams, ask the client's Microsoft Entra ID administrator to grant admin consent, then create the connection under **Connections > New connection > Microsoft Teams**.
5. Update API clients that poll run status to handle `waiting_for_approval`, and decide approvals by API where needed:

```http
POST /approvals/apr_51c0d8/approve HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"comment": "Approved within Q4 budget"}
```

```json
{
  "id": "apr_51c0d8",
  "run_id": "run_7e93f2",
  "status": "approved",
  "decided_by": "key_2d7f0a",
  "decided_at": "2025-10-14T13:02:55Z",
  "comment": "Approved within Q4 budget"
}
```

If approvals expire unexpectedly or approvers don't see requests, see [Troubleshooting Approval Steps](nimbus-troubleshooting-approvals.md).
