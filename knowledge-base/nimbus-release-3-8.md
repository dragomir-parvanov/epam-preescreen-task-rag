---
id: nimbus-release-3-8
title: Nimbus 3.8 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2026-08-03
owner: Release Management
---

Nimbus 3.8.0 was released to every workspace on 2026-08-03. It introduces concurrent-run limits per Plan Tier, together with the new run notice WF-310, adds `POST /runs/{id}/retry` so integrations can retry a failed run the same way the Runs page does, and ships the Workday connector.

The release was rolled out without downtime and needs no action from most clients. Integrations that start many runs at once, or that watch run statuses closely, should read Deprecations and breaking changes before the first busy period after the rollout.

## Highlights

- **Concurrent-run limits.** Each workspace now runs at most 5, 25 or 100 workflow runs at the same time (Starter, Business, Enterprise). Runs above the limit wait as `queued` with the notice WF-310 instead of starting straight away.
- **Retry from the API.** `POST /runs/{id}/retry` starts a fresh attempt of a run that ended as `failed`, `timed_out` or `cancelled`.
- **Workday connector.** Connect a Workday tenant through an API client and an integration system user, and trigger workflows on new hires, terminations and job changes.

## New features

**Concurrent-run limits.** A run occupies a slot only while its status is `running`; a run in `waiting_for_approval` releases its slot until it resumes. The limit applies to the whole workspace, across every workflow and every trigger type: schedules, inbound webhook triggers, connector events and manual runs.

| Plan Tier | Runs at the same time | When the limit is reached |
|---|---|---|
| Starter | 5 | The new run is created as `queued` with WF-310 |
| Business | 25 | The new run is created as `queued` with WF-310 |
| Enterprise | 100 | The new run is created as `queued` with WF-310 |

WF-310 is a notice, not a failure. Queued runs start in the order they were created as soon as a slot frees up, and run history shows the notice on the run's first line so a CSM can tell a waiting run from a stuck one. A queued run counts against the monthly workflow run quota only when it starts, and the 60-minute run timeout (WF-210) also starts counting then, so time spent waiting never pushes a run towards `timed_out`. The limits per tier, and how to design workflows that stay under them, are covered in [Concurrent Run Limits](nimbus-tier-concurrent-runs.md).

**Retrying a run through the API.** `POST /runs/{id}/retry` is the API equivalent of the Retry button on the Runs page. It creates a new run that starts from the first step with the original trigger input, on the currently published version, and counts against the monthly run quota; the new run's `retry_of` field holds the id of the run it retries. Only runs whose status is `failed`, `timed_out` or `cancelled` can be retried; any other status returns `409` with the code `conflict`. The endpoint accepts an `Idempotency-Key` header, so a client that times out and sends the same request again gets the first retry back rather than a second one. The full request and response shapes are in [Runs API](nimbus-api-runs.md).

**Workday connector.** The connector authenticates with OAuth 2.0 through an API client registered in Workday (task *Register API Client for Integrations*) and runs as an integration system user that belongs to an integration system security group. The group needs Get access to the *Worker Data: Workers* and *Worker Data: Public Worker Reports* domains, and Put access to *Person Data: Work Contact Information* if workflows update contact details. Its triggers poll the tenant every 5 minutes for new hires, terminations and job changes; its actions are Get worker and Update work contact information. Setup steps are in [Workday Connector](nimbus-connector-workday.md).

## Improvements

- `GET /workspace/entitlements` returns a new `concurrent_runs` field with the workspace's limit.
- Settings > Usage shows how many runs are running and queued right now, next to the monthly run count.
- The Runs page has a **Queued** status filter, and queued runs show their position in the queue.
- `GET /runs` accepts `status=queued`, matching the new filter.
- A WF-100 error on a schedule trigger now names the part of the cron expression that failed to parse.
- Run history labels each connector-step retry with its attempt number, so the attempts after 30 seconds, 2 minutes and 10 minutes are easy to tell apart.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-6104 | A run started with `POST /workflows/{id}/runs` while the workflow was being published could run the previous version. |
| NIM-6117 | The date filter on the Runs page used the browser's time zone instead of the workspace time zone. |
| NIM-6122 | A loop step over an empty list failed with WF-400 instead of completing with no iterations. |
| NIM-6138 | The Salesforce polling trigger skipped records modified in the same second as the previous poll. |
| NIM-6150 | Run history CSV exports cut off step error messages longer than 1,000 characters. |
| NIM-6163 | The `connector.disconnected` webhook event was sent twice when two steps of one run failed with CONN-401. |

## Deprecations and breaking changes

No endpoint, field or event was removed, and existing workflows run unchanged. The one behaviour change is that a run which used to start immediately may now wait as `queued` when the workspace is at its concurrent-run limit:

- Integrations that start a run and treat it as stuck if it isn't `running` within a few seconds should accept `queued` as a normal, waiting state.
- Code that reads step errors from `GET /runs/{id}/steps` must not treat WF-310 as a failure; the run's final status is what decides success.
- Workspaces whose schedules all fire on the same minute (for example dozens of workflows at `0 2 * * *`) will see some runs queue. Nothing is lost, but end times move later.

## Upgrade notes

The release is already live, so these steps are about adapting integrations to it:

1. Check the workspace's limit with `GET /workspace/entitlements` and compare it with the peak number of runs seen in run history.
2. Update any monitoring that alerts on runs waiting in `queued`, and exclude WF-310 from failure counts.
3. Stagger schedules that start at the same minute, either in the builder or with `PUT /workflows/{id}/schedule`.
4. Replace hand-written "start the workflow again" logic with `POST /runs/{id}/retry`, sending an `Idempotency-Key` with each call.
5. To use Workday, register the API client and integration system user in Workday first, then add the connection under Connections.

A retry request and its response look like this:

```http
POST /runs/run_8Hk2Qx7LmP/retry HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Idempotency-Key: 5b7f0c1e-2d9a-4c55-9e1f-retry-8Hk2Qx7LmP

HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "id": "run_Q3nV9bT1sW",
  "workflow_id": "wf_4mR8cZ2pLd",
  "status": "queued",
  "retry_of": "run_8Hk2Qx7LmP",
  "created_at": "2026-08-04T09:12:44Z"
}
```

Staggering two nightly schedules by a few minutes is often enough to keep a Starter workspace under its limit:

```cron
# Before: both start at 02:00 workspace time
0 2 * * *
# After: invoice sync at 02:00, CRM export at 02:10
0 2 * * *
10 2 * * *
```
