---
id: nimbus-tier-workflow-templates
title: Workflow Templates
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-09-22
owner: Product Operations
---

Workflow templates give Builders a ready-made starting point instead of an empty canvas. The template gallery holds OmniCorp's own templates for common integrations, such as creating a Jira Cloud issue from a Zendesk ticket or posting new HubSpot deals to Slack, and each workspace can add its own templates built from workflows it already runs. Templates are included on every Plan Tier.

Installing a template never starts anything running. It creates a draft workflow that a Builder connects, adjusts and publishes like any other. This Article covers the gallery, how templates behave on each tier, and how to save a workflow as a workspace template.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Template gallery | Yes | Yes | Yes |
| Install OmniCorp templates | Yes, except marked templates | Yes | Yes |
| Save a workflow as a workspace template | Yes | Yes | Yes |
| Templates with approval steps | Marked, can't be installed | Yes | Yes |
| Templates that use environments | Marked, can't be installed | Yes | Yes |

The gallery itself looks the same on every tier. What changes is which templates can be installed: a template that relies on a feature the workspace's tier doesn't include carries a **Requires Business or Enterprise** badge, and its **Use template** button is disabled.

## How it works

The gallery opens from **Workflows > New workflow > From template**. It has two tabs:

- **OmniCorp templates**, maintained by OmniCorp and grouped by category (Sales, Support, HR, Finance, IT, Data). Each card lists the connectors the template uses and the trigger it starts from.
- **Workspace templates**, the templates that Builders and Admins in this workspace have saved. Only users of this workspace see them.

Clicking **Use template** creates a new draft workflow in a folder of the Builder's choice, owned by that Builder. The draft has the template's trigger, steps, mappings and conditions, but no connections: every connector step shows **Choose connection**, and the Builder picks an existing connection or creates one. Because the draft is unpublished, it has no versions yet and doesn't run. It also doesn't count towards active connectors until it is published and active, so trying a template on Starter doesn't use up one of the five connector slots.

Templates carry expressions as written. A template step that uses `{{secrets.SLACK_SIGNING_KEY}}` or `{{env.ERP_BASE_URL}}` expects a secret or environment variable with that name in the workspace; the draft shows a warning on each step whose secret is missing, and running it fails with WF-400 until the secret exists.

### Saving a workflow as a template

Any published workflow can be saved as a workspace template. Nimbus copies the latest published version's definition and strips everything workspace-specific: connections are unbound, schedule start dates are cleared and the workflow's owner isn't recorded. Secret values are never part of a template; only the `{{secrets.<NAME>}}` references remain.

## Turning it on

The gallery is available to every Builder and Admin without any setup. To install a template:

1. Go to **Workflows**, click **New workflow** and choose **From template**.
2. Filter by connector or category, open a template card and read its **What it does** panel.
3. Click **Use template**, name the workflow and pick a folder.
4. In the builder, choose a connection for each step marked **Choose connection**.
5. Run the draft with **Run now** to test it; test runs in the builder don't count towards the monthly quota.
6. Click **Publish** to create version 1, then activate the workflow.

To save a workflow as a workspace template, open it and choose **⋯ > Save as template**, then give it a name, a category and a short description.

Workflows can also be created from a template through the API, which suits clients who provision the same workflow in several workspaces. Pass the template's slug in the create request:

```http
POST /workflows HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 6b1e0a4c-zendesk-jira-eu

{
  "name": "Escalate urgent Zendesk tickets to Jira",
  "template": "zendesk-ticket-to-jira-issue",
  "folder_id": "fld_3NQ7WD2K"
}
```

The response is the new workflow with `"status": "draft"`, and each connector step has `"connection_id": null` until a connection is chosen with `PATCH /workflows/{id}` or in the builder.

## Limits

| Limit | Value |
|---|---|
| Workspace templates per workspace | 100 |
| Template description | 1,000 characters |
| Workflows created from one template | No limit |
| Who can save a workspace template | Builders and Admins |
| Who can delete a workspace template | The Builder who saved it, or any Admin |

Templates follow the same limits as any workflow once installed: the monthly run quota, the active connector limit, the minimum schedule interval and the concurrent-run limit of the workspace's tier. A template whose schedule is more frequent than the tier allows is installed with its schedule set to the tier's minimum interval, and the builder shows a notice explaining the change. Deleting a workspace template doesn't affect workflows already created from it. The same applies when OmniCorp revises one of its own templates, for example to use a newer connector action: the gallery shows the revised template from then on, and workflows installed from the earlier revision keep their own definition and version history.

## When the Plan Tier changes

**Upgrade.** An upgrade takes effect immediately. Badges disappear from templates the new tier supports, so a client moving from Starter to Business can install templates with approval steps straight away. Templates that were already installed don't change.

**Downgrade.** A downgrade takes effect at the end of the current billing period. Workspace templates are kept in full, including those that contain approval steps or rely on environments; from that point they show the badge and can't be installed until the workspace is upgraded again. Workflows already created from templates are treated like any other workflow on the new tier; for workflows with approval steps, see [Approval Steps](nimbus-tier-approval-steps.md). Saving new workspace templates remains possible on every tier.
