---
id: nimbus-faq-workspace-and-account
title: Workspace and Account FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-17
owner: Customer Success Enablement
---

A workspace is the unit a Nimbus client works in: it holds the client's users, connections, workflows, run history and settings, and it carries one Plan Tier and one data region. This FAQ answers what CSMs are asked about workspaces themselves: naming, time zones, data regions, running more than one workspace, the Enterprise sandbox, and deleting a workspace.

Questions about what a given Plan Tier includes belong in [Plan Tiers and Entitlements](nimbus-plan-tiers.md). Commercial questions go to the client's account team, not to this Knowledge Base.

## General questions

**What identifies a workspace?**

Each workspace has a prefixed id such as `ws_7Kd2pQ`, shown under Settings > Workspace and returned by `GET /workspace`. Support tickets and SSO URLs use this id, so ask the client for it before escalating anything. The name shown in the console header is only a label and can be changed at any time.

**Can one client have several workspaces?**

Yes. Some clients keep separate workspaces per business unit or per legal entity. Each workspace is fully separate: its own users and seats, its own connections, its own Plan Tier and its own data region. Nothing is shared between them, so a person who works in two workspaces is invited to each, takes a seat in each, and switches between them from the workspace menu in the top-left corner of the console. Workflows don't move between workspaces automatically; see the region move steps below for the usual way to copy them.

**What is the sandbox workspace?**

Enterprise clients get one sandbox workspace alongside their main workspace. It is meant for trying out connectors, templates and risky changes without touching production. The sandbox isn't counted against the main workspace's limits. It is not the same thing as the Development environment inside a workspace, which Business and Enterprise clients use to stage a workflow before promoting it; see [Sandbox Workspace](nimbus-tier-sandbox-workspace.md) and [Development and Production Environments](nimbus-tier-environments.md).

## Setup questions

**Where are the workspace name, time zone and default recipients set?**

Under Settings > Workspace, by an Admin. The page holds the workspace name, the workspace time zone, the default notification recipients and, at the bottom, the Delete workspace button. The same values can be read through the API:

```http
GET /workspace HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "ws_7Kd2pQ",
  "name": "Fairhaven Logistics",
  "time_zone": "Europe/London",
  "data_region": "eu",
  "plan_tier": "business",
  "created_at": "2025-09-15T08:42:11Z"
}
```

**What does the workspace time zone affect?**

Schedule triggers: a cron expression is read in the workspace time zone unless the trigger has its own IANA time zone set. Run history and the console show times in the viewer's browser time zone, while the API always returns ISO 8601 timestamps in UTC.

### How do I move a workspace to another data region?

The data region is chosen when the workspace is created and can't be changed afterwards. Moving region means creating a new workspace in the target region and migrating the workflows into it:

1. Create the new workspace in the target region, as described in [Creating a Workspace](nimbus-admin-creating-a-workspace.md).
2. Invite the users again, with the same roles.
3. Recreate each connection. Saved credentials are never shown again, so the client needs the original keys, tokens or OAuth consent.
4. Copy the workflows, either by rebuilding them or by reading each one with `GET /workflows/{id}` in the old workspace and creating it with `POST /workflows` in the new one.
5. Point every caller of an inbound webhook trigger at the new trigger URL, because each trigger gets a new trigger token.
6. Deactivate the workflows in the old workspace, check a full day of runs in the new one, then delete the old workspace.

Run history doesn't move with the workflows; export what the client needs to keep before step 6.

## Limits and edge cases

**What can be changed after a workspace is created?**

| Setting | Changeable later | Notes |
|---|---|---|
| Workspace name | Yes | Settings > Workspace |
| Time zone | Yes | Applies to the next scheduled fire of every schedule without its own time zone |
| Data region | No | Create a new workspace and migrate |
| Plan Tier | Yes | Upgrades apply immediately; downgrades at the end of the current billing period |
| Workspace id | No | Fixed for the life of the workspace |

**Are there limits on downgrading?**

A downgrade takes effect at the end of the current billing period, and events in the audit log older than the new tier's retention are deleted when it does. A workspace in the APAC data region can't be downgraded below Enterprise. A downgrade from Enterprise stops SCIM sync, while users it provisioned keep their accounts.

**What happens when a workspace is deleted?**

Deletion is done by an Admin under Settings > Workspace > Delete workspace, after typing the workspace name to confirm. OmniCorp support can restore a deleted workspace for 14 days. After that, every workflow, run, connection and user in it is permanently deleted and can't be recovered.

## Troubleshooting questions

**Scheduled runs fire an hour early or late since the clocks changed.**

The schedule is following a different time zone from the one the client expects. Check whether the trigger has its own IANA time zone set; if it doesn't, it uses the workspace time zone from Settings > Workspace. A zone such as `Europe/Berlin` follows daylight saving, while `UTC` never does.

**The client can't find the Delete workspace button.**

Only Admins see it. A Builder or Viewer sees Settings > Workspace as read-only.

**A workspace was deleted by mistake.**

Ask the client's CSM to raise a restore request with OmniCorp support straight away, quoting the workspace id. Restores are possible only within 14 days of deletion. Active workflows come back deactivated, so an Admin reactivates them after checking their connections.

**The Downgrade option is greyed out.**

Check the data region on Settings > Workspace. A workspace created in the APAC region can't be downgraded below Enterprise; the only way to a lower tier is a new workspace in another region.

## Where to find more

- [Managing Workspace Settings](nimbus-admin-workspace-settings.md) for every field on Settings > Workspace.
- [Deleting a Workspace](nimbus-admin-deleting-a-workspace.md) and [Data Retention and Deletion](nimbus-security-data-deletion.md).
- [Data Residency](nimbus-security-data-residency.md) for where each region's data is stored.
- [Workspace API](nimbus-api-workspace.md) for `GET /workspace`, `/workspace/entitlements` and `/workspace/usage`.
