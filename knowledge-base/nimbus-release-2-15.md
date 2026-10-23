---
id: nimbus-release-2-15
title: Nimbus 2.15 Release Notes
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: release-notes
status: deprecated
last_updated: 2024-06-10
owner: Release Management
---

Nimbus 2.15.0 was released on 2024-06-10 and applied to all workspaces during the scheduled maintenance window that evening. It adds a CSV export to run history, reworks the BambooHR connector around custom fields, and tightens validation of page-based pagination in the API.

Most clients need to do nothing. API integrations that request `page=0` should be checked before their next run; see Deprecations and breaking changes.

## Highlights

1. Run history can be exported as a CSV file from the Runs page, with the same filters as the on-screen list.
2. The BambooHR connector reads and writes custom fields, and its new **Employee changed** trigger fires only when the fields a workflow cares about change.
3. `GET /runs` gains `status`, `from` and `to` filters, so integrations no longer page through every run to find the failures.
4. List endpoints reject `page=0` and `per_page` values above 100 with HTTP 400 instead of quietly adjusting them.

## New features

### Run history CSV export

The Runs page has a new **Export CSV** button above the list. The export contains every run that matches the current filters (workflow, status and date range), not just the page on screen, and covers the full 30 days of run history the platform keeps. Each row is one run, with these columns:

| Column | Content |
|---|---|
| run_id | The run's id |
| workflow | Workflow name at the time of the run |
| status | succeeded, failed or running |
| started_at, finished_at | ISO 8601 timestamps in UTC |
| trigger | schedule, event or manual |
| error | The plain-text error message of the failed step, if any |

Exports with more than 50,000 runs are refused with a message asking for a narrower date range. Builders and Admins can export; Viewers see the button greyed out. The file is generated in the browser session and isn't stored on the platform afterwards.

### BambooHR connector

The connector still authenticates with an API key from a BambooHR user and the company subdomain, so existing connections under Admin > Connections keep working without being edited. What changed:

- **Custom fields.** The field picker lists the company's custom fields by their BambooHR alias as well as their numeric id, and the Get employee and Update employee actions read and write them.
- **Employee changed trigger.** The trigger polls BambooHR every 15 minutes and starts a run only when one of the fields selected in the trigger settings has changed. Leaving the selection empty watches every field, which is how the old **Employee updated** trigger behaved.
- **Add time-off request.** A new action creates a time-off request for an employee with a type, a start date, an end date and an optional note.

## Improvements

- Admin > Users can be sorted by role and by the date a user joined.
- The workflow builder warns before a step is deleted if a later step refers to its output.
- Failed-run notification emails include a direct link to the run instead of the workflow.
- Admin > Webhooks shows the time of each endpoint's last delivery attempt, labelled with the time zone.
- The Salesforce connector's field picker loads large objects such as Opportunity noticeably faster, because field metadata is cached for the session.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-2412 | Schedules set to run on day 31 of the month skipped months with fewer days instead of running on the last day. |
| NIM-2419 | Searching Admin > Users treated uppercase letters in email addresses as different from lowercase. |
| NIM-2427 | The Slack connector posted ampersands as `&amp;` in message text. |
| NIM-2433 | BambooHR dates were returned in the company's time zone without an offset, so some hire dates appeared a day early. |
| NIM-2440 | `GET /workflows?page=0` returned the first page instead of an error. |
| NIM-2446 | Deleting a connection that an inactive workflow still used left the workflow unable to open in the builder. |

## Deprecations and breaking changes

One API behaviour changes. List endpoints such as `GET /workflows`, `GET /runs` and `GET /users` validate their pagination parameters strictly (fix NIM-2440):

- `page` starts at 1. `page=0` or a negative value now returns HTTP 400 instead of the first page.
- `per_page` defaults to 50 and allows at most 100. A larger value now returns HTTP 400 instead of being capped silently.

The error body follows the usual format, a single message with the HTTP status:

```json
{"error": "page must be 1 or greater"}
```

The BambooHR **Employee updated** trigger is deprecated. Existing workflows that use it keep running and are not migrated automatically; new workflows can only choose **Employee changed**. No date has been set for removing the old trigger.

## Upgrade notes

1. Search integration code for `page=0` and for `per_page` values above 100, and correct them before the integration's next scheduled run.
2. Where an integration pulls every run to find failures, switch it to the new filters, as in the example below, and page with `total` to know when to stop.
3. For BambooHR workflows that react to employee updates, open each one in the builder, replace **Employee updated** with **Employee changed** and select the fields that matter, so runs aren't started by unrelated edits.
4. Ask Builders who keep manual run reports to use **Export CSV** on the Runs page instead of copying rows by hand.

The filtered runs request and the shape of its response:

```http
GET /runs?status=failed&from=2024-06-03T00:00:00Z&to=2024-06-10T00:00:00Z&page=1&per_page=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {"id": "run_51842", "workflow_id": "wf_2207", "status": "failed", "started_at": "2024-06-07T04:00:02Z"}
  ],
  "page": 1,
  "per_page": 100,
  "total": 1
}
```

Related reading: [Runs API (v2)](nimbus-v2-api-runs.md) for the full list of run fields, and [Troubleshooting Workflow Runs (v2)](nimbus-v2-troubleshooting-workflow-runs.md) for reading failed runs.
