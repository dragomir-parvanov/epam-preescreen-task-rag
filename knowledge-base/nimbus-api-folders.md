---
id: nimbus-api-folders
title: Folders API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2025-11-10
owner: Platform API Team
---

Folders group workflows in the **Workflows** list so a workspace with hundreds of automations stays navigable, for example one folder per department or per client system. The Folders API lists, creates, renames and deletes folders; moving a workflow into or out of a folder is done on the workflow itself, through the Workflows API.

Folders are purely organisational. They are one level deep, and they don't change permissions: every Builder can edit and every Viewer can see every workflow, whichever folder it sits in. Clients who ask for per-folder access control should be told that roles apply to the whole workspace; see [Changing a User's Role](nimbus-admin-changing-roles.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/folders` | List the workspace's folders. |
| `POST` | `/folders` | Create a folder. |
| `PATCH` | `/folders/{id}` | Rename a folder. |
| `DELETE` | `/folders/{id}` | Delete an empty folder. |
| `PATCH` | `/workflows/{id}` | Move a workflow by setting its `folder_id` (Workflows API). |

Folders are one level deep: a folder can hold workflows but never another folder, and the API has no parent field. A request body that includes `parent_id` is rejected with `400 invalid_request`. A workflow is in at most one folder at a time, or in none, in which case the console shows it at the top level of the list.

### Moving workflows between folders

To move a workflow, send `PATCH /workflows/{id}` with `{"folder_id": "fld_..."}`. To take it out of every folder, send `{"folder_id": null}`. Moving a workflow doesn't publish a new version, doesn't interrupt its runs, and doesn't change its owner, schedule or active state; the move is recorded in the audit log as `workflow.moved`.

There is no bulk move endpoint. To move many workflows, list them with a filter and send one `PATCH` per workflow, as shown under Filtering and pagination.

### Deleting a folder

`DELETE /folders/{id}` only works on an empty folder and answers `204 No Content`. If any workflow is still in the folder the request fails with `409 conflict`, and the message gives the number of workflows left. Move them out first, either to another folder or to the top level with `"folder_id": null`. Deleting a folder never deletes workflows.

## Object fields

| Field | Type | Writable | Description |
|---|---|---|---|
| `id` | string | No | Folder id, prefixed `fld_`. |
| `name` | string | Yes | 1 to 80 characters, unique in the workspace (compared ignoring case). Leading and trailing spaces are trimmed. |
| `workflow_count` | integer | No | How many workflows are in the folder, counting Development and Production workflows separately where environments are used. |
| `created_by` | string | No | The `usr_` or `key_` id that created the folder. |
| `created_at` | string | No | ISO 8601 timestamp in UTC. |
| `updated_at` | string | No | When the folder was last renamed. |

On workflows, the matching field is `folder_id`: a `fld_` id or `null`.

## Example request and response

Create a folder for finance automations, then move a workflow into it:

```http
POST /folders HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 0b9e7d52-folders-finance

{"name": "Finance automations"}
```

```json
{
  "id": "fld_7Pq3rW1z",
  "name": "Finance automations",
  "workflow_count": 0,
  "created_by": "key_3mT8bQ1x",
  "created_at": "2025-11-06T13:44:09Z",
  "updated_at": "2025-11-06T13:44:09Z"
}
```

```http
PATCH /workflows/wf_1Bv6pH9t HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"folder_id": "fld_7Pq3rW1z"}
```

The `PATCH` answers `200 OK` with the full workflow, whose `folder_id` is now `fld_7Pq3rW1z`. Renaming the folder later with `PATCH /folders/fld_7Pq3rW1z` and `{"name": "Finance and billing"}` changes nothing on the workflows, because they hold the id, not the name.

## Filtering and pagination

`GET /folders` returns folders sorted by `name` and is cursor-paginated: `limit` (default 25, maximum 100) and `cursor`. It accepts `name_contains` for a case-insensitive search. Most workspaces have few enough folders to fit in one page of 100.

To see a folder's contents, use `GET /workflows?folder_id=fld_...`; `folder_id=none` returns workflows that aren't in any folder. Moving every inactive workflow out of a folder into an "Archive" folder, for example, goes like this:

1. Create or find the target folder and note its id, say `fld_2Ar8cH0v`.
2. Call `GET /workflows?folder_id=fld_7Pq3rW1z&status=inactive&limit=100`.
3. For each workflow in `data`, send `PATCH /workflows/{id}` with `{"folder_id": "fld_2Ar8cH0v"}`.
4. Call step 2 again without a cursor until `data` is empty.

Because each `PATCH` removes a workflow from the filtered list, step 4 deliberately starts from the first page again rather than following `next_cursor`, which would skip workflows. When nothing is being changed, follow `next_cursor` as usual until it is `null`.

## Errors

Every error uses the `{"error": {"code": "...", "message": "..."}}` envelope; see [API Error Format and Idempotency](nimbus-api-error-format.md).

| HTTP status | Code | Reason |
|---|---|---|
| 400 | `invalid_request` | `name` is empty or longer than 80 characters, or the body includes `parent_id`. |
| 400 | `invalid_request` | `PATCH /workflows/{id}` sent a `folder_id` that isn't a valid `fld_` id. |
| 401 | `unauthorized` | Missing, expired or revoked API key. |
| 404 | `not_found` | No folder with that id, or the `folder_id` on a workflow `PATCH` points to a deleted folder. |
| 409 | `conflict` | Another folder already has that name, or `DELETE` was sent for a folder that still contains workflows. |
| 429 | `rate_limited` | The workspace is over its API rate limit; space out bulk moves. |
| 500 | `internal_error` | An internal Nimbus error; retry the request. |

A `409` on create is common in scripts that run more than once. Send an `Idempotency-Key` with `POST /folders`, or look the folder up with `name_contains` before creating it.
