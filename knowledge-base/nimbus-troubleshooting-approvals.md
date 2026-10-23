---
id: nimbus-troubleshooting-approvals
title: Troubleshooting Approval Steps
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-02-23
owner: Support Engineering
---

An approval step pauses a run until a person decides whether it may continue. While it waits, the run has the status `waiting_for_approval` and the request appears in the **Approvals** inbox of every approver named on the step. An approver approves or rejects it there, from the link in the request email, or through the API. Approval steps are available on the Business and Enterprise tiers; setting them up is covered in [Adding Approval Steps to a Workflow](nimbus-admin-approval-steps.md).

Time spent in `waiting_for_approval` doesn't count towards the 60-minute run timeout. A request that nobody decides expires after 7 days, and the run then fails with WF-410.

## Symptoms

- A run has sat in `waiting_for_approval` for hours or days, and the business owner is asking why the downstream action (a purchase order, an account change) hasn't happened.
- An approver says they never received the request email and see nothing in **Approvals**.
- An approver opens the request link and sees "You are not an approver for this request".
- A run failed with WF-410 and the step log says the approval expired.
- An API call to approve or reject returns `conflict` or `not_found`.

## Common causes

**The person isn't on the approver list.** Approvers are resolved when the approval step starts. A user added to the step afterwards, or given the right role afterwards, doesn't see requests that were already waiting; only new runs pick them up.

**The email was filtered.** Request emails come from `notifications@nimbus.omnicorp.example`. Mail filters that quarantine automated messages are the usual reason an approver "never got it", even though the request is in their inbox in the console.

**Every named approver is unavailable.** When the only approvers on a step have been suspended or deleted, nobody can sign in to decide the request, and it waits until it expires. This happens most often after a leaver process removes the one finance manager named on an approval step.

**The request has already been decided or has expired.** Any one approver's decision completes the step. A second approver who acts later, or anyone acting after expiry, gets a conflict.

**The decision was made in the wrong place.** Development and Production runs create separate requests. An approver who approved the Development test run hasn't approved the Production run.

## Diagnosing the problem

1. Under **Runs**, filter by status `waiting_for_approval` and open the run. The approval step shows the request id (`apr_...`), the approvers and the time the request expires.
2. List pending requests through the API to see every waiting approval in the workspace at once:

   ```http
   GET /approvals?status=pending
   Authorization: Bearer <api-key>

   {"data": [{"id": "apr_6Wn3Xd8L", "run_id": "run_2Hk7Qe1V",
     "workflow_id": "wf_9Ty4Bc6M", "step_key": "finance_signoff",
     "status": "pending", "approvers": ["usr_3Lp8Rz2N", "usr_7Mx1Ja5K"],
     "created_at": "2026-02-16T08:04:51Z",
     "expires_at": "2026-02-23T08:04:51Z"}],
    "next_cursor": null}
   ```

3. Look up each approver under **Settings > Users** and check their status. A user who is Suspended, or who no longer appears, can't act on the request.
4. If the approver is active, ask them to open **Approvals** directly rather than relying on the email. If the request is there, the problem is mail delivery, not the step.
5. If the request isn't there, compare the approver list on the request with the one on the current version of the step. A difference means the step was edited after the run started.

## Error reference

| Code | Meaning | What to do |
|---|---|---|
| WF-410 | The approval expired after 7 days without a decision; the run failed. | Retry the run to create a new request. |
| `conflict` (409) | The request was already approved, rejected or expired when the call arrived. | Read the request with `GET /approvals?status=...` to see its final state. |
| `forbidden` (403) | The signed-in user isn't an approver on this request and isn't an Admin. | Act as a named approver or an Admin. |
| `not_found` (404) | The `apr_` id is wrong, or belongs to another workspace. | Copy the id from the run's approval step. |
| `unauthorized` (401) | The API key is missing, revoked or expired. | See [Creating and Rotating API Keys](nimbus-admin-api-keys.md). |

## Fixes

**Missing approver.** Edit the approval step, add the approver and publish. New runs use the new list. For requests already waiting, an Admin decides them: Admins can approve or reject any pending request from **Approvals** using the **All pending** filter.

**Approver suspended or deleted.** Either reactivate the user under **Settings > Users**, after which the request reappears in their inbox, or have an Admin decide it. Then change the step to name a role or several people rather than one person, so the next leaver doesn't block it.

**Deciding through the API.** An API key acts with Admin permissions, so an integration or an Admin's script can decide any pending request. Record who actually made the decision in the comment, because the audit log attributes the call to the API key:

```http
POST /approvals/apr_6Wn3Xd8L/approve
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: apr_6Wn3Xd8L-approve

{"comment": "Approved by J. Ortega (Finance) by phone; named approver unavailable"}
```

Use `POST /approvals/{id}/reject` the same way to reject. The run continues, or ends, within a few seconds of the call. See [Approvals API](nimbus-api-approvals.md) for the full request and response.

**Expired request.** An expired request can't be revived. Retry the failed run from run history (**Retry** on the run, or `POST /runs/{id}/retry`), which starts the workflow again with the same trigger input and sends a fresh request to the current approvers.

**Emails not arriving.** Ask the client's mail administrator to release and trust messages from `notifications@nimbus.omnicorp.example`; see [Troubleshooting Missing Notifications](nimbus-troubleshooting-notifications.md).

## Escalating to support

Collect before opening a ticket:

- workspace id, run id and approval id (`apr_...`);
- the workflow id and the version that was running;
- the approvers on the request and their status under **Settings > Users**;
- the exact API response, if the problem appeared through the API;
- for missing emails, confirmation that the request is (or isn't) visible in the approver's **Approvals** inbox.
