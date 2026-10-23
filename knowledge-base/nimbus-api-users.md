---
id: nimbus-api-users
title: Users API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-30
owner: Platform API Team
---

The Users API reads and manages the people in a Nimbus workspace: list them, look one up, change a role, suspend and reactivate an account, or delete it for good. It mirrors **Settings > Users** in the admin console. New people are added through the [Invitations API](nimbus-api-invitations.md), by single sign-on or by SCIM provisioning, never by this resource.

Every call needs an API key in `Authorization: Bearer <api-key>`. Because a key acts with Admin permissions, it can change any user, including other Admins; treat it accordingly. Each change made through the API is recorded in the audit log with the key's `key_` id as the actor.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/users` | List users, filtered by role, status or email. |
| `GET` | `/users/{id}` | Read one user. |
| `PATCH` | `/users/{id}` | Change `role`, `first_name` or `last_name`. |
| `POST` | `/users/{id}/suspend` | Suspend an active user: sign-in is blocked and the seat is freed. |
| `POST` | `/users/{id}/reactivate` | Reactivate a suspended user, if a seat is free. |
| `DELETE` | `/users/{id}` | Delete the user permanently. |

### Changing a role

Send `PATCH /users/{id}` with `{"role": "admin"}`, `"builder"` or `"viewer"`. The change applies from the user's next request in the console; they don't have to sign in again. Two checks protect the workspace. The last active Admin can't be moved to another role, and a user who still owns workflows can't become a Viewer, because a workflow owner has to be a Builder or Admin. Transfer the workflows first; see [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md). The console steps are in [Changing a User's Role](nimbus-admin-changing-roles.md).

### Suspending, reactivating and deleting

Suspending is reversible and is the right call when someone leaves or is on long leave. The account keeps its role, its workflows keep running, and every active session ends at once. A suspended user doesn't take a seat. `POST /users/{id}/reactivate` restores the account with its previous role, but only while the workspace has a free seat.

`DELETE /users/{id}` can't be undone. The user's sign-in, sessions and two-factor enrolment are removed; workflows they owned keep running, and an Admin must transfer them to a new owner. Run history keeps showing the deleted user's name on runs they started.

For users whose account is managed by SCIM, the identity provider stays in charge: a role change or suspension made here is overwritten by the next SCIM sync, so make the change in the IdP instead. See [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md).

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | User id, prefixed `usr_`. |
| `email` | string | Sign-in email; unique in the workspace. |
| `first_name`, `last_name` | string | Display name. |
| `role` | string | `admin`, `builder` or `viewer`. |
| `status` | string | `active` or `suspended`. |
| `sign_in_method` | string | `password` or `sso`. |
| `two_factor_enabled` | boolean | Whether an authenticator app is enrolled for password sign-in. |
| `provisioned_by` | string | `invitation`, `jit` or `scim`: how the account was created. |
| `owned_workflow_count` | integer | Workflows this user owns. |
| `last_sign_in_at` | string or null | Last successful console sign-in. |
| `suspended_at` | string or null | Set while the user is suspended. |
| `created_at` | string | When the account was created. |

`last_sign_in_at` tracks console sign-ins only. It is the usual way to find dormant accounts worth reviewing before a seat runs out; the API doesn't sort by it, so order the list on the client's side.

## Example request and response

Promoting a Viewer to Builder:

```http
PATCH /users/usr_2045 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"role": "builder"}
```

```json
{
  "id": "usr_2045",
  "email": "priya.raman@clientco.example",
  "first_name": "Priya",
  "last_name": "Raman",
  "role": "builder",
  "status": "active",
  "sign_in_method": "sso",
  "two_factor_enabled": false,
  "provisioned_by": "jit",
  "owned_workflow_count": 0,
  "last_sign_in_at": "2026-03-27T15:42:10Z",
  "suspended_at": null,
  "created_at": "2025-11-03T09:12:55Z"
}
```

Suspending the same user takes an empty body, `POST /users/usr_2045/suspend`, and returns the user with `"status": "suspended"` and `suspended_at` set. Reactivation mirrors it: `POST /users/usr_2045/reactivate`, also with an empty body, returns the user as `active` with the Builder role they had before and `suspended_at` back to null.

## Filtering and pagination

`GET /users` narrows the list with:

- `role`: `admin`, `builder` or `viewer`.
- `status`: `active` or `suspended`.
- `email`: an exact, case-insensitive email match; the quickest way to turn an email into a `usr_` id.
- `sign_in_method`: `password` or `sso`.
- `q`: a partial match on name or email.

Results are sorted by `created_at`, oldest first, and paged with `limit` (default 25, maximum 100) and `cursor`. A seat review that lists every active Builder looks like this:

1. Call `GET /users?role=builder&status=active&limit=100`.
2. Add the users in `data` to the report.
3. If the response has a non-null `next_cursor`, call again with `cursor=<next_cursor>` and the same filters.
4. When `next_cursor` is null, the list is complete.

Seat usage as a single number, without paging, is on `GET /workspace/usage` in the [Workspace API](nimbus-api-workspace.md).

## Errors

| HTTP status | Code | Cause |
|---|---|---|
| 400 | `invalid_request` | An unknown role, an empty name, or a field that can't be changed with `PATCH`, such as `email`. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 404 | `not_found` | No user with that id in this workspace. |
| 409 | `conflict` | Demoting, suspending or deleting the last active Admin. |
| 409 | `conflict` | Making a workflow owner a Viewer before their workflows are transferred. |
| 409 | `conflict` | Reactivating when every seat is taken; free a seat or change the Plan Tier. |
| 409 | `conflict` | Suspending a user who is already suspended, or reactivating one who is active. |
| 429 | `rate_limited` | The workspace's API limit was reached; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |

A user's email can't be changed through the API. For password users it is changed by the user under their profile; for single sign-on users it follows the identity provider.
