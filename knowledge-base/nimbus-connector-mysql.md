---
id: nimbus-connector-mysql
title: MySQL Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-22
owner: Integrations Team
---

The MySQL connector connects workflows to MySQL 5.7 and 8.0 databases, including Amazon RDS for MySQL, Amazon Aurora MySQL and Azure Database for MySQL. A workflow can start when rows are added or changed, read data with a query, and insert or update rows.

The connection signs in with a username and password and always uses TLS. Most support questions about this connector come down to two things: the privileges of the database user, and how `DATETIME` values are interpreted, so both are covered in detail below.

## Prerequisites

- A MySQL account created for Nimbus alone, with only the privileges its workflows need. A least-privilege account limits the damage a misconfigured workflow can do: if a workflow only reads leads and writes activity rows, the account should be able to do exactly that.
- TLS enabled on the server. Create the account with `REQUIRE SSL` so it can't be used over an unencrypted session by anything else either.
- The server's port (3306 by default) reachable from Nimbus, or, on the Enterprise tier, a private connector agent running inside the client's network (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)).
- A Builder or Admin role in Nimbus to create the connection.

The privileges map to the connector's operations as follows. Don't grant `DELETE`, `DROP`, `ALTER` or global privileges; the connector never needs them.

| Operation | Privilege needed |
|---|---|
| New row / New or updated row trigger | `SELECT` on the polled table |
| Run query | `SELECT` (plus whatever the statement itself does) |
| Insert row | `INSERT` |
| Update rows | `UPDATE` and `SELECT` on the key columns |

```sql
CREATE USER 'nimbus_app'@'%' IDENTIFIED BY '<strong-password>' REQUIRE SSL;
GRANT SELECT ON crm.leads TO 'nimbus_app'@'%';
GRANT SELECT, INSERT, UPDATE ON crm.lead_activity TO 'nimbus_app'@'%';
```

## Creating the connection

1. In the admin console, go to **Connections**, click **New connection** and choose **MySQL**.
2. Give the connection a name, for example `crm-replica`.
3. Enter **Host**, **Port**, **Database**, **Username** and **Password**.
4. Leave **Verify server certificate** on unless the server uses a self-signed certificate; in that case paste the CA certificate (PEM) into **CA certificate** rather than turning verification off. TLS itself can't be turned off.
5. Set **Session time zone** to the time zone the application writes `DATETIME` values in (default `UTC`); the section on `DATETIME` values below explains why this matters.
6. If the server sits on a private network, set **Network** to **Private agent** and pick the agent.
7. Click **Test connection**, then **Save**. The password is encrypted and is never displayed again.

## Triggers and actions

| Operation | Kind | Returns |
|---|---|---|
| New row | Polling trigger on an auto-increment column | One run per new row, with every selected column |
| New or updated row | Polling trigger on a timestamp column | One run per row whose timestamp moved past the last value seen |
| Run query | Action | `rows` for a `SELECT`; `affected_rows` for other statements |
| Insert row | Action | The inserted values and `last_insert_id` |
| Update rows | Action | `affected_rows` for an update matched on key columns |

Choose the trigger by what the workflow must notice. An `AUTO_INCREMENT` id only grows when rows are inserted, so **New row** never sees edits. **New or updated row** needs a column such as `updated_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)`. Use fractional-second precision: with whole seconds, two rows written in the same second can straddle a poll. Nimbus re-reads rows equal to the last cursor value and drops the ones it has already processed by primary key, so the table must have one.

The trigger query uses the `:cursor` placeholder, for example `SELECT id, email, source, updated_at FROM crm.leads WHERE updated_at > :cursor ORDER BY updated_at, id`.

## Field mapping

Run query, Insert row and Update rows take named parameters written as `:name` in the SQL, each mapped to an expression in the step's **Parameters** panel. Expressions in the SQL text itself aren't evaluated. An Update rows step that records the outcome of a lead-routing workflow:

```json
{
  "table": "crm.lead_activity",
  "key_columns": ["lead_id"],
  "values": {
    "lead_id": "{{trigger.body.id}}",
    "owner_email": "{{lower(steps.assign_owner.output.email)}}",
    "routed_at": "{{now()}}",
    "channel": "{{default(trigger.body.source, 'web')}}"
  }
}
```

An Update rows step that matches nothing isn't an error: `{{steps.update_activity.output.affected_rows}}` is `0`, and a condition step can branch on it to insert instead.

### DATETIME and time zones

MySQL's `DATETIME` stores a wall-clock value with no time zone, so the connector needs to be told how to read it. Nimbus interprets every `DATETIME` value in the connection's **Session time zone** and converts it to ISO 8601 in UTC before it reaches the workflow. With the session time zone set to `Europe/Berlin`, the stored value `2026-03-02 09:00:00` arrives as `2026-03-02T08:00:00Z`. `TIMESTAMP` columns are converted by the server itself, using the same session time zone, so both types arrive consistently.

On the way back in, ISO 8601 values from expressions such as `{{now()}}` are converted from UTC to the session time zone before they are written. If the session time zone doesn't match what the application uses, every value is shifted by the difference, and a timestamp-based trigger can skip or repeat rows around the change to or from daylight saving time. Prefer `UTC` wherever the application allows it.

## Limits and behaviour

The polling triggers run every 5 minutes and hand over at most 1,000 rows per poll, oldest cursor value first; the rest wait for the next poll. On first activation the trigger starts from the table's current maximum, so history isn't replayed unless **Initial cursor value** is set.

Run query returns at most 10,000 rows. A statement still running after 10 minutes is killed and the step fails with WF-200. `BLOB` columns can be handed to later steps as files of up to 100 MB, but large values also need the server's `max_allowed_packet` to be big enough.

Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Update rows is safe to retry; Insert row can create a duplicate after a network error unless the table has a unique key that rejects it.

## Troubleshooting

| Code | MySQL message | Fix |
|---|---|---|
| CONN-401 | `Access denied for user 'nimbus_app'@'...'` | Password changed or account locked. Edit the connection with the current password. |
| CONN-403 | `SELECT command denied to user` / `UPDATE command denied` | Grant the privilege on that table; compare with the table under Prerequisites. |
| CONN-404 | `Table 'crm.leads' doesn't exist` | Check the database and table name; names are case-sensitive on Linux servers. |
| CONN-429 | `Too many connections` | Raise `max_connections` or reduce how many runs of the workflow overlap. |
| CONN-503 | `Can't connect to MySQL server` | Server down, port closed, or the private agent is offline. |
| WF-100 | Trigger query without `:cursor` | Add the placeholder and an `ORDER BY` on the cursor column. |
| WF-400 | `Incorrect datetime value: ''` | A mapped expression was empty; use `default()` or a condition. |

For the same connector pattern on other databases, see [PostgreSQL Connector](nimbus-connector-postgresql.md) and [Microsoft SQL Server Connector](nimbus-connector-sql-server.md).
