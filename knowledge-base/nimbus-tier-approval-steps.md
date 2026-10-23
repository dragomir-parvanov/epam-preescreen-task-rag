---
id: nimbus-tier-approval-steps
title: Approval Steps
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-11-03
owner: Product Operations
---

An approval step pauses a workflow run until a person decides whether it should continue. Clients use it wherever an automated action needs a human sign-off first: a refund above a threshold, a new supplier record in NetSuite, a production access request raised in Jira Cloud. The run waits with status `waiting_for_approval`, the approvers are notified, and the first decision releases or stops it.

Approval steps were introduced in release 3.3.0 (2025-10-06). This guide covers tier availability, how a waiting run behaves, the numbers that apply, and what a Plan Tier change does to workflows and runs that use approvals.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Approval steps in workflows | No | Yes | Yes |
| Approvals inbox (**Approvals**) | No | Yes | Yes |
| Approvals API (`/approvals`) | No | Yes | Yes |
| Expiry of an undecided approval | Not applicable | 7 days | 7 days |

On Starter, **Approval** doesn't appear in the builder's step list, and importing a workflow that contains one fails validation.

## How it works

When a run reaches an approval step, Nimbus:

1. Sets the run status to `waiting_for_approval` and records an approval with an `apr_` id.
2. Emails each approver a summary built from the step's message, with **Approve** and **Reject** links that open the approval in the console.
3. Adds the approval to the **Approvals** inbox of every approver.

The first approver to decide settles it. **Approve** resumes the run at the next step; the step's output carries `decision`, `decided_by` and the approver's comment, so later steps can use `{{steps.<step-key>.output.comment}}`. **Reject** ends the run with status `cancelled`, and the rejection and comment are shown in run history. Other approvers see the approval as decided and can no longer act on it.

Approvers are chosen per step, either as named users or as everyone holding a role. Any active user can be an approver, including Viewers: approving doesn't require edit rights on the workflow, which suits finance or legal reviewers who shouldn't build workflows. A user who is suspended while an approval is open simply drops out of the approver list.

### Timing and the run quota

Time spent waiting doesn't count towards the 60-minute run timeout. The timeout clock stops when the run enters `waiting_for_approval` and resumes when it is approved, so a run can wait for days and still have its full remaining time afterwards.

If nobody decides within 7 days, the approval expires: the run fails with WF-410, and the approval is marked expired in the inbox. Failure notifications fire for WF-410 like any other failure, so expiries reach the people configured under **Settings > Notifications**.

A run with an approval step counts once against the monthly run quota, at the moment it starts. Resuming after approval doesn't count again, and a rejected or expired run still used its one run.

## Turning it on

Approval steps need no workspace setting on Business and Enterprise; a Builder adds them per workflow.

1. Open the workflow in **Workflows** and select **Add step > Approval** at the point where the run should pause.
2. Give the step a key, such as `finance_sign_off`, and write the message approvers will see. Expressions are allowed, for example `{{trigger.body.customer_name}}`.
3. Under **Approvers**, add named users, a role, or both.
4. Optionally add a condition step before it, so only some runs need sign-off (for example, refunds over a set amount).
5. Run a **Test run**; in test mode the approval is sent only to the person testing.
6. Publish the workflow.

The step as it appears in the workflow definition returned by `GET /workflows/{id}`:

```json
{
  "key": "finance_sign_off",
  "type": "approval",
  "message": "Refund of {{trigger.body.amount}} {{trigger.body.currency}} for {{trigger.body.customer_name}}. Approve?",
  "approvers": {
    "users": ["usr_5TgW2c", "usr_9Lk3Xa"],
    "roles": ["admin"]
  }
}
```

Approvers who prefer to work from their own tools can decide through the API, for example from a chat bot:

```http
POST /approvals/apr_7Qm4Rz/approve HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{ "comment": "Checked against the original order." }
```

`GET /approvals` lists open approvals, newest first, with cursor pagination. Decisions made through an API key are recorded against the key, not a person, so clients with strict sign-off rules should keep decisions in the console. The builder walkthrough with screenshots is in [Adding Approval Steps to a Workflow](nimbus-admin-approval-steps.md).

## Limits

| Item | Limit |
|---|---|
| Expiry of an undecided approval | 7 days, fixed; then WF-410 |
| Approval steps per workflow | 10 |
| Approvers per step | 25 named users, plus any number of roles |
| Decisions needed | 1; the first decision settles the approval |
| Comment length | 1,000 characters |
| Run timeout while waiting | Paused; the 60-minute limit applies to running time only |

The expiry can't be shortened or extended. A workflow that needs a shorter deadline can send a reminder from a parallel scheduled workflow that reads `GET /approvals`.

## When the Plan Tier changes

Upgrading from Starter makes approval steps available in the builder immediately.

A downgrade to Starter takes effect at the end of the current billing period:

1. Every workflow that contains an approval step is deactivated, and it can't be activated again until the step is removed.
2. Runs already in `waiting_for_approval` are left alone. Approvers can still decide them from the inbox or the email links until they expire after 7 days, and an approved run finishes normally.
3. No new approvals are created after the downgrade, and the **Approvals** inbox disappears once the last open approval is settled.

Before a downgrade, list the affected workflows with the client and decide whether to remove the approval step or replace it with a condition and a notification. Moving between Business and Enterprise doesn't change anything for approvals. For other features a downgrade affects, see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
