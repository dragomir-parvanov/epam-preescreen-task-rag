---
id: nimbus-admin-workspace-settings
title: Managing Workspace Settings
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-11-17
owner: Workspace Administration Team
---

The **Settings > Workspace** page holds the handful of settings that apply to an OmniCorp Nimbus workspace as a whole: its name, the time zone that schedules run in, and who receives notifications when nobody more specific has been named. It also shows, read-only, the facts about the workspace that were fixed when it was created, such as its id and data region.

Clients mostly come to this page after a reorganisation (a new name), after moving operations to another office (a new time zone), or when failure alerts are reaching the wrong people. The same page holds **Delete workspace**, which is covered separately in [Deleting a Workspace](nimbus-admin-deleting-a-workspace.md).

## Before you begin

- **Role:** Admins can edit the page. Builders and Viewers can open it and read the values, but every field is disabled for them.
- **Plan Tier:** all of these settings exist on every Plan Tier.
- **Time zone changes:** list the scheduled workflows before you change the time zone. On the **Workflows** page, filter by **Trigger: Schedule** and note which ones have no time zone of their own; those are the ones that will move.
- **Notification recipients:** have the addresses ready. A shared team mailbox is better than one person's address, because it survives staff changes.

## How it works

The page is split into an editable part and a read-only part.

| Setting | Editable | What it affects |
|---|---|---|
| Workspace name | Yes | The name in the console header, in invitation emails and in notification subjects. Up to 60 characters. |
| Time zone | Yes | Every schedule trigger that doesn't set its own IANA time zone, and how times are displayed in the console by default. |
| Default notification recipients | Yes | Who receives failure alerts for workflows with no recipients of their own. Up to 10 email addresses. |
| Workspace ID | No | The `ws_` id used in the API, SAML URLs and support requests. |
| Data region | No | Where workflows, run history, audit logs and user data are stored. |
| Plan Tier | No | Shown for reference; it is changed on **Settings > Plan**. |
| Created | No | The date the workspace was provisioned. |

**Time zone.** Schedules are cron expressions evaluated in a time zone, and a schedule that doesn't name one uses the workspace's. Changing the workspace time zone therefore shifts those schedules: a workflow set to `0 6 * * *` that ran at 06:00 in `Europe/London` runs at 06:00 in `America/New_York` once the change is saved, five hours later in absolute terms. The new time zone applies from each schedule's next occurrence; runs already queued are not moved. Schedules with their own time zone don't change at all. Timestamps in the API and in webhook payloads are always UTC and are not affected. See [Scheduling Workflows](nimbus-admin-scheduling-workflows.md) for how schedules use time zones.

**Default notification recipients.** Failure notifications go first to whatever recipients a workflow or the **Settings > Notifications** page names. The default recipients on this page are the fallback, and they also receive workspace-level notices such as connections that need attention. Run-quota alert emails at 80% and 100% always go to the Admins, whatever this list contains. For the full routing, see [Configuring Failure Notifications](nimbus-admin-failure-notifications.md).

**Data region.** The region is chosen when the workspace is created and can't be changed afterwards, so it appears here with a lock icon and no edit control. A client that needs a different region needs a new workspace and a migration of its workflows; which tiers offer which regions is listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Step-by-step

1. Open **Settings > Workspace**.
2. Under **General**, edit **Workspace name** if needed.
3. Under **Time zone**, start typing a city or IANA name (for example `Europe/Berlin` or `Asia/Singapore`) and pick it from the list. The page shows how many scheduled workflows use the workspace time zone and will move.
4. Under **Default notification recipients**, add or remove addresses. Press Enter after each one.
5. Click **Save changes**. If the time zone changed, confirm the dialog that lists the affected schedules.

The API can read these settings but not change them; edits are made in the console. `GET /workspace` is useful for checking a client's configuration from a script or a support tool:

```http
GET /workspace HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "id": "ws_4821",
  "name": "Northwind Finance Automation",
  "time_zone": "Europe/Berlin",
  "default_notification_recipients": ["nimbus-alerts@northwind.example"],
  "data_region": "eu",
  "plan_tier": "business",
  "created_at": "2025-09-15T08:02:11Z"
}
```

## Verifying the change

Reload **Settings > Workspace** and check the saved values; the console header shows the new name straight away. For a time zone change, open one of the affected scheduled workflows: the trigger panel lists the next five run times in the new zone. `GET /workspace` returns the new `name`, `time_zone` and `default_notification_recipients`. Each change is recorded in **Settings > Audit log** as a `workspace.updated` event that names the fields changed and their old and new values.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Fields are greyed out | You are signed in as a Builder or Viewer. | Ask an Admin, or have an Admin change your role. |
| Scheduled runs started an hour or several hours off after a change | Those schedules relied on the workspace time zone. | Set the old zone back, or give each workflow's schedule its own IANA time zone. |
| A time zone such as "CET" isn't in the list | Only IANA names are accepted. | Pick the city entry, for example `Europe/Paris`. |
| Alerts still reach a former employee | A workflow or **Settings > Notifications** names them directly, so the default list isn't used. | Update the recipients there. |
| No edit control on **Data region** | The region is permanent. | Plan a new workspace in the target region with the client and migrate the workflows. |
| "Up to 10 recipients" when saving | The list is full. | Replace individual addresses with a shared mailbox. |
