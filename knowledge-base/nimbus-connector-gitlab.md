---
id: nimbus-connector-gitlab
title: GitLab Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-02
owner: Integrations Team
---

The GitLab connector, added in release 3.1.0, connects workflows to projects on GitLab.com or on a self-managed GitLab instance. Workflows can start on merge request and pipeline events, and can create issues, comment on merge requests and trigger pipelines. Release engineering teams use it to announce merges, open follow-up issues when a pipeline fails, or start a deployment pipeline after an approval step.

The connection authenticates with a GitLab access token: a personal, group or project access token with the `api` scope. Tokens in GitLab carry an expiry date, so this Article also explains what happens when the token runs out.

## Prerequisites

Choose the token type by how widely the connection should reach:

| Token type | Reaches | Created under |
|---|---|---|
| Project access token | One project | Project **Settings > Access tokens** |
| Group access token | Every project in a group and its subgroups | Group **Settings > Access tokens** |
| Personal access token | Everything the user can access | User **Preferences > Access tokens** |

Project and group access tokens are tied to a bot user, not a person, so they keep working when staff change; prefer them over personal tokens. Whatever the type:

- The token needs the `api` scope. `read_api` is not enough, because triggers register webhooks and actions write data.
- The token's role must be **Maintainer** or higher on each project used by a trigger, because registering a project webhook requires it. Actions alone work with **Developer**, except that triggering a pipeline on a protected branch needs whatever role the branch protection allows to merge.
- A self-managed instance must be reachable over HTTPS from Nimbus, or, on the Enterprise tier, through the private connector agent; and it must be able to send webhooks to Nimbus over HTTPS.
- A Builder or Admin role in Nimbus. The connector is available on every Plan Tier.

## Creating the connection

1. In GitLab, create the token with the `api` scope, the role chosen above and an expiry date, and copy it; GitLab shows it only once.
2. In Nimbus, open **Connections > New connection** and choose **GitLab**.
3. Enter the **GitLab URL**: `https://gitlab.com` for GitLab.com, or the instance's base URL, such as `https://gitlab.acme.example`, for self-managed. Use the base URL only, without any API path.
4. Paste the token into **Access token**.
5. For a self-managed instance on a private network, set **Network** to **Private agent** and choose the agent.
6. Click **Test connection**. Nimbus shows the token's owner, its scopes and its expiry date.
7. Click **Save**. The token is encrypted and never shown again.

## Triggers and actions

| Name | Type | Details |
|---|---|---|
| Merge request event | Push trigger | Project; actions `open`, `update`, `merge`, `close`, `approved`; optional target branch |
| Pipeline event | Push trigger | Project; statuses `success`, `failed`, `canceled`; optional ref |
| Create issue | Action | Title, description, labels, assignee, due date, confidential |
| Comment on merge request | Action | Adds a note to a merge request |
| Trigger pipeline | Action | Ref and CI/CD variables; returns the pipeline ID and web URL |

Activating a workflow registers a webhook on the chosen project, named `OmniCorp Nimbus (<workflow-id>)`; deactivating it removes the webhook. Don't edit or delete these hooks in GitLab, or the trigger stops receiving events.

## Field mapping

Projects can be given as a numeric ID or as a full path (`platform/billing-service`). Merge requests have two numbers: a global `id` and a project-scoped `iid`, which is the `!42` users see. Comment on merge request needs the `iid`, so map `{{trigger.body.object_attributes.iid}}`, not `id`.

A workflow that waits for a change-board approval and then deploys could configure its Trigger pipeline step like this:

```json
{
  "project": "platform/billing-service",
  "ref": "{{default(trigger.body.object_attributes.target_branch, 'main')}}",
  "variables": [
    {"key": "DEPLOY_ENV", "value": "{{env.DEPLOY_TARGET}}"},
    {"key": "APPROVED_BY", "value": "{{lower(steps.change_board.output.decided_by)}}"},
    {"key": "CHANGE_REF", "value": "{{trigger.body.object_attributes.iid}}"}
  ]
}
```

Variables passed this way override project-level CI/CD variables with the same key, subject to the project's pipeline-variable settings; if the project restricts who may override variables, the token's role must be allowed to.

## Limits and behaviour

GitLab pushes each event to Nimbus as it happens, and every event starts one run. A pipeline that moves from `running` to `failed` produces one event for the final status; intermediate statuses are ignored by the trigger. Merge request descriptions and notes are passed through as Markdown text. Files passed between steps, such as a job artefact downloaded by an HTTP Request step, can be up to 100 MB. Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes; Trigger pipeline starts a new pipeline on every retry, so set its retries to 0 if duplicate deployments matter.

### Token expiry

GitLab access tokens expire at midnight UTC on their expiry date, and GitLab.com doesn't allow tokens without one. Nimbus reads the expiry date when the connection is saved and shows it on the connection's page. When the token expires or is revoked, steps that use it fail with CONN-401, the connection shows "Needs attention", and the `connector.disconnected` webhook event is sent. Webhooks already registered keep delivering events, but the actions in those runs fail until the token is replaced.

To replace the token, create a new one in GitLab, open the connection in Nimbus, click **Reconnect** and paste it. Doing this a week or two before the expiry date avoids failed runs; the triggers and their webhooks are kept.

## Troubleshooting

| Code | Cause | Fix |
|---|---|---|
| CONN-401 | Token expired, revoked, or its bot user was removed | Create a new token and click **Reconnect**. |
| CONN-403 | Token has `read_api` only, or its role is below Maintainer for a trigger | Recreate the token with `api` and the right role. |
| CONN-404 | Project path changed, or an `id` was used where the `iid` is expected | Update the project path; map `iid`. |
| CONN-429 | GitLab throttled the token | Nimbus backs off and retries the step. |
| CONN-503 | Self-managed instance unreachable, or the private agent is offline | Check the instance and **Settings > Agents**. |
| WF-400 | An empty title or ref | Use `default()` in the mapping. |

For repositories hosted on GitHub, see [GitHub Connector](nimbus-connector-github.md).
