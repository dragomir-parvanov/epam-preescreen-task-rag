---
id: nimbus-api-invitations
title: Invitations API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-02-09
owner: Platform API Team
---

An invitation is how a person who isn't in a workspace yet gets an account there. Creating one emails the person a link; when they accept, Nimbus creates their user with the role chosen on the invitation. This resource lists, creates and revokes invitations, the same ones an Admin manages with **Invite users** under **Settings > Users**.

Authenticate with an API key in `Authorization: Bearer <api-key>`; the key acts as an Admin. Once accepted, the person is a user and is managed through the [Users API](nimbus-api-users.md) instead. For the console flow, see [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/invitations` | List invitations, pending ones first. |
| `POST` | `/invitations` | Invite one email address with a role; sends the invitation email. |
| `DELETE` | `/invitations/{id}` | Revoke a pending invitation so its link stops working. |

There is no endpoint to read a single invitation or to resend one. To resend, revoke the old invitation and create a new one for the same address; the new email carries a fresh link and a fresh expiry.

### Creating an invitation

`POST /invitations` takes `email` and an optional `role` (`admin`, `builder` or `viewer`). Without a role, the user joins as a Viewer. Nimbus emails a link of the form `https://app.nimbus.omnicorp.example/invite/<token>` and the invitation expires after 7 days. After that the link shows "This invitation has expired" and the invitation's status becomes `expired`. The email's subject reads "You've been invited to <workspace name> on OmniCorp Nimbus"; for invitations sent through the API it names the workspace as the sender rather than an Admin.

The address must not already belong to a user in the workspace, active or suspended, and must not have another pending invitation. Suspended people come back through reactivation, not a new invitation.

### Seat checks

An invited person takes a seat when they accept, not when they are invited, so pending invitations don't use seats. Nimbus checks seats twice:

1. On `POST /invitations`, the request is refused with `409 conflict` if every seat is already taken by active users.
2. On acceptance, Nimbus checks again. If the seats filled up in the meantime, the person sees "No seats available, ask your Admin" and the invitation stays `pending` until it expires or a seat frees up.

It is therefore possible to have more pending invitations than free seats; the first people to accept get the seats. Seat counting is explained in [Seat Limits and How Seats Are Counted](nimbus-tier-seat-limits.md).

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Invitation id, prefixed `inv_`. |
| `email` | string | The address the invitation was sent to, lower-cased. |
| `role` | string | Role the user gets on acceptance: `admin`, `builder` or `viewer`. |
| `status` | string | `pending`, `accepted`, `expired` or `revoked`. |
| `invited_by` | string | The `usr_` id of the inviting Admin, or the `key_` id when sent through the API. |
| `expires_at` | string | Seven days after `created_at`. |
| `accepted_at` | string or null | When the person accepted. |
| `user_id` | string or null | The `usr_` id created on acceptance. |
| `created_at` | string | When the invitation was sent. |

The invitation token itself is never returned by the API; it exists only in the email. An accepted invitation keeps its record, with `user_id` pointing to the new account, so the list also shows who invited whom and with which role. Expired and revoked invitations stay listed as well; they never hold a seat and can be left alone.

## Example request and response

```http
POST /invitations HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: onboarding-4471-jmorales

{
  "email": "j.morales@clientco.example",
  "role": "builder"
}
```

```json
{
  "id": "inv_90314",
  "email": "j.morales@clientco.example",
  "role": "builder",
  "status": "pending",
  "invited_by": "key_3307",
  "expires_at": "2026-02-13T10:05:41Z",
  "accepted_at": null,
  "user_id": null,
  "created_at": "2026-02-06T10:05:41Z"
}
```

The `Idempotency-Key` header matters here more than on most resources: an onboarding script that retries a timed-out request without it could send the person two emails. With the key, a repeat within 24 hours returns the same `inv_90314` and sends nothing.

Revoking is a bodiless `DELETE /invitations/inv_90314`, which answers `204 No Content`.

## Filtering and pagination

`GET /invitations` supports:

| Parameter | Values | Notes |
|---|---|---|
| `status` | `pending`, `accepted`, `expired`, `revoked` | Comma-separate to combine, e.g. `expired,revoked`. |
| `email` | an address | Exact, case-insensitive. |
| `role` | `admin`, `builder`, `viewer` | The role on the invitation. |
| `limit` | 1 to 100 | Page size, 25 by default. |
| `cursor` | from `next_cursor` | The page after the previous one. |

An onboarding check that finds every person who let their invitation lapse in a batch might run like this:

```bash
curl -s "https://api.nimbus.omnicorp.example/invitations?status=expired&limit=100" \
  -H "Authorization: Bearer <api-key>"
```

Then follow the cursor:

1. Read `data` from the first response and record each `email`.
2. If `next_cursor` is not null, request the same URL with `&cursor=<next_cursor>`.
3. Repeat until `next_cursor` is null.
4. Create a new invitation for each address that still needs access.

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `email` is missing or not a valid address, or `role` isn't one of the three roles. |
| 401 | `unauthorized` | No valid API key. |
| 404 | `not_found` | No invitation with that id in this workspace. |
| 409 | `conflict` | Every seat is taken; the message reads "No free seats in this workspace". |
| 409 | `conflict` | The email already belongs to a user, or already has a pending invitation. |
| 409 | `conflict` | `DELETE` on an invitation that was already accepted, expired or revoked. |
| 429 | `rate_limited` | Too many API calls; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |

Large onboarding batches are easier in the console's Invite users dialog than as one API call per address, because the dialog shows the seat count as it goes.
