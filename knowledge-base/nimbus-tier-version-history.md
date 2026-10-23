---
id: nimbus-tier-version-history
title: Workflow Version History
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-08-11
owner: Product Operations
---

Version history keeps a record of every published state of a workflow, so a Builder can see what changed, who changed it and when, and put an earlier state back if a change goes wrong. Each time a workflow is published, Nimbus stores a new numbered version. Version history was introduced in release 3.1.0 and is included on every Plan Tier.

This Article explains how versions are created and kept, how they relate to Development and Production environments, and why a Plan Tier change leaves them untouched. The step-by-step restore procedure is in [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md).

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Version history | Yes | Yes | Yes |
| Versions kept per workflow | Last 50 | Last 50 | Last 50 |
| Restore an earlier version | Yes | Yes | Yes |
| Version labels for Development and Production | – | Yes | Yes |

Version history behaves identically on all three tiers. The only tier-dependent part is the environment label on each version, which appears where the workspace has environments.

## How it works

A workflow has one editable draft and a list of published versions. Saving in the builder updates the draft; it doesn't create a version, and the running workflow is unaffected. Clicking **Publish** turns the current draft into a new version with the next number (version 1, version 2 and so on, counted per workflow), and from that moment new runs use it. Runs that were already in progress finish on the version they started with.

Each version records:

- the version number and the time it was published (UTC);
- who published it, as a user or, when published through the API, as an API key;
- the optional publish note the Builder typed;
- the full definition: trigger, steps, mappings, conditions and schedule.

A version doesn't contain connection credentials or secret values. Steps refer to connections by id and to secrets by name, as in `{{secrets.SFTP_KEY}}`, so a restored version uses whatever the connection and the secret hold today.

### Restoring and environments

Restoring never rewrites history. When a Builder restores, say, version 12 of a workflow that is at version 17, Nimbus copies version 12's definition into a new version 18 and publishes it, with the note "Restored from version 12". Versions 13 to 17 stay in the list, so the restore itself can be undone by restoring version 17.

In a workspace with environments, each version carries the environment it was published to. Publishing in Development creates a Development version; promoting it creates a Production version that records which Development version it came from. Restoring an old version in Development doesn't change what runs in Production until the restored version is promoted. Promotion itself is described in [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).

## Turning it on

Version history is always on; every publish creates a version. To make the history useful, encourage clients to publish with a note, and show them where to find it:

1. Open the workflow in **Workflows** and make the change in the builder.
2. Click **Publish**. In the dialog, type a short **Publish note**, for example "Map Account.Region to NetSuite subsidiary".
3. Click **Publish** again to confirm. The new version number appears next to the workflow name.
4. To review the history, open **⋯ > Version history**. Select two versions and click **Compare** to see the steps and mappings that differ.
5. To roll back, select a version and click **Restore this version**.

The same list is available through the API, newest first, with the usual cursor pagination:

```http
GET /workflows/wf_2LQ8RZ5N/versions?limit=3 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "version": 18,
      "environment": "development",
      "published_at": "2025-08-07T14:02:51Z",
      "published_by": { "type": "user", "id": "usr_5KD1TQ8P" },
      "note": "Restored from version 12",
      "restored_from": 12
    },
    {
      "version": 17,
      "environment": "development",
      "published_at": "2025-08-06T09:30:12Z",
      "published_by": { "type": "api_key", "id": "key_8VN3WB2C" },
      "note": "Add retry to NetSuite step",
      "restored_from": null
    }
  ],
  "next_cursor": "djE3"
}
```

In a workspace without environments, `environment` is `null`.

## Limits

| Limit | Value |
|---|---|
| Versions kept per workflow | The last 50 |
| Publish note length | 500 characters |
| Versions compared at once | 2 |
| Who can publish or restore | Builders and Admins |
| Who can view the history | Builders, Admins and Viewers |

When a workflow is published for the 51st time, the oldest version is dropped and can't be recovered. In a workspace with environments, the 50 are counted separately in each environment, so frequent publishing in Development never pushes Production versions out of the list. Clients who need a longer record of a heavily edited workflow can export its definition from **⋯ > Export JSON** before major changes, and keep the exported files in their own source control alongside a note of the version number they came from.

Draft saves are not limited and are not versions: a Builder can save the draft as often as needed, and only **Publish** counts towards the 50.

Deleting a workflow deletes its version history with it. Run history is separate: each run keeps a reference to the version it ran on, for as long as run history is kept.

## When the Plan Tier changes

Nothing about version history changes on an upgrade or a downgrade. The 50-version limit is the same on every tier, and no versions are added, trimmed or relabelled when the tier changes.

The one visible effect comes from environments rather than from version history. After an upgrade from Starter, new versions start carrying an environment label once the workspace uses environments; older versions keep `environment: null`. After a downgrade to Starter, Production versions stay in the history as they were, and new versions are published without a label. Development versions that were never promoted are archived read-only rather than deleted, so they can't be restored until environments are available again. What happens to the environments themselves is covered in [Development and Production Environments](nimbus-tier-environments.md).
