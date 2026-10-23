---
id: nimbus-connector-salesforce
title: Salesforce Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-16
owner: Integrations Team
---

The Salesforce connector lets a Nimbus workflow react to records that are created or changed in a Salesforce org and write records back to it. It connects with OAuth 2.0 to either a production org or a sandbox, and it has been part of the connector catalogue since 3.0.0.

A connection belongs to the workspace and acts as the Salesforce user who authorised it, so every record Nimbus creates shows that user as Created By. Most clients connect a dedicated integration user rather than a named person, so that workflows don't break when someone leaves.

## Prerequisites

Before creating the connection, check the following on both sides:

| Requirement | Where it is set | Notes |
|---|---|---|
| Salesforce edition with API access | Salesforce contract | Enterprise, Unlimited, Performance and Developer Editions include it; Professional Edition needs the API add-on. |
| **API Enabled** system permission | Profile or permission set of the connecting user | Without it, every call fails with `API_DISABLED_FOR_USER`. |
| Object and field permissions | Profile or permission set | Read for triggers; Create and Edit for the objects the workflow writes. Field-level security applies to every field mapped. |
| Nimbus role | Nimbus console | Builder or Admin, to create the connection. |
| Active connectors | Nimbus Plan Tier | The connector counts towards the workspace's active-connector limit once an active workflow uses it; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md). |

If the org restricts connected apps, a Salesforce administrator must first open **Setup > Apps > Connected Apps > Manage Connected Apps > OmniCorp Nimbus**, set **Permitted Users** to *Admin approved users are pre-authorized* and add the integration user's profile or permission set. Nimbus requests the OAuth scopes `api` and `refresh_token offline_access`; it never asks for `full`.

## Creating the connection

1. In the Nimbus console, open **Connections** and click **New connection**.
2. Search for **Salesforce** and select it.
3. Enter a **Connection name**, for example `Salesforce – Production`.
4. Under **Org type**, choose **Production** (signs in at login.salesforce.com) or **Sandbox** (signs in at test.salesforce.com). For an org with My Domain login enforced, enter the domain in **Custom login domain** instead, such as `acme.my.salesforce.com`.
5. Click **Authorise**. A Salesforce sign-in window opens; sign in as the integration user and click **Allow**.
6. Back in Nimbus, click **Test connection**. A successful test reads the org id and user name and shows them on the connection's details page with the status **Connected**.

A sandbox refresh issues new credentials for the sandbox, so connections to a refreshed sandbox have to be reconnected. Keep separate connections for production and sandbox orgs and pick the right one in each environment of the workflow.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New record | Polling trigger | Starts a run for each record of the chosen object created since the last poll, using `CreatedDate`. |
| New or updated record | Polling trigger | Starts a run for each record whose `SystemModstamp` changed since the last poll. An optional **Filter (SOQL WHERE)** narrows the records, e.g. `StageName = 'Closed Won'`. |
| Create record | Action | Inserts one record and returns its `Id`. |
| Update record | Action | Updates the record with the given `Id`; only mapped fields are changed. |
| Upsert record | Action | Matches on an external id field (`Nimbus_Id__c`, for example) and creates or updates the record. Returns `created: true` or `false`. |
| Run SOQL query | Action | Runs a SOQL query and returns `records` and `total_size`. |

Triggers and actions work on standard and custom objects alike. Custom objects and fields use their API names with the `__c` suffix.

## Field mapping

Map fields by API name, not label. Picklist fields take the picklist value's API name; for a restricted picklist, any other value is rejected by Salesforce. Lookup fields take the 18-character `Id` of the related record, or, on Upsert, a nested object that names the related object's external id field, so the workflow doesn't need a lookup query first.

```json
{
  "object": "Opportunity",
  "external_id_field": "Nimbus_Deal_Id__c",
  "external_id_value": "{{trigger.body.deal_id}}",
  "fields": {
    "Name": "{{trigger.body.deal_name}}",
    "StageName": "{{default(trigger.body.stage, 'Prospecting')}}",
    "CloseDate": "{{trigger.body.close_date}}",
    "LeadSource": "Partner Referral",
    "Account": { "ERP_Account_Number__c": "{{trigger.body.account_number}}" },
    "OwnerId": "{{steps.find_owner.output.records[0].Id}}"
  }
}
```

Date fields expect `YYYY-MM-DD`; datetime fields expect ISO 8601 in UTC. Multi-select picklists take the values joined with semicolons, as in `Email;Phone`. A required field that resolves to empty stops the step with WF-400 before anything is sent to Salesforce.

## Limits and behaviour

- **Polling.** Both triggers poll every 5 minutes. The first poll after a workflow is activated sets the starting point, so records that existed before activation don't start runs.
- **Paging.** A poll reads up to 2,000 changed records; anything beyond that is picked up by the following polls, oldest first. **Run SOQL query** follows Salesforce's `nextRecordsUrl` until it reaches the step's **Max records** setting (default 2,000, maximum 50,000).
- **Salesforce API allocation.** Every poll and every action uses Salesforce API calls from the org's rolling 24-hour allocation. A workflow with a 5-minute poll uses a small, steady share; large SOQL loops use far more. Check **Setup > System Overview** in Salesforce if calls start failing with `REQUEST_LIMIT_EXCEEDED`.
- **Files.** Attachments and Files (`ContentVersion`) can be passed between steps up to the Nimbus limit of 100 MB per file.
- **Retries.** A failed action is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Upsert is safe to retry; Create record is not, so set its retries to 0 where a duplicate would matter.

## Troubleshooting

| Code or message | Cause | Fix |
|---|---|---|
| CONN-401 | The refresh token was revoked, the integration user was frozen, or the connected app's session policy expired the token. | Click **Reconnect** on the connection and sign in again. Set the connected app's refresh token policy to *Refresh token is valid until revoked*. |
| CONN-403 (`API_DISABLED_FOR_USER`) | The connecting user lacks **API Enabled**. | Add the permission through a permission set, then click **Test connection**. |
| CONN-403 (`INSUFFICIENT_ACCESS_OR_READONLY`) | The user can't edit the object, record or a mapped field. | Check object permissions, sharing and field-level security. |
| CONN-404 (`ENTITY_IS_DELETED`, `NOT_FOUND`) | The record id no longer exists or was merged. | Look the record up again before updating it, or use Upsert. |
| CONN-429 (`REQUEST_LIMIT_EXCEEDED`) | The org has used its API allocation. | Nimbus backs off and retries the step; reduce SOQL loops or ask Salesforce for a larger allocation. |
| WF-400 | A mapped expression resolved to empty for a required field. | Fix the mapping or add `default()`. |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | A picklist got a label or an unknown value. | Map the picklist value's API name. |

Workspaces still on the legacy platform should use [Salesforce Connector (v2)](nimbus-v2-connector-salesforce.md) instead.
