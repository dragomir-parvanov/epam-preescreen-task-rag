---
id: nimbus-tier-seat-limits
title: Seat Limits and How Seats Are Counted
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-02
owner: Product Operations
---

A seat is what a person uses up by being an active member of a Nimbus workspace. The seat limit is the most visible of the Plan Tier limits, because hitting it stops a colleague from joining, and the questions it raises are nearly always about counting: does a Viewer need a seat, does an unanswered invitation hold one, does a suspended contractor still count?

This guide sets out the counting rules, what Admins and invitees see when the workspace is full, and how to check seat use before it becomes a problem.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Seats | Up to 10 | Up to 250 | Unlimited |
| Viewers take a seat | Yes | Yes | Yes |
| Pending invitations take a seat | No | No | No |
| Suspended users take a seat | No | No | No |
| Seat use on Settings > Usage | Yes | Yes | Yes |

The seat values are the Plan Tier entitlements; [Plan Tiers and Entitlements](nimbus-plan-tiers.md) is the reference for them and for contract overrides, which appear as **Custom** on **Settings > Plan**.

## How it works

Every active user takes one seat, whatever their role. An Admin, a Builder and a Viewer each count as one, and there is no cheaper or free role for people who only look at run history. A user who belongs to two workspaces takes a seat in each.

A person moves through these states, and only one of them holds a seat:

| User state | Takes a seat | Notes |
|---|---|---|
| Invited, not yet accepted | No | The invitation is emailed and expires after 7 days if nobody accepts it. |
| Active | Yes | From the moment the invitation is accepted or the account is created by sign-in. |
| Suspended | No | The account and its workflows are kept; the user can't sign in. |
| Deleted | No | The account is removed from the workspace. |

Accepting an invitation is what takes the seat, not sending it. An Admin can therefore have more open invitations than free seats; the seats are allocated in the order people accept. Users created on their first sign-in through [single sign-on](nimbus-sso-saml.md) take a seat at that first sign-in, exactly like an accepted invitation.

Suspending is the usual way to release a seat without losing anything. The suspended user's workflows keep running under their ownership until an Admin transfers them, which [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md) describes.

### When the workspace is full

When the number of active users equals the seat limit, Nimbus blocks everything that would add one more:

1. An invitee who opens a valid invitation link sees "This workspace has no free seats. Ask an Admin to free a seat, then open this link again." The invitation stays valid until it expires.
2. A first-time single sign-on user is refused with the same message and no account is created.
3. **Reactivate** on a suspended user is disabled in **Settings > Users**, with a tooltip naming the limit.
4. `POST /users/{id}/reactivate` returns `409 Conflict` with code `conflict` and the message "Seat limit reached".

Sending a new invitation is refused while active users fill every seat (`POST /invitations` answers `409 conflict`), but invitations sent earlier stay valid, and pending invitations never count towards the limit. Changing an existing user's role never needs a free seat.

## Turning it on

Seat counting is always on. To check seat use and free seats when a client is near the limit:

1. Go to **Settings > Usage** and read the **Seats** card, which shows active users against the limit and the number of open invitations.
2. Go to **Settings > Users** and filter **Status** to **Active**. Sort by **Last sign-in** to find people who haven't used the workspace recently.
3. Suspend the accounts that no longer need access. Each suspension frees a seat immediately.
4. Delete open invitations that will never be accepted from the **Invitations** tab, so the invitation count on the **Seats** card reflects real demand.
5. Ask the waiting colleague to open their invitation link again.

On workspaces with API access, an Admin can pull the same numbers to monitor them:

```bash
curl -s "https://api.nimbus.omnicorp.example/workspace/usage" \
  -H "Authorization: Bearer <api-key>"
# "seats": { "limit": 250, "used": 184, "pending_invitations": 12 }

curl -s "https://api.nimbus.omnicorp.example/users?status=active&limit=100" \
  -H "Authorization: Bearer <api-key>"
```

On Enterprise, `seats.limit` is `null`; the count is still returned.

## Limits

| Plan Tier | Seats | When the limit is reached |
|---|---|---|
| Starter | Up to 10 | Invitations can't be accepted and suspended users can't be reactivated |
| Business | Up to 250 | Same as Starter |
| Enterprise | Unlimited | Never reached |

Other numbers that come up alongside seats:

- Invitations expire after 7 days. An expired invitation can be resent from the **Invitations** tab.
- New users invited without a role get Viewer, and a Viewer still takes a seat.
- Service accounts don't exist in Nimbus: API keys act for the workspace, not for a user, so automation never needs a seat of its own.

Seats are counted continuously, not per month, so freeing a seat takes effect at once rather than at the next billing date.

## When the Plan Tier changes

An upgrade takes effect immediately. A Starter workspace moving to Business can accept waiting invitations and reactivate suspended users as soon as the change is applied.

A downgrade takes effect at the end of the current billing period, and the number of active users must already fit the new tier's limit by then; otherwise the downgrade is held. Nimbus doesn't pick who loses access. Before the date, agree with the client which users to suspend, and suspend them yourselves with the steps above. On Enterprise workspaces that provision users through SCIM, suspend them in the identity provider instead, because changes made directly in Nimbus are overwritten at the next sync (see [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md)).

After a downgrade, open invitations stay valid, but they can only be accepted while there is a free seat.
