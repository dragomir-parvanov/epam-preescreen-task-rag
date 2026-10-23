---
id: nimbus-tier-sandbox-workspace
title: Sandbox Workspace
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-04-13
owner: Product Operations
---

An Enterprise workspace can have one sandbox workspace alongside it: a separate Nimbus workspace for trying out changes, testing new connectors and training Builders without touching production workflows or using up production limits. The sandbox has its own workflows, connections, secrets and run history, and it is linked to the production workspace it was created from.

Clients most often ask for a sandbox when a change is too big for the Development environment inside one workspace, for example when they want to test a new Salesforce sandbox org connection, rehearse a change to role mapping, or let a systems integrator build workflows away from live data.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Sandbox workspace | No | No | Yes, one per production workspace |
| Counted against production limits | – | – | No |
| Development and Production environments | No | Yes | Yes |

Business clients who want somewhere to try changes have the Development environment instead, which is described in [Development and Production Environments](nimbus-tier-environments.md). Environments separate versions of a workflow; a sandbox separates everything, including connections and users.

## How it works

The sandbox is a full Nimbus workspace with its own id (`ws_...`) and its own console URL. Its name is the production workspace's name followed by "(Sandbox)", and a yellow banner across the top of the console shows that you are in the sandbox. It is created in the same data region as the production workspace, and that can't be changed, because a workspace's region is fixed when the workspace is created.

What the sandbox shares with production, and what it doesn't:

| Item | In the sandbox |
|---|---|
| Plan Tier features | The same Enterprise features as production |
| Workflow runs, seats, active connectors, secrets | Counted separately; never counted against production |
| Users | Invited separately; sandbox users don't take production seats |
| Single sign-on | Configured separately, with its own ACS URL and entity ID |
| Workflows | Copied in on demand; never synced automatically |
| Connections and secrets | Not copied; created again in the sandbox |
| Audit log | Its own audit log |

Workflows move into the sandbox by copying. A copied workflow arrives as an inactive draft with its steps, mappings, schedule and folder, but with every connection step unbound, because connection credentials are never shown again after saving and so can't be carried across. Point each step at a sandbox connection, ideally one to the third-party app's own test environment, such as a Salesforce sandbox org. Expressions such as `{{secrets.ERP_TOKEN}}` are copied as written, so create secrets with the same names in the sandbox.

Copying works in both directions. Once a change has been proven in the sandbox, a Builder copies the workflow back to production, where it also lands as a draft. Publishing it there creates a new version in the production workflow's history.

## Turning it on

An Admin of the production workspace creates the sandbox. It takes a minute or two.

1. In the production workspace, go to **Settings > Workspace > Sandbox** and click **Create sandbox**.
2. Confirm the name. The data region is shown but can't be changed.
3. When the status shows **Ready**, click **Open sandbox**. The Admin who created it is its first Admin.
4. Invite the Builders and Admins who will work in the sandbox, or configure single sign-on for it.
5. Create the connections and secrets the copied workflows will need.
6. In production, open a workflow, choose **⋯ > Copy to sandbox**, and pick a folder in the sandbox.

An Admin can confirm the sandbox and its link to production with the workspace endpoint, called with an API key from the production workspace:

```http
GET /workspace HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "id": "ws_4TR9QK2L",
  "name": "Acme Operations",
  "plan_tier": "enterprise",
  "data_region": "eu",
  "sandbox": {
    "workspace_id": "ws_9MB3XC7E",
    "name": "Acme Operations (Sandbox)",
    "status": "ready",
    "created_at": "2026-03-02T10:15:44Z"
  }
}
```

API keys are per workspace, so automation that should run against the sandbox needs a key created in the sandbox itself.

## Limits

| Limit | Value |
|---|---|
| Sandboxes per production workspace | 1 |
| Workflow runs per month in the sandbox | Unlimited, not counted against production |
| Concurrent runs in the sandbox | 100, separate from production |
| Data region | Same as production; can't be changed |
| Workflows copied per action | 1 (copy each workflow separately) |

Because the sandbox doesn't count against production limits, clients sometimes ask whether they can run production work there. They shouldn't: the sandbox is meant for testing, and it is removed if the client leaves Enterprise, as described below. Deleting the sandbox and creating a new one is allowed, for example to start again from a clean slate; the new sandbox gets a new workspace id and starts empty.

## When the Plan Tier changes

**Upgrade to Enterprise.** The upgrade takes effect immediately, and **Settings > Workspace > Sandbox** becomes available as soon as it is applied. Nothing is created automatically; an Admin creates the sandbox when the client is ready.

**Downgrade below Enterprise.** A downgrade takes effect at the end of the current billing period, and at that moment the sandbox is removed together with its workflows, connections, secrets, run history and users. The production workspace isn't affected. Removal follows the same path as [Deleting a Workspace](nimbus-admin-deleting-a-workspace.md), so OmniCorp support can restore the sandbox for 14 days, but a restore only helps if the client returns to Enterprise within that window. Before the downgrade date, ask the client to:

1. Copy back to production any workflow that only exists in the sandbox.
2. Export any sandbox run history they want to keep.
3. Tell sandbox users that their sandbox access ends on the downgrade date.

A workspace in the APAC data region can't be downgraded below Enterprise, so a sandbox there stays in place for as long as its production workspace is on Enterprise.
