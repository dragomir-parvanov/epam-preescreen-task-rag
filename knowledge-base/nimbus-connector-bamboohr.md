---
id: nimbus-connector-bamboohr
title: BambooHR Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-07-21
owner: Integrations Team
---

The BambooHR connector lets a workflow read and update employee records in a client's BambooHR account and file time-off requests on an employee's behalf. Typical uses are onboarding flows that start when HR adds a new hire, and syncs that push job title or department changes from BambooHR into other systems.

The connector authenticates with a BambooHR API key and watches for changes by polling. It doesn't receive push events, so a change made in BambooHR reaches the workflow on the next poll rather than instantly.

## Prerequisites

Check these with the client before anyone opens the connection form:

- **A BambooHR user to own the API key.** The key acts with exactly the access level of the user who generated it. Ask the client to create a dedicated integration user (for example `nimbus-integration@client.example`) rather than using an HR administrator's personal account, so the connection doesn't break when that person leaves.
- **An access level that covers the fields the workflow touches.** The integration user's access level must be able to view every field the workflow reads and edit every field it writes. Time-off requests also need permission to request time off for other employees.
- **The company subdomain.** This is the first part of the client's BambooHR address: for `https://acme.bamboohr.com` the subdomain is `acme`.
- **A Builder or Admin role in Nimbus** for the person creating the connection.
- **Room in the Plan Tier.** A connection counts towards active connectors once an active workflow uses it. Starter workspaces are limited to 5 active connectors and Business to 50; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Creating the connection

The API key is generated in BambooHR first, then pasted into Nimbus.

1. Sign in to BambooHR as the integration user.
2. Open the user menu (the name in the top-right corner) and choose **API Keys**.
3. Click **Add New Key**, name it `OmniCorp Nimbus`, and click **Generate Key**. Copy the key; BambooHR doesn't show it again.
4. In the Nimbus admin console, go to **Connections** and click **New connection**.
5. Choose **BambooHR** from the catalogue.
6. Enter a connection name, the **Company subdomain** and the **API key**.
7. Click **Save and test**. Nimbus reads the company's field list to confirm that the key and subdomain match.

Once saved, the API key is encrypted and never shown again. To rotate it, generate a new key in BambooHR, open the connection, click **Edit credentials**, paste the new key and save; then delete the old key in BambooHR.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New employee | Polling trigger | Starts a run for each employee record created since the last poll. Output: `employeeId`, the requested fields and `created`. |
| Employee fields changed | Polling trigger | Starts a run when any of the watched fields changes on an employee. Output: `employeeId`, `changedFields` and the new values. |
| Get employee | Action | Returns the fields you list for one employee id. |
| Update employee | Action | Writes the mapped fields on one employee record. Fields you don't map are left as they are. |
| Add time-off request | Action | Creates a request for an employee with a time-off type id, start date, end date, amount and status (`requested` or `approved`). |

The **Employee fields changed** trigger needs a list of watched fields. Leaving the list empty is rejected when the workflow is activated with WF-100, because the trigger would otherwise fire on every edit in the account.

Table fields, such as the job information and compensation history tables, aren't written by **Update employee**. When a client needs to add a row to one of those tables, use the [HTTP Request Connector](nimbus-connector-http-request.md) with the same API key.

## Field mapping

BambooHR identifies standard fields by an alias such as `firstName`, `workEmail`, `jobTitle`, `department` or `hireDate`. Custom fields that the client has added have no alias and are addressed by their numeric field id instead, for example `4047`. In the step editor both appear in the field picker, with custom fields listed as the field's label followed by its id in brackets. In expressions and raw JSON, use the alias or the id as the key.

This **Update employee** step copies an employee's new department from a Jira Cloud ticket and stamps a custom "Onboarding status" field (id `4047`):

```json
{
  "employeeId": "{{trigger.body.employee_id}}",
  "fields": {
    "department": "{{steps.get_ticket.output.fields.customfield_10071}}",
    "jobTitle": "{{default(steps.get_ticket.output.fields.summary, 'New starter')}}",
    "4047": "Equipment ordered"
  }
}
```

Dates are written as `YYYY-MM-DD`. List fields such as `department` and `division` accept only values that already exist in the BambooHR list; a value that doesn't match an existing option is rejected by BambooHR and the step fails with WF-400. Aliases are case-sensitive: `workemail` is not the same field as `workEmail`.

## Limits and behaviour

- **Polling.** Both triggers poll every 5 minutes. The first poll after activation records a starting point and doesn't replay employees created or changed before the workflow was switched on.
- **Batching.** Each poll processes up to 500 changed employees, one run per employee. Anything beyond that is picked up by the next poll, so a bulk import in BambooHR is worked through over several polling cycles.
- **Run quota.** Every run started by a trigger counts towards the workspace's monthly workflow runs. A mass update of a few thousand employee records can use a noticeable share of a Starter workspace's 5,000 runs.
- **Files.** The connector doesn't transfer employee documents. A file passed between steps from another connector can be up to 100 MB.
- **Retries.** A failed step is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. The retry count can be set from 0 to 5 per step. When BambooHR throttles the connector, Nimbus waits for the period BambooHR asks for before retrying.

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| CONN-401 | The API key was deleted in BambooHR, or the integration user was disabled. | Generate a new key as the integration user and click **Reconnect** on the connection. |
| CONN-403 | The integration user's access level can't view or edit the field, or can't request time off for others. | Widen the access level in BambooHR under **Settings > Access Levels**. |
| CONN-404 | The employee id doesn't exist, or the subdomain points at a different company. | Check the id in the trigger output and the subdomain on the connection. |
| CONN-429 | BambooHR throttled the connector. | No action; Nimbus backs off and retries the step. Spread large updates over time if it recurs. |
| WF-400 | A mapped field resolved to empty, or a list field value doesn't exist in BambooHR. | Check the expression in the step and the options in the BambooHR list field. |
| WF-100 | **Employee fields changed** has no watched fields. | Add at least one field alias or id to the trigger. |

When a connection shows **Needs attention**, its steps fail with CONN-401 until someone reconnects it, and Nimbus sends the `connector.disconnected` webhook event to any endpoint subscribed to it.
