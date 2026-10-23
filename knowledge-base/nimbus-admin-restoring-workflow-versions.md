---
id: nimbus-admin-restoring-workflow-versions
title: Restoring a Previous Workflow Version
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-02
owner: Workspace Administration Team
---

Every time a Builder publishes a workflow, Nimbus keeps the published definition as a numbered version. When a change goes wrong (a mapping that sends empty fields to Salesforce, a condition that now skips every record), the quickest fix is usually to put the last good version back from **Version history** in the builder, then work out what broke at leisure.

Restoring never rewrites history. It copies the old definition into a new version on top, so the faulty version stays visible and can be compared or restored again later.

## Before you begin

- **Plan Tier:** any. Version history has been on every tier since release 3.1.0.
- **Role:** Builder or Admin to restore. Viewers can open Version history and compare versions, but the **Restore** button is hidden for them.
- **Know which environment you're in.** On Business and Enterprise workspaces with environments, Development and Production each have their own version history. Restoring in Production doesn't touch Development, and the reverse. See [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).
- **Unpublished draft changes.** Restoring replaces the current draft. If someone has unpublished edits they want to keep, they should publish or copy them first.

## How it works

A version is created each time the workflow is published, and only then; autosaved drafts aren't versions. Nimbus keeps the last 50 versions of each workflow. When a 51st is published, the oldest one drops off and can no longer be viewed or restored.

Each version records:

| Field | Example |
|---|---|
| Version number | `27` |
| Published at | `2026-01-28 16:42` (workspace time zone) |
| Published by | The user, or "Restored from v19 by …", or "Promoted from Development v31" |
| Note | The optional text entered at publish time |
| Definition | Trigger, steps, step keys, mappings, conditions and per-step settings |

A version holds the workflow's definition only. It doesn't include connection credentials, secret values or `{{env.NAME}}` values, so restoring an old version uses today's connections, secrets and environment variables. If an old version refers to a secret or variable that has since been removed, the restore succeeds but runs fail with WF-400 at the step that needs it.

Restoring version 19 when the current version is 27 creates version 28 with version 19's definition and the note "Restored from v19". An active workflow stays active: its next run uses version 28, while any run already in progress finishes on the version it started with. Run history keeps the version number of each run, so it is always clear which definition produced which result.

### Comparing two versions

**Compare** shows two versions side by side, step by step. Added steps are marked green, removed steps red, and changed steps amber, with the changed fields listed underneath (for example, a mapping expression that changed from `{{trigger.body.email}}` to `{{lower(trigger.body.email)}}`). Comparing is read-only and is the safest first move when a client reports that "something changed".

## Step-by-step

To restore a previous version in the console:

1. Open **Workflows** and select the workflow. Check the environment switcher if the workspace uses environments.
2. Click **Version history** in the builder toolbar. The list shows the newest version first.
3. Find the version that last worked. Run history helps here: open a successful run on **Runs** and note the version it ran on.
4. Tick that version and the current one, then click **Compare** to confirm the difference is the one you expect.
5. Open the old version's **⋯** menu and click **Restore this version**.
6. Add a note such as "Rollback: v27 cleared the Account owner mapping", then click **Restore**.

The API lists versions, which is useful for finding the right one across many workflows or for keeping a record outside Nimbus. Restoring is done in the console.

```http
GET /workflows/wf_3Yd6pK0s/versions?limit=5 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "version": 28,
      "published_at": "2026-01-29T10:05:12Z",
      "published_by": "usr_6Fq9wB3e",
      "note": "Restored from v19",
      "restored_from_version": 19
    },
    {
      "version": 27,
      "published_at": "2026-01-28T16:42:51Z",
      "published_by": "usr_1Kc5sV8m",
      "note": "Map Account owner from HubSpot",
      "restored_from_version": null
    }
  ],
  "next_cursor": "djI2"
}
```

An API key is needed for the call; see [Creating and Rotating API Keys](nimbus-admin-api-keys.md).

## Verifying the change

1. **Version history** shows a new version at the top with the note "Restored from v…" and your name.
2. Compare the new version with the one you restored: Nimbus should report no differences.
3. Click **Run now** with test data, or wait for the next scheduled or triggered run, and open it on **Runs**. The run detail shows the new version number, and the step that was failing should now succeed.
4. The restore is also recorded in the audit log as `workflow.version_restored`; see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| The version the client wants isn't in the list | Only the last 50 versions are kept | It can't be recovered. Rebuild from the oldest available version. |
| **Restore** button missing | The user is a Viewer | Ask a Builder or Admin, or change the user's role. |
| Restored workflow fails with WF-400 | The old version refers to an `{{env.NAME}}` or `{{secrets.NAME}}` that no longer exists | Re-create the variable or secret, or fix the step and publish. |
| Restored workflow fails with CONN-404 | A step refers to a record, folder or object that was removed in the third-party app since that version | Update the step to the current object and publish. |
| Production still behaves the old way | The restore was done in Development | Restore in Production, or promote the restored Development version. |
| The run that failed is still on the bad version | It started before the restore | Retry it from **Runs**; retries use the current version. See [Searching and Exporting Run History](nimbus-admin-run-history.md). |
