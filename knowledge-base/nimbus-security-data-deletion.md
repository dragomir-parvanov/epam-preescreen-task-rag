---
id: nimbus-security-data-deletion
title: Data Retention and Deletion
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-27
owner: Security & Compliance
---

Clients ask two retention questions in almost every security review: how long Nimbus keeps their data, and how they get it deleted when they need to. This note answers both for a v3 workspace. It states the retention Nimbus applies on its own, what an Admin can delete straight away, what happens when a whole workspace is deleted, and how a CSM handles a deletion request that the console can't fulfil.

Two retention periods are documented elsewhere and are only linked here: what happens to a deprovisioned user's data is in [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md), and how long audit-log events are kept on each Plan Tier is in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Scope

The note covers the data Nimbus stores for a workspace: run history, workflow versions, connections and their credentials, secrets, users and the workspace itself. It covers deletion by the client (in the console or the API), deletion by Nimbus on a schedule, and deletion carried out by OmniCorp support on request.

It doesn't cover data that workflows have already written into connected apps such as Salesforce or SharePoint Online. Deleting a Nimbus workflow or run doesn't reach into those apps; the client deletes that data in the app itself.

## Controls in place

Nimbus applies these retention rules without any setting:

| Data | Retention | What happens at the end |
|---|---|---|
| Run history: inputs, outputs and step logs | 90 days, on every Plan Tier | Deleted automatically, run by run, as each run passes 90 days |
| Workflow versions | The last 50 versions of each workflow | The oldest version is deleted when a 51st is published |
| Credentials of a deleted connection | None | Erased immediately when the connection is deleted |
| Value of a deleted secret | None | Erased immediately when the secret is deleted |
| Audit log | Depends on the Plan Tier | See [Plan Tiers and Entitlements](nimbus-plan-tiers.md) |
| Deprovisioned users | Fixed period, then deleted | See [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md) |
| A deleted workspace | Restorable by OmniCorp support for 14 days | Every workflow, run, connection and user is then permanently deleted |

The 90-day run history window is the one clients most often need to plan around. A run's trigger payload and step outputs can contain personal data, such as a candidate record passed from Workday to Slack, and that data stays readable in **Runs** until the run ages out. Clients who need run data for longer export it before then; see [Searching and Exporting Run History](nimbus-admin-run-history.md).

Connection credentials are erased immediately because a deleted connection has no further use and keeping an OAuth refresh token or a database password would only add exposure. The erasure can't be undone: to use the app again, a Builder or Admin creates a new connection and authorises it from scratch.

### Workspace deletion

An Admin deletes a workspace under **Settings > Workspace**. For 14 days afterwards OmniCorp support can restore it in full, which covers the case of an Admin deleting the wrong workspace. After 14 days every workflow, run, connection and user in it is permanently deleted, and support can't bring any of it back. The step-by-step procedure is in [Deleting a Workspace](nimbus-admin-deleting-a-workspace.md).

## Admin settings

Most deletions are done by an Admin, or by a Builder for connections, in the console:

1. **Delete a connection.** Open **Connections**, select the connection, click **Delete** and confirm. The builder flags every step that used it, and those workflows can't be published again until each step is pointed at another connection.
2. **Delete a secret.** Open **Settings > Secrets**, click **Delete** next to the secret and confirm. Expressions that reference `{{secrets.<NAME>}}` resolve to empty and the step fails with WF-400.
3. **Delete a user.** Open **Settings > Users**, select the user and click **Delete**. Transfer ownership of their workflows first, as described in [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md).
4. **Delete the workspace.** Open **Settings > Workspace**, click **Delete workspace**, type the workspace name and confirm.

Connections and secrets can also be deleted through the API, which suits clients who script their off-boarding:

```http
DELETE /connections/con_7Yb3Rw9Px HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 204 No Content
```

```http
DELETE /secrets/BAMBOOHR_API_KEY HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 204 No Content
```

A repeated call for an id or name that no longer exists returns 404 with the `not_found` error code, which a script can treat as success.

### Handling a client deletion request

Some requests can't be met from the console, typically a data subject's erasure request that touches run history before the 90 days are up. The client is the controller and OmniCorp the processor under the data processing agreement, so the client decides what is deleted and OmniCorp carries it out:

1. Ask the client for the workspace id (`ws_…`) and the run ids (`run_…`) to purge, or a date range plus a workflow id (`wf_…`).
2. Open a case with OmniCorp support, marked as a deletion request, with those ids.
3. Support deletes the runs and confirms in writing; pass the confirmation to the client.

## Shared responsibilities

| Area | OmniCorp | Client |
|---|---|---|
| Run history | Deletes runs automatically after 90 days | Exports runs it must keep longer; avoids passing personal data it doesn't need through workflows |
| Connections and secrets | Erases credentials and secret values immediately on deletion | Deletes connections and secrets it no longer uses |
| Users | Applies the documented retention to suspended and deleted users | Removes leavers promptly, in the console or through its IdP |
| Workspace deletion | Keeps a restorable copy for 14 days, then deletes it permanently | Exports anything it needs before deleting, and confirms the deletion is intended |
| Data in connected apps | Nothing; Nimbus doesn't delete data in third-party apps | Deletes data in each connected app under its own contract with that vendor |
| Deletion requests | Carries out purges requested through support and confirms them | Decides what must be deleted and supplies the ids |

## Evidence for auditors

The audit log records each deletion with the actor and the time: `connection.deleted`, `secret.deleted`, `user.deleted` and `workspace.deleted`. A client can filter and export these under **Settings > Audit log**, or query them with `GET /audit-log/events?action=connection.deleted`; see [Audit Log API](nimbus-api-audit-log.md). For deletions OmniCorp carries out, the written confirmation from support is the evidence to keep. The retention and secure-disposal controls themselves are covered by OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate, which the CSM shares under NDA.
