---
id: nimbus-admin-exporting-the-audit-log
title: Searching and Exporting the Audit Log
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-29
owner: Workspace Administration Team
---

The audit log records who did what in a workspace: sign-ins, role changes, new API keys, edited workflows, changed security settings. Admins search it under **Settings > Audit log** and export what they find as CSV, and the same events are available from `GET /audit-log/events` for clients who want to pull them into their own tools.

How far back the log goes depends on the workspace's Plan Tier. This guide doesn't repeat those periods; check [Plan Tiers and Entitlements](nimbus-plan-tiers.md) before promising a client a particular range.

## Before you begin

- **Role:** Admin. Builders and Viewers don't see **Settings > Audit log**, and the API endpoint needs an API key, which only Admins can create.
- **Plan Tier:** every tier has the audit log and CSV export. Continuous streaming to Splunk, Datadog or an HTTPS endpoint, under **Settings > Audit log > Streaming**, is Enterprise only.
- **An API key**, if you'll use the API or schedule exports. See [Creating and Rotating API Keys](nimbus-admin-api-keys.md).
- **The client's question, made concrete.** Auditors usually ask something like "every role change in Q2" or "everything a departed employee did in their last week". Knowing the actor, action and range up front saves several searches.

## How it works

Every event has the same shape, whether it is seen in the console, in a CSV export or in the API:

| Field | Example | Meaning |
|---|---|---|
| `id` | `evt_7Xc2Lp9q` | Unique event id. |
| `occurred_at` | `2026-06-15T13:04:27Z` | When it happened, ISO 8601 in UTC. |
| `actor.type` | `user`, `api_key` or `system` | Who acted. `system` covers actions Nimbus takes itself, such as provisioning. |
| `actor.id` | `usr_2Lw7eT5d` or `key_5Rm1aZ8n` | The user or API key. |
| `actor.email` | `a.ferreira@client.example` | Present when the actor is a user. |
| `action` | `user.role_changed` | What was done, as `<area>.<past_tense>`. |
| `target.type`, `target.id` | `user`, `usr_8Pz4tG1k` | What it was done to. |
| `details` | `{"previous_role": "viewer", "new_role": "admin"}` | Before and after values where they apply. |

Common actions include `user.invited`, `user.role_changed`, `user.suspended`, `auth.sign_in_succeeded`, `auth.sign_in_failed`, `api_key.created`, `api_key.revoked`, `workflow.published`, `workflow.promoted`, `webhook_endpoint.created` and `sso.configuration_updated`. The **Action** filter in the console lists them all.

Events are written within a few seconds of the action and can't be edited or deleted by anyone in the workspace, Admins included. When an event passes the retention period for the workspace's tier, Nimbus removes it automatically. A downgrade to a tier with a shorter period removes the older events when the downgrade takes effect, which is a good reason to export before downgrading.

## Step-by-step

To search and export in the console:

1. Go to **Settings > Audit log**.
2. Set **Actor** to one or more users or API keys, or leave it empty for everyone.
3. Set **Action** to the actions you need. Typing `role` narrows the list to role-related actions.
4. Set **From** and **To**. The pickers use the workspace time zone; the export converts to UTC.
5. Click **Search**. Click any row to see the full event, including `details`.
6. Click **Export CSV**. The file contains every event matching the filters, not only the page on screen, with one row per event and the fields above as columns (`details` as a JSON string).

The same search through the API, page by page:

```bash
curl -s "https://api.nimbus.omnicorp.example/audit-log/events?action=user.role_changed&from=2026-04-01T00:00:00Z&to=2026-07-01T00:00:00Z&limit=100" \
  -H "Authorization: Bearer <api-key>"
```

The response is `{"data": [...], "next_cursor": "..."}`. Repeat the request with `cursor=<next_cursor>` until `next_cursor` is `null`. The `actor` filter takes a user or API key id, such as `actor=usr_2Lw7eT5d`.

### Scheduling regular exports

There is no built-in scheduled export. Clients who want a standing copy outside Nimbus have two options:

1. **On Enterprise**, turn on streaming under **Settings > Audit log > Streaming**, which sends each event to Splunk, Datadog or an HTTPS endpoint as it happens.
2. **On any tier with API access**, build a workflow with a schedule trigger such as `0 3 * * *` (every night at 03:00 in the workspace time zone). An [HTTP Request Connector](nimbus-connector-http-request.md) step calls `GET /audit-log/events` with `from` set to the previous run's time, a loop follows `next_cursor`, and an [Amazon S3 Connector](nimbus-connector-amazon-s3.md) or [SFTP Connector](nimbus-connector-sftp.md) step writes the file. Store the API key with `{{secrets.NIMBUS_AUDIT_KEY}}`, never in the step itself.

## Verifying the change

For a one-off export, open the CSV and compare its row count with the total shown above the results in **Settings > Audit log**. Spot-check one row against the console's event detail; `occurred_at` should match once converted from UTC to the workspace time zone.

For a scheduled export, check after its first night:

- The workflow's run on **Runs** has status `succeeded` and its loop ran as many times as there were pages.
- The file in the client's bucket or SFTP folder has events up to the run's start time.
- Reading the log isn't itself recorded as an action, so the export workflow's API key won't appear as an actor in the results.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Older events the client expects aren't there | They are past the tier's retention period, or were removed by a downgrade | Nothing can bring them back. Set up a regular export so it doesn't recur. |
| The CSV has fewer rows than expected | The **Actor** filter is still set from a previous search | Clear all filters and search again. |
| Times in the CSV look an hour or more out | The CSV is in UTC; the console shows the workspace time zone | Convert, or compare in UTC. |
| `GET /audit-log/events` returns 403 | The workspace's Plan Tier doesn't include API access | Use **Export CSV** in the console instead. |
| The API returns 400 `invalid_request` | `from` or `to` isn't ISO 8601, or `limit` is over 100 | Use timestamps like `2026-04-01T00:00:00Z` and `limit=100` or less. |
| No **Streaming** tab | Streaming needs Enterprise | Use a scheduled export workflow. |
