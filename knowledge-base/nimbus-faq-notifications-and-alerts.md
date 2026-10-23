---
id: nimbus-faq-notifications-and-alerts
title: Notifications and Alerts FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-23
owner: Customer Success Enablement
---

Nimbus tells people about problems and pending work in two ways: emails to people in the workspace, and webhook events to the client's own systems. This FAQ covers the questions CSMs get about both: failure notifications, the run quota alerts at 80% and 100%, approval requests, "Needs attention" emails for broken connections, and which webhook events to use when a client wants to automate their own alerting.

## General questions

**Which notifications does Nimbus send, and to whom?**

| Notification | Sent when | Recipients |
|---|---|---|
| Run failure alert | A run ends as failed or timed_out | Recipients set under Settings > Notifications, else the workspace default recipients |
| Quota alert | The workspace reaches 80% and 100% of its monthly workflow runs | All Admins |
| Approval request | A run reaches an approval step | The approvers named on the step |
| Connection needs attention | A connection's authorisation expires or is revoked | The connection's creator and all Admins |
| SCIM token expiry | 14 days before the provisioning token expires (Enterprise) | All Admins |
| Invitation | An Admin invites a user | The invited person |

All notification emails come from notifications@nimbus.omnicorp.example and carry the workspace name in the subject line, which helps clients with several workspaces filter them.

**Are notifications sent for every failed step?**

No. A failed connector step is retried first (3 times by default), and a failure alert is sent only when the run itself fails. Steps that succeed on a retry generate no email.

**What can a client automate with webhooks instead of email?**

Nimbus sends webhook events for `workflow.run.completed`, `workflow.run.failed`, `user.provisioned`, `user.suspended` and `connector.disconnected`. Clients typically route `workflow.run.failed` and `connector.disconnected` into their incident or chat tooling. A `workflow.run.failed` delivery looks like this:

```json
{
  "id": "evt_5Rn2Vh",
  "event": "workflow.run.failed",
  "created_at": "2026-03-12T06:04:51Z",
  "data": {
    "workflow_id": "wf_8Tq1Lc",
    "workflow_name": "Nightly invoice sync",
    "run_id": "run_2Hb7Xe",
    "status": "failed",
    "error_code": "CONN-401",
    "failed_step": "fetch_invoices"
  }
}
```

The receiving endpoint must verify each delivery as described in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Setup questions

**Where are the default recipients set?**

Under Settings > Workspace > Default notification recipients. They receive run failure alerts for every workflow that doesn't have its own recipients. Recipients can be workspace users or external addresses such as a shared team mailbox.

**How is a webhook endpoint registered for these events?**

An Admin adds it under Settings > Developers > Webhooks, ticks the events to subscribe to, and copies the signing secret shown once. The same can be done with `POST /webhooks/endpoints`.

### How do I set up failure notifications?

Failure alerts are configured by an Admin:

1. Go to Settings > Notifications.
2. Under Run failures, choose Every failed run or Daily digest. The digest is sent at 08:00 in the workspace time zone and lists every failed and timed-out run of the previous 24 hours.
3. Add the workspace-wide recipients, or leave the field empty to use the default recipients.
4. To send alerts for one workflow to a different team, click Add override, pick the workflow and set its own recipients.
5. Click Save, then use Send test alert to check that the email arrives.

## Limits and edge cases

**When exactly do the quota alerts arrive?**

Once at 80% and once at 100% of the month's workflow runs, per calendar month. At 100%, scheduled, event-triggered and manual runs are all rejected with WF-300 until the quota resets on the 1st of the month (UTC) or the tier is upgraded. Test runs in the builder don't count towards the quota. The current position is on Settings > Usage.

**How long does an approver have to respond?**

Approvals expire after 7 days. A run whose approval gets no decision in that time fails with WF-410, which in turn triggers a failure alert. Approvers can act from the email or from the Approvals inbox in the console.

**Does a run waiting for approval count as failed?**

No. Its status is `waiting_for_approval`, and no failure alert is sent while it waits.

**Is a "Needs attention" email repeated?**

It is sent once when the connection breaks. The connection keeps its "Needs attention" status in Connections until someone clicks Reconnect, and each step that uses it fails with CONN-401 in the meantime.

## Troubleshooting questions

**An Admin says they never received a quota alert.**

Check that they were an Admin when the threshold was crossed, since only Admins receive quota alerts, and that the message isn't filtered as bulk mail. The usage dashboard shows the date each threshold was reached.

**Failure alerts stopped arriving after a team mailbox was changed.**

The old address is probably still in the recipients. Update it under Settings > Notifications or in the workflow's override, then send a test alert.

**An approver didn't get the approval email.**

Approvers must be users of the workspace, and a suspended user receives nothing. Check the approval step's approver list, and point the approver to the Approvals inbox in the meantime.

**The client's incident tool misses some failures.**

Compare the endpoint's delivery log with run history; see [Troubleshooting Webhook Deliveries](nimbus-troubleshooting-webhook-deliveries.md).

## Where to find more

- [Configuring Failure Notifications](nimbus-admin-failure-notifications.md) and [Troubleshooting Missing Notifications](nimbus-troubleshooting-notifications.md).
- [Usage Dashboard and Quota Alerts](nimbus-tier-usage-dashboard.md) and [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).
- [Adding Approval Steps to a Workflow](nimbus-admin-approval-steps.md).
- [Registering Webhook Endpoints](nimbus-admin-webhook-endpoints.md).
