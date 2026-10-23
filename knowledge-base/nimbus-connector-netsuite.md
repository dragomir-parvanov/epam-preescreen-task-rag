---
id: nimbus-connector-netsuite
title: NetSuite Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-02
owner: Integrations Team
---

The NetSuite connector, added in release 3.2.0, connects a workflow to a client's Oracle NetSuite account. It creates and updates records such as customers, sales orders and vendor bills, runs SuiteQL queries, and starts runs from the results of a saved search. Finance and order-to-cash teams use it most, often paired with Salesforce or an inbound webhook from an e-commerce platform.

NetSuite has no push events for the connector to subscribe to, so its triggers poll. Authentication uses NetSuite's token-based authentication (TBA), which needs a little setup on the NetSuite side before the connection can be made.

## Prerequisites

Token-based authentication ties four secrets to one integration record, one role and one user. Have the client's NetSuite administrator prepare:

- **TBA enabled.** Under **Setup > Company > Enable Features > SuiteCloud**, tick **Token-Based Authentication** and **REST Web Services**.
- **An integration record** for Nimbus, with **Token-Based Authentication** ticked and **Authorization Code Grant** left unticked.
- **A dedicated role** for the integration. It needs the **Log in using Access Tokens** and **REST Web Services** permissions, **SuiteAnalytics Workbook** for SuiteQL, and the record permissions the workflows use (for example **Customers: Full**, **Sales Order: Create**, **Perform Search** for saved-search triggers).
- **An integration user** with that role. Using a named employee's login means the connection breaks when their access is changed.
- **The account id.** It appears under **Setup > Company > Company Information**.
- **A Builder or Admin** to create the connection in Nimbus, and room for another active connector on the workspace's Plan Tier (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

The account id must be entered in the format NetSuite shows it:

| Account type | Example account id | Notes |
|---|---|---|
| Production | `4810325` | Digits only. |
| Sandbox | `4810325_SB1` | Underscore and the sandbox number, in capitals. |
| Release preview | `4810325_RP` | Only for testing upcoming NetSuite releases. |

## Creating the connection

1. In NetSuite, open the integration record and copy the **Consumer Key** and **Consumer Secret**. NetSuite shows them only once, when the record is saved.
2. Go to **Setup > Users/Roles > Access Tokens > New**, choose the integration record, the integration user and the dedicated role, and save. Copy the **Token ID** and **Token Secret**.
3. In the Nimbus admin console, go to **Connections > New connection** and choose **NetSuite**.
4. Enter the **Account ID**, then paste the consumer key, consumer secret, token id and token secret.
5. Click **Save and test**. Nimbus signs a request to the account and reads the role's name back to confirm the token works.

A sandbox account is a separate connection with its own integration record and token, because sandbox refreshes from production overwrite access tokens. On Business and Enterprise workspaces that use environments, point the Development environment's steps at the sandbox connection and the Production environment's steps at the production one before promoting the workflow.

## Triggers and actions

| Name | Type | Details |
|---|---|---|
| New saved search result | Polling trigger | Runs once per row that appears in a saved search since the last poll. |
| Updated saved search result | Polling trigger | Runs once per row whose **Date Last Modified** is later than the last poll. |
| Create record | Action | Creates a record of the chosen type (customer, sales order, invoice, vendor bill, custom record and others) and returns its internal id. |
| Update record | Action | Updates the mapped fields on a record identified by its internal id or external id. |
| Run SuiteQL query | Action | Runs a read-only SuiteQL query and returns the rows as a list. |

Saved-search triggers require the search to include **Internal ID** and **Date Last Modified** as result columns. A search without them can't be activated and fails with WF-100. Use a saved search owned by the integration role, or one shared with it, so that a change to someone's personal search doesn't alter the trigger.

## Field mapping

NetSuite fields are addressed by their script ids (`companyname`, `subsidiary`, `custentity_tier`), not their labels. Select and list fields take the internal id of the chosen value, wrapped in an `id` object. The example below creates a customer from an inbound webhook and reads the subsidiary id from an environment variable, because sandbox and production accounts often number their subsidiaries differently:

```json
{
  "recordType": "customer",
  "fields": {
    "companyname": "{{trigger.body.company.name}}",
    "email": "{{lower(trigger.body.company.billing_email)}}",
    "subsidiary": { "id": "{{env.NETSUITE_SUBSIDIARY_ID}}" },
    "custentity_crm_id": "{{trigger.body.company.id}}"
  }
}
```

SuiteQL queries can use expressions for their parameters. Rows come back in `steps.<step-key>.output.rows`, ready for a loop step:

```sql
SELECT id, tranid, entity, trandate, status
FROM transaction
WHERE type = 'SalesOrd'
  AND lastmodifieddate >= TO_DATE('{{steps.get_watermark.output.value}}', 'YYYY-MM-DD')
```

## Limits and behaviour

Both triggers poll every 5 minutes. Each poll reads the saved search a page at a time and starts one run per new or changed row. The first poll after activation only records where to start, so existing rows aren't replayed.

SuiteQL results are paged by NetSuite; the action follows the pages and returns up to 5,000 rows in one step. A query that would return more fails with WF-400, and the query should be narrowed or split with a date range. Very large queries can also run into the step limit: a step that takes longer than 10 minutes is stopped with WF-200.

NetSuite limits how many requests one account handles at the same time, shared across every integration on the account. When that limit is hit the step fails with CONN-429 and Nimbus backs off and retries it, using the step's retry settings (3 retries by default, after 30 seconds, 2 minutes and 10 minutes). Clients who see CONN-429 often should check what else is using their account's concurrency.

## Troubleshooting

| Error | Cause in NetSuite | Fix |
|---|---|---|
| CONN-401 | The access token was revoked, the integration user was made inactive, or a sandbox refresh replaced the token. | Create a new access token and click **Reconnect**. |
| CONN-403 | The role lacks a permission for the record type or for SuiteQL. | Add the permission to the dedicated role, then retry the run. |
| CONN-404 | No record with that internal id exists, or the account id points at the wrong account. | Check the id, and whether the connection is the sandbox or production one. |
| CONN-429 | The account's concurrency limit was reached. | Nimbus retries automatically; spread schedules that hit NetSuite at the same minute. |
| WF-100 | The saved search is missing **Internal ID** or **Date Last Modified**. | Add both result columns to the search. |
| WF-400 | A mandatory NetSuite field, such as `subsidiary`, resolved to empty. | Map the field or set a default with `{{default(x, y)}}`. |
