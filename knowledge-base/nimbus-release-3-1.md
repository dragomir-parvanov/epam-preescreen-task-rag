---
id: nimbus-release-3-1
title: Nimbus 3.1 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2025-06-02
owner: Release Management
---

Nimbus 3.1.0 was released on 2025-06-02 for every v3 workspace. It adds workflow version history, support for the `Idempotency-Key` header on API `POST` requests, and four connectors: Azure Blob Storage, Microsoft SQL Server, GitLab and Marketo.

The release is additive. No existing workflow, connection or API call changes behaviour, and no client action is needed unless the client wants to adopt the new features.

## Highlights

Builders can now see every published version of a workflow and roll back to an earlier one in two clicks. API clients that retry `POST` requests after a timeout can send an `Idempotency-Key` so a retried call never starts a second run or creates a second user. The catalogue grows by four connectors, bringing Azure storage, SQL Server databases, GitLab projects and Marketo into workflows.

## New features

Publishing a workflow in the builder now creates a new, numbered version. The builder's **Version history** panel lists the last 50 versions of each workflow with the publisher, the publish time and an optional note entered at publish time. Selecting a version shows it read-only, and **Restore this version** copies it forward as a new version, so history is never rewritten and a restore can itself be undone. Version history is available on every Plan Tier; see [Workflow Version History](nimbus-tier-version-history.md) and [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md). The versions are also listed by `GET /workflows/{id}/versions`.

### New connectors

| Connector | Authentication | Trigger |
|---|---|---|
| Azure Blob Storage | Connection string or SAS token | Polling trigger on new blobs |
| Microsoft SQL Server | SQL authentication over TLS | Polling trigger on a query |
| GitLab | Personal, group or project access token | Push triggers |
| Marketo | Client ID and client secret | Polling triggers |

Azure Blob Storage watches a container (optionally under a prefix) for new blobs and offers actions to upload, download, copy and delete blobs. A SAS token needs at least the Read and List permissions for the trigger, plus Write and Delete if the workflow writes back. Details are in [Azure Blob Storage Connector](nimbus-connector-azure-blob-storage.md).

Microsoft SQL Server runs a polling query every 5 minutes and starts one run per new row, keyed on a column the Builder picks (typically an identity or `modified_at` column). The connection always encrypts traffic with TLS; a server that refuses encrypted connections fails the connection test. See [Microsoft SQL Server Connector](nimbus-connector-sql-server.md).

GitLab registers a project or group hook automatically when a trigger is saved, so push, merge request and pipeline events arrive within seconds. The access token needs the `api` scope. See [GitLab Connector](nimbus-connector-gitlab.md).

Marketo connects with the client ID and client secret of a LaunchPoint custom service, plus the instance's REST endpoint host. Its triggers poll for new and updated leads and for program membership changes. See [Marketo Connector](nimbus-connector-marketo.md).

### Idempotency keys

Every `POST` endpoint now accepts an `Idempotency-Key` header. Nimbus remembers each key for 24 hours: a repeat of the same request with the same key returns the original response, including the original status code, and performs no new work. Reusing a key with a different request body within that window is rejected with `409 conflict`. Keys are scoped to the workspace, so two workspaces can use the same key value safely. The full behaviour is in [API Error Format and Idempotency](nimbus-api-error-format.md).

## Improvements

- The run detail view shows the workflow version that ran, with a link to that version in Version history.
- `GET /runs` accepts a `workflow_version` filter.
- The connection test for database connectors reports the server version it reached.
- The HTTP Request connector shows the response headers in the step log, with `Authorization` values masked.
- Folder names in the workflow list can be up to 80 characters.
- The workflow list shows each workflow's current version number next to its status, and sorting by **Last published** now uses the publish time of that version.
- The audit log records `workflow.published` and `workflow.version_restored` events with the version number, so an Admin can see who rolled a workflow back; see [Audit Log Event Catalogue](nimbus-security-audit-events.md).

## Fixed issues

| Issue | Description |
|---|---|
| NIM-4261 | A schedule saved with a non-default IANA time zone fired one hour early for a week after a daylight-saving change. |
| NIM-4264 | The Salesforce polling trigger skipped records updated in the same second as the previous poll. |
| NIM-4270 | Cancelling a queued run from the console left it shown as `queued` until the page was refreshed. |
| NIM-4273 | `GET /runs/{id}/steps` returned steps out of order for runs with a loop step. |
| NIM-4279 | The Box connector's upload action failed for files whose names contained non-Latin characters. |
| NIM-4282 | A webhook endpoint test from the console reported success before the receiver had answered. |

## Deprecations and breaking changes

Nothing breaks in 3.1. Workflows published before the upgrade appear in Version history as a single version holding their current definition; earlier edits were not recorded and can't be restored. Sending `Idempotency-Key` is optional, and requests without it behave exactly as before.

## Upgrade notes

The release was applied to all v3 workspaces automatically. To adopt the new features:

1. Ask Builders to add a short note when they publish, so Version history is useful during a rollback.
2. Update API clients that retry `POST` calls to generate one key per logical operation (a UUID is fine) and reuse it on every retry of that operation.
3. Keep the key for at least as long as the client might retry; after 24 hours the same key is treated as new.
4. Connect the new connectors from **Connections > New connection**, then use **Test** before building on them.

A retried run request with an idempotency key:

```http
POST /workflows/wf_3c71a9/runs HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 7d0e2c4b-9a51-4f3e-8f6a-2b1d9c0e5a44

{"input": {"order_id": "SO-20931"}}
```

If the first attempt reached Nimbus, the retry returns the same `run_` id instead of starting a second run.
