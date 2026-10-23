---
id: nimbus-troubleshooting-promotion
title: Troubleshooting Workflow Promotion
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-06
owner: Support Engineering
---

Promotion copies the current Development version of a workflow into Production, where it runs against the client's live systems. The Builder clicks **Promote to Production** in the workflow builder, or an integration calls `POST /workflows/{id}/promote`. Nimbus checks that Production has everything the workflow refers to before it creates the new Production version; if any check fails, nothing is copied and Production keeps running the version it had.

This reference covers promotions that are refused, and promoted workflows that fail on their first Production runs. The normal procedure is in [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md), and which tiers include environments is in [Development and Production Environments](nimbus-tier-environments.md).

## Symptoms

- The **Promote to Production** button is missing from the builder, or the environment switcher shows only Development.
- Clicking **Promote to Production** opens a dialog listing steps "without a Production connection" or variables "without a Production value", and the **Promote** button is disabled.
- Promotion stops with "Production has changed since the last promotion".
- An integration's call to the promote endpoint returns `forbidden`, `invalid_request` or `conflict`.
- Promotion succeeds, but the first Production runs fail with WF-400 or CONN-401, or the trigger never fires.

## Common causes

**The workspace has no environments.** Environments are included on the Business and Enterprise tiers. A Starter workspace has a single set of workflows with no Development or Production split, so there is nothing to promote to.

**A step has no Production connection.** Connections belong to one environment. Each step that uses a connector needs a connection mapped for Production under **Workflows > Environments > Connection mapping**. A workflow developed against a HubSpot sandbox account can't be promoted until someone has connected the production HubSpot account and mapped it.

**An environment variable has no Production value.** Every `{{env.NAME}}` expression in the workflow must have a value in both environments. Variables are added in Development as the workflow is built, and the Production value is easy to forget.

**Someone restored Production.** Promotion assumes Production holds exactly what was last promoted. Production is read-only in the builder, but if an Admin restored an older Production version from **Version history**, promoting would silently overwrite that change, so Nimbus stops and reports a conflict.

**The caller lacks permission.** Builders and Admins can promote; a Viewer can't, and the button is hidden for them.

**Environment-specific trigger details.** An inbound webhook trigger has a different URL in each environment, and a schedule is set per environment. A promoted workflow whose sender still posts to the Development URL never runs in Production.

## Diagnosing the problem

1. Confirm the workspace is entitled to environments. `GET /workspace/entitlements` returns `"environments": true` on Business and Enterprise; on Starter it returns `false`.
2. Run the promotion through the API, which returns the reason in the error message:

```http
POST /workflows/wf_5Rk2Nv8D/promote
Authorization: Bearer <api-key>
Idempotency-Key: promote-wf_5Rk2Nv8D-v14

HTTP/1.1 409 Conflict
{"error": {"code": "conflict",
  "message": "Production is missing a connection for step 'create_invoice' (NetSuite) and a value for env.ERP_SUBSIDIARY_ID."}}
```

3. For a conflict, open **Version history**, switch the environment filter to Production and look for a version whose source is "Restored" after the last "Promoted" entry. The entry shows who made it and when.
4. If promotion succeeded but runs fail, open the first failed Production run under **Runs** (filter **Environment: Production**) and read the failing step's code and its resolved inputs.
5. For a trigger that never fires, compare the inbound trigger URL in Production with the one the sending system is configured to call.

## Error reference

| Code | Where it appears | Meaning |
|---|---|---|
| `forbidden` (403) | Promote endpoint | The workspace's Plan Tier has no environments. |
| `invalid_request` (400) | Promote endpoint | The `version` doesn't exist, or `connection_map` names a connection of the wrong connector or environment. |
| `conflict` (409) | Promote endpoint | A step has no Production connection or an `env.` variable has no Production value (the message names each one), or Production was restored since the last promotion. |
| `not_found` (404) | Promote endpoint | The workflow id is wrong or the workflow was deleted. |
| WF-400 | Production run | A data-mapping expression resolved to empty, often an `env.` variable set to an empty string. |
| CONN-401 | Production run | The Production connection's authorisation has expired or been revoked. |
| WF-100 | Production run | The Production trigger is invalid, for example a schedule with no cron expression. |

## Fixes

- **Starter workspace:** promotion isn't possible. Either the client upgrades to Business, which takes effect immediately, or they build and test in a separate copy of the workflow and switch it over by hand. See [Plan Tiers and Entitlements](nimbus-plan-tiers.md) for what each tier includes.
- **Missing connection:** a Builder or Admin opens **Workflows > Environments > Connection mapping**, chooses Production, creates or selects the production connection for each listed connector, and promotes again.
- **Missing variable:** open **Workflows > Environments > Variables**, select Production and enter a value for each name in the error. Secrets referenced as `{{secrets.NAME}}` are workspace-wide and don't need mapping.
- **Conflict:** decide with the client whether the Production change should survive. If it should, make the same change in Development first and promote again. If it shouldn't, click **Promote anyway** in the dialog, or repeat the API call with `{"overwrite_production_changes": true}`; the overwritten version stays in Version history and can be restored.
- **Failing first runs:** reconnect the Production connection, correct the empty variable, and set the Production schedule or give the sender the Production trigger URL. Then retry the failed runs.

Because promotion creates a new Production version, a bad promotion can be undone by restoring the previous Production version; see [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md).

## Escalating to support

Escalate when promotion fails with a reason that the steps above don't explain, or with `internal_error`. Collect:

- workspace id and workflow id, and the Development version number being promoted;
- the full error body from the promote endpoint, or a screenshot of the promotion dialog;
- the Version history entries for Production since the last successful promotion;
- whether the call used an `Idempotency-Key`, and its value, if the same promotion was submitted twice.
