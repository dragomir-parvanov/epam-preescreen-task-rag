---
id: nimbus-v2-connector-salesforce
title: Salesforce Connector (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: guide
status: deprecated
last_updated: 2025-03-10
owner: Integrations Team
---

The legacy Salesforce connector reads new and changed records from a Salesforce org and creates or updates records in it. It signs in with a Salesforce username, password and security token, checks for changes every 15 minutes, and offers two write actions: create record and update record.

This guide is for CSMs supporting workspaces that still run on the legacy platform. The current Salesforce connector, which signs in with OAuth 2.0 and has more actions, is described in [Salesforce Connector](nimbus-connector-salesforce.md); the wider support timeline is in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Prerequisites

- **A Salesforce integration user.** Ask the client for a dedicated user rather than a person's login. The connection stops working whenever that user's password changes, so a shared or personal account causes avoidable outages.
- **API access.** The user's profile or a permission set must grant **API Enabled**, plus read and edit on every object and field the workflows touch.
- **A password that doesn't expire.** Set **Password never expires** on the integration user's profile, or the client's password policy will break the connection on the expiry date.
- **The security token.** Salesforce emails it to the user when they choose **Reset My Security Token** under **Settings > My Personal Information**. A new token is also issued, and the old one stops working, whenever the password is changed.
- **An Admin** in the Nimbus workspace, because connections are managed under **Admin > Connections**.

The connector works with production orgs and with sandboxes. A sandbox user's username carries the sandbox name as a suffix, for example `integration@client.example.uat`.

## Creating the connection

1. In the Nimbus admin console, go to **Admin > Connections** and click **Add connection**.
2. Choose **Salesforce**.
3. Under **Login URL**, choose **Production** (`https://login.salesforce.com`) or **Sandbox** (`https://test.salesforce.com`).
4. Enter the **Username**, the **Password** and the **Security token** in their separate fields. Don't append the token to the password.
5. Click **Save**. Nimbus signs in once to check the credentials and lists the objects the user can see.

Credentials are stored on the connection itself. When the client changes the integration user's password or resets the token, an Admin opens **Admin > Connections**, selects the connection, clicks **Edit**, enters the new values and saves. Every workflow using that connection picks up the change on its next run; no workflow needs editing.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New record | Polling trigger | Starts one run per record of the chosen object whose `CreatedDate` is after the previous check. |
| Updated record | Polling trigger | Starts one run per record whose `LastModifiedDate` is after the previous check. |
| Create record | Action | Creates a record of the chosen object and returns its 18-character Id. |
| Update record | Action | Updates the mapped fields on a record identified by its Id. |

There is no upsert action and no SOQL query action. To update a record when only an external reference is known, a workflow has to find the Id some other way first, typically from a field stored on the triggering record. A workflow that must create the record if it doesn't exist has to keep track of the Ids it has created itself. Both of these are much simpler on the current connector, which is a common reason clients give for upgrading.

## Field mapping

Fields are addressed by their API names, not their labels: `AccountId`, `StageName`, and custom fields with the `__c` suffix, such as `Billing_Reference__c`. Lookup fields take the related record's Id. To set a record type, map `RecordTypeId` to the Id shown in Salesforce Setup under the object's **Record Types**.

An **Update record** step that closes an opportunity when an order is confirmed:

```json
{
  "object": "Opportunity",
  "id": "{{trigger.body.opportunity_id}}",
  "fields": {
    "StageName": "Closed Won",
    "CloseDate": "{{trigger.body.confirmed_on}}",
    "Billing_Reference__c": "{{steps.create_invoice.output.invoice_number}}"
  }
}
```

Dates go in as `YYYY-MM-DD` and date-times as ISO 8601 in UTC. Picklist fields accept the picklist value's API name; a value that isn't defined on the picklist is rejected by Salesforce if the picklist is restricted.

## Limits and behaviour

| Behaviour | Value |
|---|---|
| Polling interval | Every 15 minutes, for both triggers |
| Records per check | Up to 2,000; the rest are picked up at the next check |
| First check after activation | Records the starting point; existing records don't start runs |
| Records per write action | One |
| Run history | Kept for 30 days |

Because each check happens every 15 minutes, a change in Salesforce can take up to a quarter of an hour to start a run. A bulk data load of thousands of records spreads over several checks and starts one run per record.

Every call the connector makes counts against the org's daily API request allocation in Salesforce, which is shared with every other integration on the org. A client who hits that allocation sees steps fail until Salesforce resets it; the org's usage is shown in Salesforce Setup under **System Overview**.

A failed step isn't retried: the run fails at that step, and a Builder starts the workflow again by hand once the cause is fixed. Before rerunning a workflow whose **Create record** step failed, check in Salesforce that the record wasn't created anyway, or the rerun creates a duplicate.

## Troubleshooting

| Run history message | Cause in Salesforce | Fix |
|---|---|---|
| Connection authorization failed | The password was changed or expired, or the security token was reset. | Under **Admin > Connections**, edit the connection and enter the new password and token. |
| Permission denied by Salesforce | The user lacks **API Enabled** or access to the object or field. | Add the permission to the user's profile or a permission set. |
| Record not found | The record Id doesn't exist or was deleted, or the Id belongs to a different object. | Check the Id in the run history and the object chosen in the step. |
| Request limit exceeded | Salesforce refused the call because the org's API allocation is used up. | Wait for Salesforce to reset the allocation and reduce the connector's call volume. |
| Required field is empty | A required field, often the Id on **Update record**, resolved to empty. | Check the expression and the trigger output it reads from. |

Repeated authorization failures straight after a successful edit usually mean the token was reset again after it was copied. Reset it once more, copy the token from the newest email only, and update the connection.
