---
id: nimbus-connector-dynamics-365
title: Microsoft Dynamics 365 Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-10-12
owner: Integrations Team
---

The Microsoft Dynamics 365 connector, new in release 3.9.0, reads and writes rows in the Dataverse tables behind Dynamics 365 Sales, Customer Service and other model-driven apps. A workflow can start when an account, contact, opportunity or case is created or changed, and can create, update or upsert rows in any standard or custom table the connection can reach.

The connector signs in as an application user, not as a person. That takes two pieces of setup on the Microsoft side: an app registration in Microsoft Entra ID, and an application user in the Dataverse environment with a security role.

## Prerequisites

| Requirement | Who sets it up | Where |
|---|---|---|
| App registration with a client secret | Microsoft Entra ID administrator | Microsoft Entra admin center > App registrations |
| Application user linked to the app registration | Power Platform administrator | Power Platform admin center > Environments > *environment* > Settings > Users + permissions > Application users |
| A security role on the application user | Power Platform administrator | The same page, **Edit security roles** |
| The environment URL | Either | Power Platform admin center, environment details, e.g. `https://contoso.crm4.dynamics.com` |
| Builder or Admin role in Nimbus | Nimbus Admin | Settings > Users |

Give the application user a custom security role that grants only the tables the workflows need, with **Organization** depth for read and the write privileges required. The built-in **System Administrator** role works but gives the connection far more access than any workflow should have. The connector also counts towards the workspace's active connectors; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## Creating the connection

1. In the Microsoft Entra admin center, open **App registrations > New registration**, name it `OmniCorp Nimbus – Dynamics`, choose **Accounts in this organizational directory only**, and register it.
2. Under **Certificates & secrets**, create a client secret and copy its **Value**. Note the expiry date the administrator chose. No API permissions or admin consent are needed: Dataverse grants access through the application user's security role, not through Microsoft Entra ID permissions.
3. In the Power Platform admin center, open the environment, go to **Application users > New app user**, pick the app registration, select the business unit and assign the security role.
4. In the Nimbus admin console, go to **Connections > New connection** and choose **Microsoft Dynamics 365**.
5. Enter the **Environment URL**, the **Directory (tenant) ID**, the **Application (client) ID** and the **Client secret**.
6. Click **Save and test**. Nimbus requests a token from Microsoft Entra ID and calls `WhoAmI` against the environment to confirm the application user exists.

Each Dataverse environment needs its own connection. A client with separate development and production environments in Power Platform can map them to the Development and Production environments of their Nimbus workflows.

## Triggers and actions

| Name | Type | Notes |
|---|---|---|
| New row | Polling trigger | Starts a run for each row whose `createdon` is later than the last poll. |
| Updated row | Polling trigger | Starts a run for each row whose `modifiedon` is later than the last poll. Optionally limited to changes in selected columns. |
| Create row | Action | Creates a row in the chosen table and returns its GUID. |
| Update row | Action | Updates the mapped columns of a row identified by GUID. |
| Upsert row | Action | Updates the row matched by an alternate key, or creates it if no row matches. |

**Upsert row** needs an alternate key defined on the table in Power Apps (**Tables > *table* > Keys**), for example `new_erpcustomerid` on `account`. Without one, the table doesn't appear in the action's table picker. Both triggers accept an optional OData filter, such as `statecode eq 0`, to skip inactive rows.

## Field mapping

Dataverse shows display names in its apps ("Account Name", "Main Phone") but the connector works with logical names: `name`, `telephone1`, `emailaddress1`, and custom columns with the publisher prefix, such as `new_erpcustomerid`. The step editor's column picker shows the display name with the logical name beneath it; always use the logical name in expressions and raw JSON.

Lookup columns are the main difference from other CRM connectors. A lookup is set by binding to the related row with the table's entity set name (usually the plural logical name) and the row's GUID:

```json
{
  "table": "contact",
  "alternateKey": { "new_externalref": "{{trigger.body.person.id}}" },
  "columns": {
    "firstname": "{{trigger.body.person.given_name}}",
    "lastname": "{{trigger.body.person.family_name}}",
    "emailaddress1": "{{lower(trigger.body.person.email)}}",
    "parentcustomerid_account@odata.bind": "/accounts({{steps.upsert_account.output.id}})",
    "preferredcontactmethodcode": 2
  }
}
```

Choice columns such as `preferredcontactmethodcode` take the option's integer value, not its label. The values are listed in Power Apps under the column's **Choices** settings.

## Limits and behaviour

Both triggers poll every 5 minutes. Each poll reads changed rows in pages of 500 and starts one run per row; a poll that finds more than 5,000 rows continues from where it stopped on the next poll. The first poll after activation only records the starting time.

Dataverse applies service protection limits per application user. When the connection exceeds them, Dataverse asks the caller to wait and the step reports CONN-429; Nimbus backs off and retries it. A bulk update of thousands of rows in Dynamics will therefore start many runs over several polls, each counting towards the monthly workflow runs. Narrow **Updated row** to the columns that matter to avoid runs for irrelevant edits, such as a change of owner.

Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. File and image columns aren't written by this connector.

The client secret has an expiry date set in Microsoft Entra ID. When it expires, every step fails with CONN-401 and the connection shows **Needs attention**. Ask the client to diarise the expiry and to store a new secret on the connection before the old one lapses, using **Edit credentials**.

## Troubleshooting

| Error | Cause in Dynamics 365 | Fix |
|---|---|---|
| CONN-401 | Client secret expired or deleted, or the app registration was deleted. | Create a new secret, update the connection, and click **Reconnect**. |
| CONN-403 | The security role lacks a privilege on the table, or the application user is disabled. | Add the privilege to the role, or re-enable the application user. |
| CONN-404 | The row GUID doesn't exist, or the logical name is misspelled. | Check the GUID and use the logical name, not the display name. |
| CONN-429 | Dataverse service protection limits were reached. | Nimbus retries automatically; spread bulk changes out. |
| WF-400 | A required column resolved to empty, or a choice column received a label. | Map the column, and use the choice's integer value. |
| WF-100 | The OData filter on a trigger is invalid. | Correct the filter syntax, e.g. `statecode eq 0`. |
