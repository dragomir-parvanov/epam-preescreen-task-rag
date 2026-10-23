---
id: nimbus-connector-postgresql
title: PostgreSQL Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-15
owner: Integrations Team
---

The PostgreSQL connector lets a workflow read from and write to a PostgreSQL database: it can start a run for every new or changed row in a table, run a query, insert a row or upsert one. It works with PostgreSQL 12 and later, including managed services such as Amazon RDS for PostgreSQL, Amazon Aurora PostgreSQL and Azure Database for PostgreSQL.

Nimbus signs in with a database username and password, always over TLS. Databases that can't be reached from the internet are connected through the private connector agent, which is available on the Enterprise tier.

## Prerequisites

Before a Builder creates the connection, the client's database team needs to provide the following:

- **A dedicated database role** with password authentication (SCRAM or md5). Don't reuse a personal login: the connection keeps working only as long as this role's password is unchanged.
- **TLS enabled on the server** (`ssl = on` in `postgresql.conf`, or the managed service's default). The connector refuses unencrypted sessions.
- **Grants** on exactly the schemas and tables the workflows touch. Polling and Run query need `SELECT`; Insert row needs `INSERT`; Upsert row needs `INSERT` and `UPDATE` and a unique index or primary key on the conflict columns.
- **Network reachability.** The server's port (5432 by default) must accept TLS connections from Nimbus over the internet, or the client must run the private connector agent inside their network. The agent is Enterprise only; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

A minimal role for a workflow that syncs orders looks like this:

```sql
CREATE ROLE nimbus_sync LOGIN PASSWORD '<strong-password>';
GRANT CONNECT ON DATABASE commerce TO nimbus_sync;
GRANT USAGE ON SCHEMA sales TO nimbus_sync;
GRANT SELECT ON sales.orders TO nimbus_sync;
GRANT SELECT, INSERT, UPDATE ON sales.customers TO nimbus_sync;
```

The connector is available on every Plan Tier, and a PostgreSQL connection used by an active workflow counts towards the workspace's active connectors.

## Creating the connection

A Builder or Admin creates the connection in the admin console:

1. Open **Connections** and click **New connection**, then choose **PostgreSQL**.
2. Enter a **Connection name** that says which database it reaches, for example `commerce-prod (read/write)`.
3. Fill in **Host**, **Port** (default `5432`), **Database**, **Username** and **Password**.
4. Choose the **SSL mode**. Only `require` and `verify-full` are offered. With `require` the session is encrypted but the server certificate isn't checked; with `verify-full` Nimbus also checks the certificate chain and that the certificate's name matches **Host**. For `verify-full`, paste the issuing CA certificate (PEM) into **CA certificate** if it isn't a public CA.
5. Under **Network**, leave **Direct** selected, or choose **Private agent** and pick an agent that shows "Online" under **Settings > Agents**.
6. Click **Test connection**. Nimbus opens a TLS session, signs in and runs `SELECT 1`.
7. Click **Save**. The password is encrypted and never shown again; to change it, open the connection, click **Edit** and enter the new password.

Use `verify-full` for production databases. `require` is acceptable for a managed service whose CA the client can't easily export, but it doesn't protect against a server being impersonated.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New or updated row | Polling trigger | Runs the trigger query and starts one run per row whose cursor column is greater than the last value seen |
| Run query | Action | Runs one parameterised SQL statement and returns its rows (or the affected-row count) |
| Insert row | Action | Inserts one row into a table and returns the inserted row through `RETURNING *` |
| Upsert row | Action | `INSERT ... ON CONFLICT (<conflict columns>) DO UPDATE`; returns the row and whether it was inserted or updated |

### Polling with a cursor column

The trigger query must select from one table or view, include a `:cursor` placeholder in its `WHERE` clause and order by the cursor column. A good cursor column only ever increases: a `bigserial` primary key catches new rows, and an `updated_at timestamptz` column maintained by a trigger catches both new and changed rows.

```sql
SELECT id, customer_id, status, total_amount, updated_at
FROM sales.orders
WHERE updated_at > :cursor
ORDER BY updated_at, id
LIMIT 1000
```

Nimbus stores the highest cursor value it has processed. When the workflow is activated for the first time, the trigger records the current maximum and starts from there, so existing rows don't each start a run. To backfill, set **Initial cursor value** in the trigger to an earlier value before activating.

## Field mapping

Values reach SQL only through named parameters. The SQL editor doesn't evaluate `{{...}}` expressions, so a statement such as `WHERE email = '{{trigger.body.email}}'` is sent literally and fails. Write a placeholder such as `:customer_email` in the SQL, then map it in the step's **Parameters** panel. Parameters are bound by the driver, which also prevents SQL injection from values that arrive in webhook payloads.

An Upsert row step that keeps a customer table in step with a CRM looks like this in the step's configuration view:

```yaml
step: upsert_customer
action: Upsert row
table: sales.customers
conflict_columns: [external_id]
values:
  external_id: "{{trigger.body.Id}}"
  email: "{{lower(trigger.body.Email)}}"
  display_name: "{{trigger.body.Name}}"
  tier: "{{default(trigger.body.Tier__c, 'standard')}}"
  synced_at: "{{now()}}"
```

The trigger exposes each row as `{{trigger.body.<column>}}`, and later steps read action results as `{{steps.upsert_customer.output.row.<column>}}` and `{{steps.upsert_customer.output.inserted}}`. Column types are converted predictably: `timestamptz` and `timestamp` become ISO 8601 strings in UTC, `json` and `jsonb` become objects, and `numeric` is returned as a string so no precision is lost; wrap it in a transform if a number is needed.

## Limits and behaviour

- **Polling.** The trigger query runs every 5 minutes. One poll returns at most 1,000 rows; any remaining rows are picked up by the next poll, in cursor order.
- **Query results.** Run query returns at most 10,000 rows. Page through larger result sets with `LIMIT` and `OFFSET` (or keyset paging) inside a loop step.
- **Transactions.** Each step runs in its own transaction and commits when the step succeeds. Nimbus doesn't hold a transaction open across steps.
- **Timeouts.** A statement that runs longer than 10 minutes is cancelled and the step fails with WF-200. Index the cursor column so polling stays fast.
- **Binary data.** `bytea` values can be passed to later steps as files of up to 100 MB.
- **Retries.** A failed step is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Insert row is not idempotent, so a retry after a network error can create a duplicate; prefer Upsert row, or set the step's retries to 0.

## Troubleshooting

| Code | What PostgreSQL reports | Fix |
|---|---|---|
| CONN-401 | `password authentication failed for user "nimbus_sync"` | The password was changed or the role was dropped. Edit the connection and enter the current password. |
| CONN-403 | `permission denied for table orders` | Grant the missing privilege to the role, then retry the run. |
| CONN-404 | `relation "orders" does not exist` | Schema-qualify the table (`sales.orders`) or add the schema to the role's `search_path`. |
| CONN-429 | `sorry, too many clients already` | The server is at `max_connections`. Raise the limit or lower the workflow's concurrency. |
| CONN-503 | Connection refused or timed out | Check that the server is running and reachable; for agent connections, check the agent's status under **Settings > Agents**. |
| WF-100 | Trigger query has no `:cursor` placeholder | Add the placeholder to the `WHERE` clause and order by the cursor column. |
| WF-400 | `null value in column violates not-null constraint` | A mapped expression resolved to empty; add a `default()` or a condition step before the write. |

If **Test connection** reports `server does not support SSL connections`, TLS isn't enabled on the server; the connector has no unencrypted fallback. For the MySQL and SQL Server equivalents of these steps, see [MySQL Connector](nimbus-connector-mysql.md) and [Microsoft SQL Server Connector](nimbus-connector-sql-server.md).
