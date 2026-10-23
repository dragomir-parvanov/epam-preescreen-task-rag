---
id: nimbus-admin-promoting-workflows
title: Promoting Workflows from Development to Production
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-23
owner: Workspace Administration Team
---

Environments let a team change a workflow without touching the copy that runs against live systems. Every workflow on a Business or Enterprise workspace has a Development environment, where Builders edit and test, and a Production environment, which only changes when someone promotes a version into it.

This guide covers how promotion works, what it carries across and what it leaves behind, and how to promote from the builder or with `POST /workflows/{id}/promote`.

## Before you begin

Check the following before promoting a workflow for the first time:

| Requirement | Detail |
|---|---|
| Plan Tier | Business or Enterprise. Starter workspaces have a single environment and no Promote button; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md). |
| Role | Builder or Admin. Viewers can see both environments but can't promote. |
| Published version | Promotion copies a published version. Unpublished edits in the Development draft are never promoted. |
| Production connections | Each connector the workflow uses needs a connection selected for Production (Workflows > the workflow > Environments > Production > Connections). |
| Production variables | Every `{{env.NAME}}` the workflow references needs a Production value. |

If the workflow reads credentials with `{{secrets.NAME}}`, make sure the named secret exists in the vault before the first Production run; see [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md).

## How it works

A workflow's definition (its trigger, steps, field mappings, conditions, loops and approval steps) is shared between environments by version. What differs between them is configuration: which connection each connector step uses, and the values of environment variables. Builders typically point Development at a Salesforce sandbox org or a test Slack channel, and Production at the real ones, while the steps refer to them the same way.

Promotion takes one published Development version and makes it the current Production version. Production gets a new version number in its own history, with the note "Promoted from Development v14" (or whichever version was chosen), so a Production rollback can later be done from Version history without touching Development.

What promotion copies and what it doesn't:

| Copied to Production | Not copied |
|---|---|
| Trigger type and configuration, including the cron expression of a schedule trigger | Connection selections (set per environment) |
| Steps, step keys, mappings and expressions | `{{env.NAME}}` values (set per environment) |
| Per-step retry settings and approval-step approvers | Run history and step logs |
| The workflow name, description and folder | The inbound webhook trigger URL (each environment has its own trigger token) |

Secrets referenced with `{{secrets.NAME}}` are resolved by name from the vault at run time, so promotion copies the reference, never the secret value.

Promotion doesn't change whether the Production workflow is active. A workflow that was active in Production stays active and picks up the new version from its next run; runs already in progress finish on the version they started with. A workflow promoted for the first time arrives inactive and must be activated.

## Step-by-step

To promote a workflow in the console:

1. Open **Workflows** and select the workflow. The environment switcher at the top of the builder shows **Development**.
2. Publish the changes you want to promote. Note the version number shown in the confirmation banner.
3. Open **Environments > Production**. Under **Connections**, pick a Production connection for every connector listed. Under **Variables**, fill in a value for every name marked **Missing**.
4. Click **Promote**, choose the Development version (the latest published one is selected by default) and add an optional note for the Production history.
5. Review the summary. Nimbus lists any connector without a Production connection and any variable without a Production value; the **Promote** button stays disabled until the list is empty.
6. Click **Promote to Production**.
7. For a first promotion, switch to **Production** and click **Activate**.

The same promotion through the API, using a key created as described in [Creating and Rotating API Keys](nimbus-admin-api-keys.md):

```http
POST /workflows/wf_8Kq2nR7t/promote HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: promote-wf_8Kq2nR7t-v14

{
  "version": 14,
  "note": "Adds the HubSpot owner lookup"
}
```

A successful call answers `200 OK` with the new Production version:

```json
{
  "workflow_id": "wf_8Kq2nR7t",
  "environment": "production",
  "version": 9,
  "promoted_from_version": 14,
  "active": true
}
```

If a connection or variable is missing for Production, the call fails with `409` and the error code `conflict`, and the message names the missing item. A first promotion arrives with `"active": false`; activate it with `POST /workflows/{id}/activate`.

## Verifying the change

Switch the builder to **Production** and open **Version history**. The newest entry should carry the note "Promoted from Development v14" and your name. Then check that the Production configuration resolves as expected:

- Open the first step that uses a connection and confirm the connection name shown is the Production one, not the sandbox.
- In **Runs**, filter by the workflow and look for the next run after the promotion. Its detail page shows the version number it ran on.
- For a schedule trigger, the **Next run** time under the trigger panel should match the cron expression you tested in Development.

If you'd rather not wait for the schedule, click **Run now** in the Production builder. That run is a real run: it counts towards the monthly quota and acts on live systems.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| No **Environments** tab or **Promote** button | The workspace is on Starter | Environments need Business or Enterprise. |
| **Promote** is disabled with "1 connection not set" | A connector has no Production connection | Pick one under **Environments > Production > Connections**. |
| Production runs fail with WF-400 | An expression resolves to empty, often an `{{env.NAME}}` whose Production value is blank | Fill in the variable under **Environments > Production > Variables** and rerun. |
| Production runs fail with CONN-401 | The Production connection's authorisation expired or was revoked | A Builder or Admin clicks **Reconnect** on the connection. |
| A client's system posts to the old URL after go-live | Each environment has its own inbound webhook trigger URL | Give the client the Production trigger URL from the trigger panel. |
| Production behaves like an older version | The workflow was promoted, but a long run started before promotion is still going | Wait for that run to finish; new runs use the promoted version. |

For promotions that complete but leave Production in an unexpected state, roll back from Production's Version history as described in [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md).
