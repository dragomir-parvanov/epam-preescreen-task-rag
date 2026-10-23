---
id: nimbus-v2-api-users
title: Users API (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-03-03
owner: Platform API Team
---

The Users API manages the people in a workspace on the legacy Nimbus platform: it lists users, invites new ones, changes their role, and suspends or reactivates them. It is the API equivalent of **Admin > Users** in the console, and HR or IT teams use it to script joiner and leaver steps from their own systems.

Users reach a workspace in one of two ways only: an Admin invites them, or they sign in with single sign-on for the first time and are created by just-in-time provisioning. There is no SCIM provisioning, so leavers aren't removed automatically when they leave the identity provider; a client's offboarding process has to call this API, or an Admin has to act in the console. The console procedures are in [Inviting and Removing Users (v2)](nimbus-v2-admin-managing-users.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/users` | List users, page by page. |
| `POST` | `/users` | Invite a user by email with a role. |
| `GET` | `/users/{id}` | Read one user. |
| `PATCH` | `/users/{id}` | Change a user's role or name. |
| `POST` | `/users/{id}/suspend` | Suspend a user: sign-in is blocked and console sessions end. |
| `POST` | `/users/{id}/reactivate` | Reactivate a suspended user with their previous role. |
| `DELETE` | `/users/{id}` | Delete a user, or withdraw an invitation that hasn't been accepted. |

There is no separate invitations resource. An invited user appears in `GET /users` with status `invited` until they accept.

### Inviting a user

`POST /users` takes `email` (required), `role` (`admin`, `builder` or `viewer`) and optionally `first_name` and `last_name`. Without a `role`, the user is invited as a Viewer. Nimbus emails the invitation straight away and answers `201 Created` with the new user in status `invited`. The request doesn't accept an `Idempotency-Key` header; if it times out, look the address up with `GET /users?email=<address>` before sending it again.

### Changing a role

Send `PATCH /users/{id}` with `{"role": "builder"}`. The new role applies to the user's next request in the console, without signing them out. Single sign-on group attributes are ignored, so users created by just-in-time provisioning start as Viewers and keep that role until it is changed here or under **Admin > Users**. A role set through the API isn't overwritten by later sign-ins.

## Object fields

| Field | Type | Writable | Description |
|---|---|---|---|
| `id` | string | No | User id, prefixed `usr_`. |
| `email` | string | On invite only | The user's login. Can't be changed afterwards; delete and re-invite instead. |
| `first_name`, `last_name` | string | Yes | Display name. Replaced at each sign-in for users who sign in with single sign-on. |
| `role` | string | Yes | `admin`, `builder` or `viewer`. |
| `status` | string | No | `invited`, `active` or `suspended`; changed by the suspend and reactivate endpoints. |
| `source` | string | No | `invitation` or `jit`, depending on how the user was created. |
| `created_at` | string | No | ISO 8601, UTC. |
| `last_sign_in_at` | string or null | No | The most recent console sign-in; `null` for invited users. |

Suspension keeps the user's record, role and workflow ownership, and a suspended user no longer takes a seat. Workflows they own keep running, but an Admin should give them a new owner in the console.

## Example request and response

Invite a new analyst as a Builder:

```http
POST /users HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "email": "priya.raman@example.co.uk",
  "role": "builder",
  "first_name": "Priya",
  "last_name": "Raman"
}
```

```json
{
  "id": "usr_8Nc3Tf1v",
  "email": "priya.raman@example.co.uk",
  "first_name": "Priya",
  "last_name": "Raman",
  "role": "builder",
  "status": "invited",
  "source": "invitation",
  "created_at": "2025-02-27T09:12:48Z",
  "last_sign_in_at": null
}
```

When Priya accepts, `status` becomes `active`. For an offboarding script, the matching call is `POST /users/usr_8Nc3Tf1v/suspend` with no body, which answers `200 OK` with the updated user.

## Filtering and pagination

`GET /users` is page-based: `page` from 1, `per_page` default 50 and maximum 100. Each response includes `total`, the number of users matching the filters, alongside `data`. Filters:

- `role`: `admin`, `builder` or `viewer`.
- `status`: `invited`, `active` or `suspended`.
- `source`: `invitation` or `jit`.
- `email`: an exact, case-insensitive match, for looking up one person.

Results are sorted by `created_at`, oldest first. A quarterly access review that lists every active Admin and Builder runs like this:

1. Call `GET /users?status=active&role=admin&per_page=100&page=1` and read `total`.
2. Request further pages, increasing `page`, until you have `total` users.
3. Repeat steps 1 and 2 with `role=builder`.
4. Compare `last_sign_in_at` against the review period and suspend accounts nobody uses.

## Errors

An error is the HTTP status plus a JSON body with a single message, such as `{"error": "user not found"}`. There are no error codes; log the message with the status.

| HTTP status | Typical message | Why |
|---|---|---|
| 400 | `invalid role` / `invalid email address` | The role isn't one of the three values, or the email can't be parsed. |
| 401 | `invalid API key` | The key is missing or has been deleted under Admin > API keys. |
| 404 | `user not found` | Unknown `usr_` id in this workspace. |
| 409 | `a user with this email already exists` | `POST /users` for an address that is already active, invited or suspended in the workspace. |
| 409 | `no seats available` | The workspace has used all the seats of its Plan Tier. |
| 409 | `cannot remove the last admin` | Suspending, deleting or demoting the only active Admin. |
| 429 | `rate limit exceeded` | Too many requests in a short time; wait for `Retry-After`. |

A `409` for an existing address usually means the person was suspended earlier: reactivate them with `POST /users/{id}/reactivate` instead of inviting them again. Seat limits per tier are in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
