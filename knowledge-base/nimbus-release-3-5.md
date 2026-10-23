---
id: nimbus-release-3-5
title: Nimbus 3.5 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2026-02-02
owner: Release Management
---

Nimbus 3.5.0 was released on 2026-02-02 for every v3 workspace. It gives Admins a usage dashboard that shows how much of the Plan Tier's allowances a workspace is using, a matching `GET /workspace/usage` endpoint, and quota alert emails at 80% and 100% of the monthly workflow-run quota.

Until this release, the first sign that a workspace had used its monthly runs was usually a WF-300 failure in run history. 3.5 is aimed at making that visible well in advance.

## Highlights

The new **Settings > Usage** page shows workflow runs this month, seats in use, active connectors and stored secrets on one screen, on every Plan Tier. The same figures are available from the API for clients that feed them into their own monitoring. Admins are now emailed when the workspace reaches 80% and again at 100% of its monthly run quota.

## New features

### Usage dashboard

**Settings > Usage** is visible to Admins on Starter, Business and Enterprise workspaces. Each meter shows the current figure against the Plan Tier's allowance, as listed under **Settings > Plan**:

| Meter | What is counted | Resets |
|---|---|---|
| Workflow runs | Runs started since the 1st of the month (UTC); test runs in the builder are excluded | 1st of each month, 00:00 UTC |
| Seats | Active users of any role; suspended users and pending invitations are excluded | Not periodic |
| Active connectors | Connectors with at least one connection used by an active workflow | Not periodic |
| Secrets | Secrets stored in the secrets vault | Not periodic |

Below the meters, a daily chart shows runs per day for the current and previous month, split by trigger type (schedule, connector event, inbound webhook, manual), and a **Top workflows** table lists the 10 workflows that started the most runs this month. Selecting a workflow opens its run history filtered to the current month, which is usually the fastest way to find a schedule that fires more often than intended. On Enterprise workspaces, where runs are unlimited, the run meter shows the count without a quota bar. More on reading the page is in [Usage Dashboard and Quota Alerts](nimbus-tier-usage-dashboard.md).

### Usage API and quota alerts

`GET /workspace/usage` returns the same counts as the dashboard; see [Workspace API](nimbus-api-workspace.md). The response reports what is used, and `GET /workspace/entitlements` reports the allowances, so a monitoring script normally calls both.

Quota alert emails go to every Admin in the workspace at two points:

1. When runs started this month reach 80% of the quota, with the date the quota resets and a link to **Settings > Usage**.
2. When they reach 100%, stating that scheduled, event-triggered and manual runs are now rejected with WF-300 until the quota resets on the 1st of the month (UTC) or the Plan Tier is upgraded.

Each alert is sent once per month. Quota alerts are separate from the failure alerts configured under **Settings > Notifications**: they can't be switched off and always go to Admins, while failure alerts for runs rejected with WF-300 follow the workspace's notification settings and recipients; see [Configuring Failure Notifications](nimbus-admin-failure-notifications.md). A client who wants Builders to hear about the quota as well can add them as notification recipients for WF-300, or promote one of them to Admin. An upgrade takes effect immediately, so after an upgrade from Starter to Business, runs are accepted again straight away. See [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).

## Improvements

- The console shows a banner to Admins and Builders while the workspace is at or above 80% of its run quota.
- Run history can be filtered by trigger type.
- WF-300 failures in run history link to **Settings > Usage**.
- `GET /runs` accepts `from` and `to` filters on the run start time.
- The **Connections** page marks which connections count towards active connectors.
- **Settings > Plan** links each allowance to its meter on the new page, so Admins can move between the limit and the current figure.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-4893 | The run quota counter included runs rejected with WF-300, so it could show more than 100% of the quota. |
| NIM-4897 | Secrets with a digit immediately after an underscore could not be referenced in expressions. |
| NIM-4902 | The Snowflake **Insert rows** action failed on `VARIANT` columns when the value was an empty object. |
| NIM-4906 | A suspended workflow owner still received failure notifications for that workflow. |
| NIM-4911 | `GET /workspace/entitlements` reported active connectors including connectors used only by inactive workflows. |
| NIM-4915 | Approval request emails were sent from a no-reply address that some mail filters rejected. |

## Deprecations and breaking changes

Nothing breaks in 3.5, and quota enforcement is unchanged: the same runs count, the quota resets at the same time, and WF-300 means the same thing. The only behaviour visible to existing integrations is the corrected run counter from NIM-4893, which can make the figure reported for the current month slightly lower than before. Clients whose mail systems filter automated messages should make sure messages from the Nimbus notification address reach their Admins.

## Upgrade notes

1. Check that the people who should receive quota alerts are Admins; Builders and Viewers don't receive them.
2. Open **Settings > Usage** and compare the run meter with the client's expectations for the month.
3. If the client monitors usage centrally, add a scheduled call to `GET /workspace/usage`. For example:

```bash
curl -s https://api.nimbus.omnicorp.example/workspace/usage \
  -H "Authorization: Bearer <api-key>"
```

```json
{
  "period_start": "2026-02-01T00:00:00Z",
  "period_end": "2026-03-01T00:00:00Z",
  "workflow_runs": {"used": 81240, "percent_of_quota": 81.2},
  "seats": {"used": 118},
  "active_connectors": {"used": 31},
  "secrets": {"used": 64},
  "updated_at": "2026-02-24T08:15:00Z"
}
```

4. If runs are close to the quota mid-month, review the **Top workflows** table before suggesting an upgrade; a misconfigured schedule is the most common cause. [Troubleshooting Run Quota Errors](nimbus-troubleshooting-run-quota.md) covers the checks.

`percent_of_quota` is null on Enterprise workspaces. Counts are refreshed every few minutes, so a figure can lag a run that has just started.
