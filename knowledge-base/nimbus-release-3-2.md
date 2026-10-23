---
id: nimbus-release-3-2
title: Nimbus 3.2 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2025-08-04
owner: Release Management
---

Nimbus 3.2.0 was released on 2025-08-04 for every v3 workspace. Its main change is separate Development and Production environments for workflows on the Business and Enterprise tiers, together with a promotion step in the console and a new `POST /workflows/{id}/promote` endpoint. The release also adds the NetSuite and Intercom connectors.

Starter workspaces receive the connectors and the fixes below, but not environments; their workflows keep a single definition as before.

## Highlights

| Area | What changed | Tiers |
|---|---|---|
| Environments | Each workflow has a Development and a Production version; Builders edit in Development and promote to Production | Business, Enterprise |
| API | `POST /workflows/{id}/promote` and the `{{env.<NAME>}}` expression | Business, Enterprise |
| Connectors | NetSuite and Intercom | All tiers |

## New features

### Development and Production environments

On Business and Enterprise workspaces, the workflow builder now has an environment switcher next to the workflow name. Edits are always made in **Development**; **Production** is read-only in the builder and changes only through promotion. Scheduled, event-triggered and inbound webhook runs use the Production definition, while **Run now** and test runs in the builder use whichever environment is selected.

Each environment holds its own set of environment variables and its own connection for every connector step. A typical setup points Development at a Salesforce sandbox org and Production at the production org, with the same workflow logic in both. Variables are referenced in any step with `{{env.<NAME>}}`, for example `{{env.REGION_CODE}}`, and are edited under the workflow's **Environments** tab in the builder.

Promoting copies the Development definition to Production and publishes it as a new version, so the previous Production definition stays in Version history and can be restored. Builders and Admins can promote from the builder with **Promote to Production**, which shows a diff of changed steps and asks for an optional note. Promotion copies the trigger, the steps and their settings; it never copies environment variables or connection assignments, which stay with each environment, so promoting can't point Production at a sandbox account by accident. If a Production variable that a promoted step references has no value yet, promotion is blocked and the dialog lists the missing names. The full workflow is in [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md), and tier details in [Development and Production Environments](nimbus-tier-environments.md).

### NetSuite and Intercom connectors

**NetSuite** connects with token-based authentication: the account ID, a consumer key and secret from an integration record, and a token ID and secret issued to a user and role. The role needs the **Log in using Access Tokens** and **REST Web Services** permissions, plus access to the record types the workflow reads or writes. Triggers poll for new and changed records, such as sales orders, customers and vendor bills. See [NetSuite Connector](nimbus-connector-netsuite.md).

**Intercom** connects with OAuth 2.0; the installing teammate must be able to install apps in the Intercom workspace. Its push triggers fire on new conversations, conversation replies, closed conversations and new contacts, delivered within seconds. Actions create and update contacts, add notes and tags, and reply to conversations as a chosen admin. See [Intercom Connector](nimbus-connector-intercom.md).

## Improvements

- The workflow list has an **Environment** column showing whether Production is behind Development.
- `GET /workflows/{id}` returns an `environments` object with the version number currently in each environment.
- The run detail view and `GET /runs/{id}` show which environment a run used.
- Connections can be given a description, shown in the step picker, to tell sandbox and production accounts apart.
- Expression autocomplete in the builder now suggests `{{env.<NAME>}}` variables defined for the selected environment.
- Each promotion is recorded in the audit log as `workflow.promoted`, with the actor, the version number and the note, so an Admin can trace what reached Production and when.
- Workflow templates open in Development on Business and Enterprise workspaces, so a template can be tried against test accounts before it is promoted.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-4418 | Restoring a version from Version history did not restore its per-step retry count. |
| NIM-4423 | The PostgreSQL polling trigger stopped after a query returned a column of type `interval`. |
| NIM-4427 | An `Idempotency-Key` sent on `POST /invitations` was ignored when the invited email differed only in letter case. |
| NIM-4431 | The Azure Blob Storage trigger started duplicate runs for blobs overwritten during a poll. |
| NIM-4436 | The Marketo connector's lead search failed when a filter value contained a comma. |
| NIM-4440 | The **Last run** column showed a test run from the builder as the workflow's last production run. |

## Deprecations and breaking changes

On Business and Enterprise workspaces, every existing workflow was migrated so that its current published definition became both its Development and its Production version, and its existing connections were assigned to both environments. Nothing runs differently after the upgrade.

The one behaviour change is for clients that update workflows through `PATCH /workflows/{id}`. On Business and Enterprise workspaces, a `PATCH` now changes the Development definition only. Integrations that deploy workflows by API must call `POST /workflows/{id}/promote` afterwards, or the change never reaches Production. Starter workspaces are unaffected.

## Upgrade notes

Clients adopting environments usually follow this order:

1. For each connector used by a workflow, create a second connection to the third-party app's test or sandbox account, and give both connections clear descriptions.
2. In the builder, open the workflow's **Environments** tab and assign the test connections and variable values to Development.
3. Replace hard-coded values that differ between environments (folder ids, queue names, record owners) with `{{env.<NAME>}}` expressions.
4. Make and test changes in Development, then promote. If promotion fails, see [Troubleshooting Workflow Promotion](nimbus-troubleshooting-promotion.md).
5. Update deployment scripts that use `PATCH /workflows/{id}` to call the promote endpoint after the update, as below.

```http
POST /workflows/wf_9b24e1/promote HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 5f1c8e70-2a9d-4b6e-9d3f-0c7a1e4b8d22

{"note": "Route EMEA orders to the new queue"}
```

```json
{
  "workflow_id": "wf_9b24e1",
  "environment": "production",
  "version": 14,
  "promoted_by": "key_2d7f0a",
  "promoted_at": "2025-08-12T09:41:07Z"
}
```

The endpoint is documented in [Environments and Promotion API](nimbus-api-environments.md).
