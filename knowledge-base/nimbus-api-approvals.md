---
id: nimbus-api-approvals
title: Approvals API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-01-26
owner: Platform API Team
---

An approval step pauses a run until a person says yes or no, for example before a workflow issues a refund in NetSuite or grants access in Jira Cloud. While it waits, the run has the status `waiting_for_approval` and an approval object appears in the console under **Approvals** and in this API. The Approvals API lets a client list those approvals and decide them from its own tools, such as an internal portal or a chat bot, instead of the Nimbus inbox.

Approval steps were added in release 3.3.0 and are part of the Business and Enterprise tiers; see [Approval Steps](nimbus-tier-approval-steps.md). How to add one to a workflow and choose its approvers is covered in [Adding Approval Steps to a Workflow](nimbus-admin-approval-steps.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/approvals` | List approvals, pending ones by default. |
| `POST` | `/approvals/{id}/approve` | Approve; the run continues with the next step. |
| `POST` | `/approvals/{id}/reject` | Reject; the run stops with status `failed`. |

There is no endpoint to create an approval: approvals are created only by a run reaching an approval step. To read one approval, filter the list by `run_id`.

### Approving and rejecting

Both decision endpoints take an optional JSON body with a `comment` of up to 1,000 characters. A comment is optional when approving and required when rejecting, so the Builder who owns the workflow can see why it stopped. The comment is stored on the approval, shown in the run's step log, and available to later steps as `{{steps.<step-key>.output.comment}}`.

An API key acts with Admin permissions, so it can decide any approval in its workspace, not only those whose `approvers` list includes a particular user. The decision is recorded with the key's id in `decided_by` and in the audit log. Clients that decide on behalf of a person should put that person's name in the comment. Both endpoints accept an `Idempotency-Key` header, which makes a retried decision safe.

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Approval id, prefixed `apr_`. |
| `status` | string | `pending`, `approved`, `rejected` or `expired`. |
| `run_id` | string | The waiting run (`run_`). |
| `workflow_id` | string | The workflow the run belongs to (`wf_`). |
| `step_key` | string | The key of the approval step inside the workflow. |
| `title` | string | The step's heading, with expressions already resolved, e.g. "Refund 1,240.00 for order 55871". |
| `details` | string | The longer message the step shows approvers, resolved for this run. |
| `approvers` | array of strings | User ids (`usr_`) allowed to decide in the console. |
| `requested_at` | string | When the run reached the step (ISO 8601, UTC). |
| `expires_at` | string | `requested_at` plus 7 days. |
| `decided_at` | string or null | When the decision was made; `null` while pending. |
| `decided_by` | string or null | `usr_` id for a console decision, `key_` id for an API decision. |
| `comment` | string or null | The approver's comment. |

An approval that nobody decides before `expires_at` becomes `expired` and the run fails with WF-410. Time spent waiting doesn't count towards the 60-minute run timeout, which applies only while the run is executing steps.

## Example request and response

Approve a refund from an internal finance portal:

```http
POST /approvals/apr_4Xc81LmQ/approve HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: fin-portal-apr_4Xc81LmQ

{
  "comment": "Approved by R. Okafor (Finance) via refund portal"
}
```

```json
{
  "id": "apr_4Xc81LmQ",
  "status": "approved",
  "run_id": "run_7Ld3kE2s",
  "workflow_id": "wf_1Bv6pH9t",
  "step_key": "approve_refund",
  "title": "Refund 1,240.00 for order 55871",
  "details": "Customer reports a damaged shipment. Zendesk ticket 88214.",
  "approvers": ["usr_6Tq2", "usr_9Hn5"],
  "requested_at": "2026-01-22T08:15:40Z",
  "expires_at": "2026-01-29T08:15:40Z",
  "decided_at": "2026-01-22T09:03:12Z",
  "decided_by": "key_3mT8bQ1x",
  "comment": "Approved by R. Okafor (Finance) via refund portal"
}
```

The response is returned once the decision is stored. The run itself resumes asynchronously; poll `GET /runs/{id}` or subscribe to the `workflow.run.completed` and `workflow.run.failed` webhook events to learn the outcome.

## Filtering and pagination

`GET /approvals` is cursor-paginated (`limit` default 25, maximum 100; `cursor` from `next_cursor`) and sorted by `expires_at`, soonest first, so the most urgent approvals come first. Filters:

| Parameter | Effect |
|---|---|
| `status` | `pending` (default), `approved`, `rejected`, `expired` or `all`. |
| `workflow_id` | Only approvals from one workflow. |
| `run_id` | The approval for one run. |
| `approver` | Only approvals where this `usr_` id is in `approvers`. |
| `expires_before` | ISO 8601 timestamp; useful for reminder jobs. |

A reminder job that nudges approvers a day before expiry would:

1. Compute a timestamp 24 hours from now, in UTC.
2. Call `GET /approvals?status=pending&expires_before=<timestamp>&limit=100`.
3. Send each approver in `approvers` a reminder with the `title` and a link to the Approvals inbox.
4. If `next_cursor` is not `null`, call the same URL with `cursor=<next_cursor>` and repeat step 3; stop when it is `null`.

## Errors

The envelope is `{"error": {"code": "...", "message": "..."}}`, described in [API Error Format and Idempotency](nimbus-api-error-format.md).

| HTTP status | Code | When it happens |
|---|---|---|
| 400 | `invalid_request` | `reject` sent without a `comment`, a comment over 1,000 characters, or an unknown `status` filter value. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 403 | `forbidden` | The workspace's Plan Tier doesn't include approval steps. |
| 404 | `not_found` | No approval with that `apr_` id in the workspace. |
| 409 | `conflict` | The approval is already `approved`, `rejected` or `expired`; the message says which and when. |
| 429 | `rate_limited` | The workspace is over its API rate limit. |
| 500 | `internal_error` | Internal error; retry with the same `Idempotency-Key`. |

A `409` on a decision is normal when two people act at once, for example one in the console and one through the portal. The first decision wins; read the approval again to show the user what happened.
