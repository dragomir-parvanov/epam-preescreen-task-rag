---
id: nimbus-connector-workday
title: Workday Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-31
owner: Integrations Team
---

The Workday connector, added in release 3.8.0, connects Nimbus to Workday Human Capital Management. It polls Workday for new hires, terminations and job changes, reads a worker's record, and updates work contact information. Its main use is joiner-mover-leaver workflows: creating accounts in other applications when someone is hired, changing their access when they move role, and removing it when they leave.

Nimbus authenticates with OAuth 2.0 through an API client registered in the client's Workday tenant. The client acts as an integration system user (ISU) whose security group decides exactly which workers and fields Nimbus can see.

## Prerequisites

The Workday side is set up by the client's Workday security administrator. Nimbus needs:

- **An integration system user**, created with the **Create Integration System User** task. Tick **Do Not Allow UI Sessions**, and exempt the account from password expiry in **Maintain Password Rules**, so the integration doesn't stop when a password ages out.
- **An integration system security group** (unconstrained, or constrained to the organisations Nimbus should see) containing the ISU, created with **Create Security Group**.
- **Domain security policy permissions** for that group, then **Activate Pending Security Policy Changes**:

| Domain | Access | Needed for |
|---|---|---|
| Worker Data: Public Worker Reports | Get | Read worker |
| Worker Data: Staffing Information | Get | Hire and job change triggers |
| Worker Data: Terminations | Get | Termination trigger |
| Person Data: Work Contact Information | Get and Put | Update contact information |

- **An API client** registered with **Register API Client for Integrations**, with the functional areas Staffing, Contact Information and Organizations and Roles, and a non-expiring refresh token generated for the ISU with **Manage Refresh Tokens for Integrations**.
- **A Builder or Admin role** in Nimbus. The connector is available on every Plan Tier.

## Creating the connection

1. In Workday, run **View API Clients** and note the **Workday REST API Endpoint**, the **Token Endpoint**, the client ID and the tenant name.
2. In Nimbus, go to **Connections > New connection** and select **Workday**.
3. Enter **Tenant name** and **Token endpoint** (for example `https://wd2-impl-services1.workday.com/ccx/oauth2/acme_prod/token`), and the **REST API endpoint** host.
4. Paste the **Client ID**, **Client secret** and **Refresh token**.
5. Click **Test connection**. Nimbus signs in as the ISU and reads one worker, so a missing domain permission shows up here rather than in the first run.
6. Click **Save**. The secret and the refresh token are encrypted and never shown again.

Use separate connections for implementation and production tenants, and promote workflows between Nimbus environments rather than editing the tenant on a live connection.

## Triggers and actions

| Name | Type | Starts or returns |
|---|---|---|
| New hire | Polling trigger | One run per completed Hire business process |
| Termination | Polling trigger | One run per completed Termination business process |
| Job change | Polling trigger | One run per completed Change Job business process (transfer, promotion, manager change) |
| Read worker | Action | Worker ID, legal and preferred name, position, supervisory organisation, manager, location, work email and phone |
| Update contact information | Action | Submits a change to work email or work phone; returns the business process event ID |

Update contact information starts Workday's own business process. If the client's Workday configuration routes that process for approval, the action returns once the event is submitted, with status `In Progress`, not when it is approved.

## Field mapping

Trigger output carries the worker and the business process: `{{trigger.body.worker.employee_id}}`, `{{trigger.body.worker.wid}}`, `{{trigger.body.event.effective_date}}`, `{{trigger.body.event.reason}}` and, for job changes, the before and after values under `{{trigger.body.change.previous}}` and `{{trigger.body.change.proposed}}`. A leaver workflow that tells the manager and queues the leaver for processing on their last day could start like this:

```yaml
- step: get_worker
  action: Read worker
  worker_id: "{{trigger.body.worker.employee_id}}"
- step: notify_manager
  action: Slack > Send direct message
  user_email: "{{lower(steps.get_worker.output.manager.work_email)}}"
  text: >-
    {{steps.get_worker.output.preferred_name}} leaves on
    {{trigger.body.event.effective_date}} (reason: {{default(trigger.body.event.reason, 'not given')}}).
- step: queue_leaver
  action: PostgreSQL > Insert row
  table: hr.pending_leavers
  values:
    wid: "{{trigger.body.worker.wid}}"
    effective_date: "{{trigger.body.event.effective_date}}"
```

Contingent workers have a contingent worker ID instead of an employee ID; Read worker accepts either, or the Workday ID (WID), which is the safest key to store in other systems.

## Limits and behaviour

The triggers poll Workday every 5 minutes and fire when a business process completes, not on its effective date. A termination entered on 3 March with an effective date of 31 March starts its run on 3 March. Workflows that should act on the last day record the `effective_date` somewhere durable, as the example above does, and a second workflow on a daily schedule processes the leavers due that day. Hires are often entered weeks ahead, so joiner workflows can provision accounts in advance and check the start date before granting access.

A business process that is rescinded after it completed doesn't start a new run and doesn't undo the earlier one. Add a Read worker step before any irreversible action, and check the worker's current status.

Each poll reads up to 100 events per page and follows all pages. Don't use a Delay step to wait for an effective date: a run still running after 60 minutes is stopped with WF-210. Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes; Workday rejects a duplicate contact change for the same value, so retries of Update contact information don't create a second change.

## Troubleshooting

| Code | Likely cause | Fix |
|---|---|---|
| CONN-401 | Refresh token regenerated or revoked, API client disabled, or ISU locked | Generate a new refresh token for the ISU and click **Reconnect**. |
| CONN-403 | The security group lacks a domain permission, or policy changes weren't activated | Add the permission and run **Activate Pending Security Policy Changes**. |
| CONN-404 | The worker ID doesn't exist, or is a contingent worker ID used as an employee ID | Use the WID or the right ID type. |
| CONN-503 | Workday is in its weekly maintenance window or the tenant is unavailable | No action; the step is retried. |
| WF-400 | A mapped field, often the work email of a new hire, is empty | Use `default()` or wait until the field is filled. |

For the BambooHR equivalent, see [BambooHR Connector](nimbus-connector-bamboohr.md).
