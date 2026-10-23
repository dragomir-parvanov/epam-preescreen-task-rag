---
id: nimbus-admin-failure-notifications
title: Configuring Failure Notifications
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-05-04
owner: Workspace Administration Team
---

Failure notifications tell people when a workflow run fails, so a broken integration is noticed in minutes rather than when a client's sales team finds missing records. They are configured once for the workspace under **Settings > Notifications** and can be overridden on any single workflow.

Quota alert emails, which warn when the workspace nears its monthly workflow runs, are separate: they always go to Admins and aren't configured here. Both are described below.

## Before you begin

- **Role:** Admin for the workspace defaults under **Settings > Notifications**. Builders and Admins can set a per-workflow override in the builder.
- **Plan Tier:** any. Failure notifications are available on Starter, Business and Enterprise.
- **Chat channels:** to post to Slack or Microsoft Teams, the workspace needs a working connection to that app. Set it up first with the [Slack Connector](nimbus-connector-slack.md) or [Microsoft Teams Connector](nimbus-connector-microsoft-teams.md) Article. A private Slack channel only works if the Nimbus app has been invited to it.
- **Default recipients:** the workspace's default notification recipients are set under **Settings > Workspace**; see [Managing Workspace Settings](nimbus-admin-workspace-settings.md). They are pre-filled as the address list when you first open **Settings > Notifications**.

## How it works

A notification is sent when a run ends with the status `failed` or `timed_out`. Runs that are `cancelled` don't notify, because someone cancelled them on purpose, and runs that wait as `queued` with WF-310 don't notify either, because that is a notice rather than a failure. A failed step that later succeeds on retry doesn't notify; only the run's final status counts.

Each rule sends to any combination of these destinations:

| Destination | Who receives it | Notes |
|---|---|---|
| Workflow owner | The Builder or Admin who owns the workflow | If the owner is suspended or deleted, the alert goes to the workspace Admins until ownership is transferred. |
| Email addresses | Up to 20 addresses | They don't need to be Nimbus users, so a client's on-call mailbox works. |
| Slack channel | One channel per rule | Posted by the Nimbus app through the selected connection. |
| Microsoft Teams channel | One channel per rule | Posted through the selected connection. |

Every alert carries the workflow name, environment, run id, the failed step's key and its error code (for example CONN-401 or WF-400), and a link to the run.

**Delivery mode** decides how often alerts go out:

- **Immediate** sends one alert per failed run, within a minute of the failure.
- **Hourly digest** collects all failures in the hour and sends one summary at the top of the hour, grouped by workflow with a count and the most recent error code. Use it for high-volume workflows where a dependency outage would otherwise send hundreds of alerts.

A **per-workflow override** replaces the workspace defaults for that workflow entirely: destinations, delivery mode, or both. It can also mute a workflow, which is useful for a Development copy that fails while being built. Overrides follow the workflow through promotion, so a muted Development override is copied to Production too; check it after [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).

### Quota alerts

When the workspace has used 80% and then 100% of its monthly workflow runs, every Admin receives an email. These quota alerts can't be redirected or turned off under **Settings > Notifications**. At 100%, new runs are rejected with WF-300 until the quota resets on the 1st of the month (UTC) or the Plan Tier is upgraded; current usage is on **Settings > Usage**.

## Step-by-step

To set the workspace defaults:

1. Go to **Settings > Notifications**.
2. Under **Run failures**, tick **Notify the workflow owner** if owners should hear about their own workflows.
3. Under **Email addresses**, add or remove addresses, one per line.
4. Under **Chat**, choose **Slack** or **Microsoft Teams**, pick the connection and the channel. Add a second chat row if both apps are used.
5. Choose **Immediate** or **Hourly digest**.
6. Click **Save**.

To override the defaults on one workflow:

1. Open the workflow in **Workflows** and click **Settings** in the builder toolbar.
2. Open the **Notifications** tab and switch **Use workspace defaults** off.
3. Set the destinations and delivery mode for this workflow, or tick **Mute failure notifications**.
4. Click **Save**. The override applies from the next run; it doesn't need a publish.

There is no API for notification rules. Clients who want failures pushed into their own monitoring can register a webhook endpoint for the `workflow.run.failed` event instead; the request below does that, and [Registering Webhook Endpoints](nimbus-admin-webhook-endpoints.md) covers the rest:

```http
POST /webhooks/endpoints HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "url": "https://alerts.client.example/nimbus",
  "events": ["workflow.run.failed"],
  "description": "Run failures to on-call"
}
```

## Verifying the change

The quickest test is a run that fails on purpose. In a test workflow, add an HTTP Request step that calls a URL returning 404, set its retries to 0 and click **Run now**. Test runs in the builder still send failure notifications, though they don't count towards the run quota.

Then confirm:

1. Each address received the email, from `notifications@nimbus.omnicorp.example`. Ask the client to check spam folders and mail rules if not.
2. The Slack or Teams channel shows the alert with a working **Open run** link.
3. With **Hourly digest**, nothing arrives until the top of the next hour, then one summary.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| No alert for a run that failed | The workflow has an override that mutes it or sends elsewhere | Open the workflow's **Settings > Notifications** tab and check **Use workspace defaults**. |
| No alert for a timed-out run in a digest | The digest hasn't been sent yet | Wait for the top of the hour. |
| Slack alerts stopped arriving | The Slack connection shows "Needs attention" (CONN-401) | Click **Reconnect** on the connection. |
| Teams alerts fail with CONN-403 | The connected account can't post in that channel | Add the account to the team, or pick another channel. |
| An Admin wants to stop quota emails | Quota alerts aren't configurable | They go to all Admins; change the user's role if they shouldn't be an Admin. |
| Alerts go to a former owner's manager | The owner was removed and ownership wasn't transferred | Transfer ownership as in [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md). |
