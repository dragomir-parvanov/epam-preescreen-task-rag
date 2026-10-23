---
id: nimbus-connector-sql-server
title: Microsoft SQL Server Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-07-06
owner: Integrations Team
---

The Microsoft SQL Server connector, added in release 3.1.0, connects workflows to SQL Server 2016 and later, Azure SQL Database and Azure SQL Managed Instance. It polls a table for changed rows using a `rowversion` column, runs queries, inserts rows and executes stored procedures.

The connector uses SQL authentication (a SQL login and password) over an encrypted connection. Windows authentication and Microsoft Entra ID authentication aren't supported. Servers that live on-premises or in a private network are reached through the private connector agent on the Enterprise tier.

## Prerequisites

| Requirement | Details |
|---|---|
| SQL Server | 2016 or later, Azure SQL Database or Azure SQL Managed Instance, with mixed-mode (SQL Server and Windows) authentication enabled |
| Login | A SQL login used only by Nimbus, mapped to a user in the target database |
| Permissions | `SELECT` on polled and queried objects, `INSERT` on tables written to, `EXECUTE` on each stored procedure called |
| Encryption | A server certificate for TLS; a certificate from an internal CA is fine (see Creating the connection) |
| Network | The server's port (1433 by default) reachable from Nimbus, or a private connector agent (Enterprise; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)) |

A typical setup for an accounts-payable integration grants only what the workflows use:

```sql
CREATE LOGIN nimbus_svc WITH PASSWORD = '<strong-password>', CHECK_POLICY = ON;
USE Finance;
CREATE USER nimbus_svc FOR LOGIN nimbus_svc;
GRANT SELECT ON SCHEMA::ap TO nimbus_svc;
GRANT INSERT ON ap.InvoiceImport TO nimbus_svc;
GRANT EXECUTE ON OBJECT::ap.usp_ApproveInvoice TO nimbus_svc;
```

If the login has a password expiry policy, the connection stops working when the password expires; either exempt the login (`CHECK_EXPIRATION = OFF`) or plan the rotation.

## Creating the connection

1. Go to **Connections > New connection** and select **Microsoft SQL Server**.
2. Name the connection and enter **Server** (host name, or `host\instance` for a named instance), **Port**, **Database**, **Login** and **Password**.
3. Set the certificate options. Encryption is always on. **Trust server certificate** is off by default, which means the server certificate must chain to a trusted CA and match **Host name in certificate** (leave that field empty to use **Server**). For an internal CA, paste its certificate into **CA certificate**. Turn **Trust server certificate** on only for a server with a self-signed certificate, and treat that as a temporary measure: the session is still encrypted, but the server's identity isn't checked.
4. Choose **Direct** or **Private agent** under **Network**.
5. Click **Test connection**. Nimbus signs in and runs `SELECT @@VERSION`, and shows the server version on success.
6. Click **Save**.

### On-premises servers through the private connector agent

An Enterprise client whose SQL Server isn't reachable from the internet runs the private connector agent, the `omnicorp/nimbus-agent` Docker image, on a host that can reach the database. The agent opens an outbound TLS connection to Nimbus, so no inbound port has to be opened. Register it under **Settings > Agents** with the one-time registration token, start the container, and select it in step 4 above. The agent shows "Offline" once it has missed heartbeats for 2 minutes; steps that use it then fail with CONN-503 until it is back.

## Triggers and actions

| Name | Type | Notes |
|---|---|---|
| New or changed row | Polling trigger | Uses a `rowversion` column as the cursor |
| Run query | Action | Parameterised T-SQL; returns the first result set |
| Insert row | Action | Returns the inserted row through `OUTPUT INSERTED.*` |
| Execute stored procedure | Action | Input and output parameters, return value and the first result set |

SQL Server increments a table's `rowversion` value on every insert and update, which makes it a better cursor than a `datetime2` column: it can't be set by the application and never goes backwards. The trigger query must contain the `@cursor` parameter:

```sql
SELECT InvoiceId, VendorId, Amount, Status, RowVer
FROM ap.Invoice
WHERE RowVer > @cursor
ORDER BY RowVer;
```

Nimbus passes `rowversion` values to the workflow as hex strings such as `0x00000000000007D3`. On first activation the trigger starts from the table's current highest value.

## Field mapping

Parameters are written T-SQL style (`@InvoiceId`) and mapped to expressions in the step's **Parameters** panel; `{{...}}` in the SQL text isn't evaluated. For Execute stored procedure, Nimbus reads the procedure's parameter list when the step is configured, so the panel lists each parameter with its type and direction:

```json
{
  "procedure": "ap.usp_ApproveInvoice",
  "parameters": {
    "@InvoiceId": "{{trigger.body.InvoiceId}}",
    "@ApprovedBy": "{{lower(steps.approval.output.decided_by)}}",
    "@ApprovedAt": "{{now()}}",
    "@Comment": "{{default(steps.approval.output.comment, '')}}"
  }
}
```

The step's output has `return_value`, `output_parameters` and `rows`, so a later condition can test `{{steps.approve_invoice.output.output_parameters.Status}}`. `datetime2` and `datetimeoffset` values become ISO 8601 strings in UTC; `decimal` and `money` columns are returned as strings to keep their precision; `uniqueidentifier` values are returned in upper case.

## Limits and behaviour

- The trigger polls every 5 minutes and passes on at most 1,000 rows per poll, in `rowversion` order.
- Run query and Execute stored procedure return at most 10,000 rows from the first result set; further result sets are ignored.
- Each step is its own transaction. A stored procedure that manages its own transactions keeps working, but anything it commits stays committed if a later step fails.
- A statement or procedure running longer than 10 minutes is cancelled with WF-200; long batch procedures should be split or run by SQL Server Agent instead.
- `varbinary(max)` values can be passed to later steps as files of up to 100 MB.
- Failed steps are retried 3 times by default (after 30 seconds, 2 minutes and 10 minutes). A stored procedure that isn't idempotent should have its step's retries set to 0.

## Troubleshooting

| Code | SQL Server error | Fix |
|---|---|---|
| CONN-401 | 18456 `Login failed for user 'nimbus_svc'` | Wrong or expired password, or the login is disabled. Edit the connection. |
| CONN-403 | 229 `The SELECT permission was denied on the object` | Grant the permission to the database user (not only the login). |
| CONN-404 | 208 `Invalid object name 'ap.Invoice'` | Check the schema and that **Database** is the database holding the object. |
| CONN-503 | Timeout or `The certificate chain was issued by an authority that is not trusted` | Server unreachable or the agent is Offline; for the certificate error, add the CA certificate. |
| WF-100 | Trigger query without `@cursor` | Add `WHERE RowVer > @cursor` and order by the `rowversion` column. |
| WF-200 | Step stopped after 10 minutes | Tune the query or procedure; add an index on the cursor column. |

For other databases, see [PostgreSQL Connector](nimbus-connector-postgresql.md) and [MySQL Connector](nimbus-connector-mysql.md).
