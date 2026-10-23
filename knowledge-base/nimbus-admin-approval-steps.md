---
id: nimbus-admin-approval-steps
title: Adding Approval Steps to a Workflow
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-12
owner: Workspace Administration Team
---

An approval step pauses a workflow until a person says yes or no. Clients use it in front of anything that is expensive or hard to undo: issuing a refund in NetSuite, granting access in ServiceNow, deleting records in Salesforce. The run waits with the status `waiting_for_approval` until an approver decides, and the decision is recorded with the run.

This guide shows how to add an approval step in the builder, who can approve, where approvers see the request, and what happens when nobody answers.

## Before you begin

- **Plan Tier:** Business or Enterprise. Approval steps arrived in release 3.3.0 and aren't available on Starter; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- **Role:** Builder or Admin to add or edit the step. Approvers can have any role, including Viewer, because approving doesn't require edit rights on the workflow.
- **Approvers must be active users** of the workspace. Invite anyone who is missing first, as described in [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md).
- **Chat delivery (optional):** to send requests to a channel, the workspace needs a working Slack or Microsoft Teams connection. See the [Slack Connector](nimbus-connector-slack.md) and [Microsoft Teams Connector](nimbus-connector-microsoft-teams.md) Articles.

## How it works

When a run reaches an approval step, Nimbus creates an approval (id prefix `apr_`), sets the run's status to `waiting_for_approval` and notifies the approvers. The run holds there; the steps after it don't start. Time spent waiting doesn't count towards the 60-minute run limit, which applies only while the run is `running`.

Approvers are set on the step in one of two ways:

| Approver type | Who can decide | Typical use |
|---|---|---|
| Specific users | Any one of the listed users | A named finance lead and their deputy |
| A role | Any active user with that role (Admin, Builder or Viewer) at the moment the request is created | "Any Admin may approve" |

The first decision wins: once one approver approves or rejects, the request closes for everyone else. Nimbus doesn't support approval by several people in sequence within one step, but two approval steps in a row achieve the same thing.

The approval message is the text approvers read. It accepts expressions, so it can show the values the approver needs, for example `Refund {{trigger.body.amount}} for order {{trigger.body.order_id}} requested by {{trigger.body.agent_email}}`. The step's output carries `decision` (`approved` or `rejected`), `decided_by` and `comment`, which later steps can read as `{{steps.<step-key>.output.decision}}`.

Approvers can act from three places:

- The **Approvals** inbox in the console, which lists every pending request addressed to them.
- The approval email, whose **Review** button opens the request in the inbox after sign-in.
- A Slack or Microsoft Teams message posted to the channel chosen on the step, with **Approve** and **Reject** buttons. Nimbus matches the person who clicks to a workspace user by email address; clicks from someone who isn't an approver are refused.

An approval that gets no decision expires after 7 days. The run then fails with WF-410 and the failure is reported like any other failed run.

## Step-by-step

1. Open **Workflows**, select the workflow and make sure the builder shows the environment you want to edit (usually **Development**).
2. Click **+** between the two steps where the pause should happen and choose **Approval**.
3. Give the step a key, such as `approve_refund`. Later steps use this key in expressions.
4. Under **Approvers**, choose **Users** and pick one or more people, or choose **Role** and pick a role.
5. Write the **Message**. Insert values with expressions from the trigger or earlier steps.
6. Under **Notify in**, leave **Email** on and optionally pick a Slack or Teams connection and a channel.
7. Under **On rejection**, choose **Fail the run** (the default) or **Continue**. With **Continue**, add a condition step after the approval that branches on `{{steps.approve_refund.output.decision}}`.
8. Click **Save**, then **Publish**. Promote the new version if the workflow uses environments; see [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).

Pending approvals can also be listed and decided through the API, which is useful when a client wants approvals inside their own tooling:

```bash
# List approvals waiting for a decision
curl -s "https://api.nimbus.omnicorp.example/approvals?status=pending&limit=50" \
  -H "Authorization: Bearer <api-key>"

# Approve one, with a comment that is stored on the run
curl -s -X POST "https://api.nimbus.omnicorp.example/approvals/apr_3hT9wLq2/approve" \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Within the agreed refund policy"}'
```

`POST /approvals/{id}/reject` takes the same body. A decision made with an API key is recorded against the key rather than a person, so clients who need a named approver should decide in the console or chat.

## Verifying the change

Click **Run now** in the builder with test input. The run should stop at the approval step and the run detail page should show `waiting_for_approval`, the approvers and the rendered message. Check that:

1. Each approver sees the request in **Approvals** and has received the email.
2. If a channel was chosen, the message appears in Slack or Teams with working buttons.
3. After you approve, the run continues and the approval step's output shows `"decision": "approved"` with your name in `decided_by`.

Reject a second test run to confirm the **On rejection** setting behaves as intended.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| No **Approval** option in the step menu | Starter workspace | Approval steps need Business or Enterprise. |
| Run failed with WF-410 | Nobody decided within 7 days | Rerun the workflow, and check that the approvers still work in the workspace and receive the emails. |
| An approver doesn't see the request in **Approvals** | They weren't an approver when the request was created, for example they were given the role afterwards | Approver lists are fixed per request; ask a current approver to decide, or rerun. |
| Slack or Teams buttons answer "You can't approve this request" | The clicking user's chat email doesn't match their Nimbus email, or they aren't an approver | Decide in the Approvals inbox instead, or align the email addresses. |
| No chat message is posted | The Slack or Teams connection shows "Needs attention" | A Builder or Admin clicks **Reconnect** on the connection. |
| The run continued after a rejection | **On rejection** is set to **Continue** with no condition step | Add a condition on the step's `decision` output, or switch to **Fail the run**. |
