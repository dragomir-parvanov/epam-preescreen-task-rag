---
id: nimbus-troubleshooting-inbound-triggers
title: Troubleshooting Inbound Webhook Triggers
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-30
owner: Support Engineering
---

An inbound webhook trigger gives a workflow its own URL, `https://hooks.nimbus.omnicorp.example/t/<trigger-token>`, that another system can call to start a run. A successful call is a `POST` with a JSON body of up to 1 MB, and Nimbus answers `202 Accepted` with the id of the new run. Any other answer means no run was started, and the sending system decides what happens next: some retry, many just log the error and drop the event.

This reference covers calls to a trigger URL that don't start runs. How to set up the trigger is in [Inbound Webhook Triggers](nimbus-api-inbound-webhook-triggers.md); events Nimbus sends out to the client are in [Troubleshooting Webhook Deliveries](nimbus-troubleshooting-webhook-deliveries.md).

## Symptoms

- The sending system (a form tool, an e-commerce platform, the client's own code) reports failed calls to the trigger URL with a status such as 400, 403, 404 or 409.
- The client says "we sent it but nothing happened", and there is no run for that time under **Runs**.
- Calls used to work and all started failing at the same moment, often right after someone edited the workflow.
- Only some calls fail, typically the larger ones or the ones from one particular sender.

## Common causes

**The token was regenerated.** The trigger panel in the builder has **Regenerate URL**, meant for a URL that has leaked. Regenerating issues a new token and invalidates the old one immediately, so every sender still using the old URL gets `404 Not Found`. The same 404 comes back when the workflow has been deleted, or when the sender has mistyped or truncated the token.

**The body is larger than 1 MB.** Nimbus rejects bodies over 1 MB with `400 Bad Request` and the code `invalid_request` before reading them. Senders that include attachments, base64-encoded images or a whole order history hit this.

**The body isn't valid JSON.** The trigger accepts only `application/json`. A form-encoded body, an XML payload, a trailing comma, or a JSON document sent without a `Content-Type: application/json` header is answered `400 Bad Request` with the code `invalid_request`.

**The workflow is inactive.** A trigger URL only starts runs while the workflow is active. A workflow that was deactivated, or that was saved but never activated, answers `409 Conflict` with the code `conflict`. Its URL stays the same, so it starts working again as soon as the workflow is activated.

**The monthly runs are used up.** When the workspace has used its workflow runs for the month, event-triggered runs are rejected with WF-300. The trigger URL answers `403 Forbidden` with the code `forbidden` and a message beginning `WF-300`, and keeps doing so until the quota resets on the 1st of the month (UTC) or the Plan Tier is upgraded.

## Diagnosing the problem

1. Get the exact status and body the sender received. If the sender's logs don't show them, reproduce the call with `curl` and a copy of the payload:

```bash
curl -i -X POST "https://hooks.nimbus.omnicorp.example/t/<trigger-token>" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json
```

A healthy trigger answers:

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{"run_id": "run_7M3P0Q2X", "status": "queued"}
```

2. Compare the URL the sender uses with the one in the builder's trigger panel (**Copy URL**). Ask whether anyone clicked **Regenerate URL**; the audit log records it under **Settings > Audit log** with the workflow's id.
3. Check the payload size with `wc -c payload.json`; anything over 1,048,576 bytes is too large.
4. Check that the payload parses with `python3 -m json.tool payload.json`, and that the sender sets `Content-Type: application/json`.
5. Check that the workflow is active: its row under **Workflows** shows *Active*, or `GET /workflows/{id}` returns `"status": "active"`.
6. Check the month's run usage under **Settings > Usage**, or with `GET /workspace/usage`.

## Error reference

| Status | `code` | Cause | Run started? |
|---|---|---|---|
| 202 Accepted | (none) | The call was accepted; the body holds `run_id`. | Yes |
| 400 Bad Request | `invalid_request` | The body is larger than 1 MB, isn't valid JSON or isn't sent as `application/json`. | No |
| 403 Forbidden | `forbidden`, message `WF-300` | The workspace has used its monthly workflow runs. | No |
| 404 Not Found | `not_found` | The token is wrong or was regenerated, or the workflow was deleted. | No |
| 409 Conflict | `conflict` | The workflow isn't active. | No |

A `202 Accepted` means the run was created, not that it succeeded. If the run exists but fails, continue with [Troubleshooting Failed Workflow Runs](nimbus-troubleshooting-failed-runs.md).

## Fixes

- **New token:** update every sender with the URL from **Copy URL**. Treat the token like a password: regenerate it only when it has leaked, and list the senders to update before doing so.
- **Wrong or deleted workflow:** if the workflow was deleted, the old URL can't be restored. Build or restore the workflow, then give senders its new URL.
- **Payload over 1 MB:** send a reference instead of the content, for example the order id or the key of a file in Amazon S3, and fetch the full record or file in the first step of the workflow. Files passed between steps can be up to 100 MB.
- **Invalid JSON:** fix the sender's serialisation and set `Content-Type: application/json`. Senders that can only post forms need a small relay that converts the body to JSON.
- **Inactive workflow:** activate it under **Workflows**, or with `POST /workflows/{id}/activate`.
- **WF-300:** see [Troubleshooting Run Quota Errors](nimbus-troubleshooting-run-quota.md). Calls rejected at the quota are not queued; the sender has to send them again after the reset or upgrade.

In every case, Nimbus doesn't keep calls it rejected, so ask the client which events need to be re-sent once the trigger works again.

## Escalating to support

Escalate when a call gets a 5xx answer, or when a `202 Accepted` returns a `run_id` that never appears under **Runs**. Collect:

- the workflow id (`wf_...`) and the trigger URL with all but the last four characters of the token masked;
- the timestamps of failing calls in UTC, the status and full response body the sender received, and any `run_id`;
- the payload size and a redacted sample of the payload;
- the name of the sending system and whether it retries.
