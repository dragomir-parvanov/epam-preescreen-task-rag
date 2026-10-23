---
id: nimbus-connector-asana
title: Asana Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-08-18
owner: Integrations Team
---

The Asana connector brings Asana projects into Nimbus workflows. A run can start when a task is added to a project or completed, and workflow steps can create tasks, add subtasks, set custom field values and post comments. Clients use it to turn form submissions or support escalations into Asana tasks, and to update other systems when the task is done.

The connection is authorised with OAuth 2.0 by an Asana user and acts as that user: tasks and comments it creates show that user as their author, and it sees only the workspaces and projects that user can see.

## Prerequisites

- **An Asana user** who is a full member of the Asana organisation or workspace. Guest accounts can be used only for projects that have been explicitly shared with them, and can't see custom fields from the organisation's library. Many clients create a dedicated user, such as "Nimbus Automation", so comments read clearly and nothing breaks when a person leaves.
- **Project membership.** The user must be a member of every project the workflows use, with **Editor** access to create or change tasks; **Commenter** access is enough for the comment action only.
- **Custom fields** already added to the project if a workflow sets them. The connector sets values; it doesn't add fields to projects.
- **A Builder or Admin role** in Nimbus. The connector is available on every Plan Tier.

## Creating the connection

1. In Nimbus, go to **Connections**, click **New connection** and select **Asana**.
2. Click **Connect to Asana** and sign in to Asana as the chosen user.
3. On Asana's authorisation page, check the app name reads **OmniCorp Nimbus** and click **Allow**.
4. Choose the default **Workspace** for the connection. Steps can override it, but most clients have one organisation.
5. Click **Test connection**. Nimbus shows the user's name and the number of projects it can see.
6. Click **Save**.

The user can revoke access at any time in Asana under **Settings > Apps > Deauthorize**; the connection then needs reconnecting.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New task in project | Push trigger | Starts a run when a task is added to the chosen project, including tasks moved in from another project |
| Task completed | Push trigger | Starts a run when a task in the project is marked complete |
| Create task | Action | Creates a task in a project and optional section, with assignee, due date, notes and custom fields |
| Add subtask | Action | Creates a subtask under an existing task |
| Update custom field | Action | Sets one or more custom field values on a task |
| Add comment | Action | Posts a comment on a task's activity feed |

Subtasks don't belong to their parent's project unless they're added to it explicitly, so they don't start the New task in project trigger. Marking a completed task incomplete doesn't start a run, and completing it again does.

## Field mapping

Asana identifies everything by a global ID, the `gid`: a numeric string such as `"1205550001234567"`. Workspaces, projects, sections, tasks, users, custom fields and the options of a dropdown field all have one. Names aren't accepted where a gid is expected.

Custom fields are set by field gid, and dropdown (enum) fields take the gid of the enum option, not its label. Sending the label "High" for a priority field makes Asana reject the step with "enum_value: Not a valid enum option". Text fields take a string, number fields a number, and date fields an ISO 8601 date.

```json
{
  "task": "{{trigger.body.task.gid}}",
  "custom_fields": {
    "1205550001112223": "1205550001112229",
    "1205550001112230": "{{default(steps.estimate.output.hours, 0)}}",
    "1205550001112241": "{{lower(steps.lookup_account.output.tier)}}"
  }
}
```

In this example `1205550001112223` is the Priority field and `1205550001112229` its "High" option. To set a dropdown from data, map labels to option gids in a transform step first. Comments accept plain text; Add comment's `text` can use any expression, such as `Escalated by {{trigger.body.requester}} at {{now()}}`.

### Finding workspace and project gids

The builder's pickers fill in gids for projects, sections and users. When you need one by hand, open the project in Asana: the project gid is the first long number in the browser's address, as in `https://app.asana.com/0/1205550009876543/list`. A task's gid is the last number when the task is open in the side pane. The workspace gid is shown on the connection's page in Nimbus after **Test connection**.

## Limits and behaviour

- **Delivery.** Asana pushes events for the project to Nimbus, usually within a minute, sometimes grouping several changes into one delivery; Nimbus still starts one run per matching task.
- **Webhook lifetime.** Nimbus registers an Asana webhook on the project when the workflow is activated. If the connected user loses access to the project, Asana deletes the webhook and the trigger stops; reactivating the workflow after restoring access registers it again.
- **Attachments.** Files passed between steps and attached to tasks can be up to 100 MB.
- **Paging.** Steps that look up tasks read them 100 at a time.
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Create task isn't idempotent: if Asana created the task but the response was lost, a retry creates a second one. Set retries to 0 on that step if a duplicate is worse than a failed run.

## Troubleshooting

| Code | Asana-side cause | Fix |
|---|---|---|
| CONN-401 | The user deauthorised Nimbus, was removed from the organisation, or changed their sign-in method | Click **Reconnect** and sign in as an active user. |
| CONN-403 | The user isn't a member of the project, or has Commenter access where Editor is needed | Add the user to the project with Editor access. |
| CONN-404 | A gid doesn't exist or belongs to another workspace; the task was deleted | Re-pick the project or field in the builder. |
| CONN-429 | Asana throttled the connection | Nimbus backs off and retries automatically. |
| WF-400 | The task name or a required field resolved to empty | Add `default()` or a condition before the step. |

For issue tracking in Jira instead, see [Jira Cloud Connector](nimbus-connector-jira-cloud.md).
