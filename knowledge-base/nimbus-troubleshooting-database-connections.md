---
id: nimbus-troubleshooting-database-connections
title: Troubleshooting Database Connections
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-22
owner: Support Engineering
---

A database connection in Nimbus is a username and password that the PostgreSQL, MySQL or Microsoft SQL Server connector uses to open a TLS session to the client's database server. When a Builder saves the connection, or clicks **Test** on it under **Connections**, Nimbus opens a session, authenticates, runs a trivial query and reports the result. This reference covers connections that fail that test, and connections that pass it but whose steps fail later for the same underlying reasons.

Connector-specific setup, including the fields on the connection form and how polling triggers on a query work, is in [PostgreSQL Connector](nimbus-connector-postgresql.md), [MySQL Connector](nimbus-connector-mysql.md) and [Microsoft SQL Server Connector](nimbus-connector-sql-server.md).

## Symptoms

Clients usually describe one of these:

- Saving a new connection fails with a red banner under the **Test** button, and the connection isn't created.
- An existing connection shows **Needs attention** under **Connections**, and every step that uses it fails in run history.
- A polling trigger on a query stops starting runs, although the workflow is still active.
- A step that writes rows fails for one table but works for another on the same connection.
- The test spins for about 30 seconds and then reports that the host couldn't be reached.

## Common causes

| Cause | Typical sign |
|---|---|
| TLS is off on the server, or its certificate can't be validated | The test fails at the `tls` stage: "server does not support TLS" or "certificate verify failed" |
| Wrong username, password or database name | The test fails at the `authenticate` stage: "password authentication failed", "Access denied for user" or "Login failed for user" |
| The password was changed or the database account disabled after the connection was saved | Steps that worked before fail with CONN-401 |
| The database user lacks privileges on a schema, table or procedure | The test passes, but a step fails with CONN-403 |
| The server is reachable only inside the client's own network | The test times out at the `connect` stage |
| Steps are routed through a private connector agent that is down | Steps fail with CONN-503 |

Nimbus only connects to databases over TLS 1.2 or later and never falls back to an unencrypted session. The server's certificate must chain to a public certificate authority, or to the CA certificate pasted into the connection's **Server CA certificate** field, and the **Host** on the connection must match a name in that certificate. A connection that names the server by a short internal alias usually fails validation even when TLS is switched on.

The connection test proves only that Nimbus can sign in and run `SELECT 1`. Privileges on individual tables are checked when a step first touches them, which is why a connection can test green and still fail at run time.

## Diagnosing the problem

1. Open **Connections**, select the connection and click **Test**. Note the stage and the exact message; the database's own wording is passed through unchanged.
2. Repeat the test through the API, which returns the failing stage as a field. This is useful when the client's Builder can't share a screen:

   ```http
   POST /connections/con_8Hq2LmR4/test
   Authorization: Bearer <api-key>

   HTTP/1.1 200 OK
   {
     "connection_id": "con_8Hq2LmR4",
     "result": "failed",
     "stage": "authenticate",
     "message": "FATAL: password authentication failed for user \"nimbus_sync\"",
     "tested_at": "2026-06-18T09:42:11Z"
   }
   ```

   The stages run in order: `connect`, `tls`, `authenticate`, `query`. A failure at `connect` means Nimbus never reached the server.
3. If the test passes, open the failed run under **Runs**, select the red step and read its error code, or list the steps with `GET /runs/{id}/steps`. The step log shows the statement that failed.
4. Ask the client's database administrator to sign in as the same database user from their own SQL client and run the failing statement. For PostgreSQL, `SELECT has_table_privilege('nimbus_sync', 'sales.invoices', 'INSERT');` answers the privilege question directly.
5. If the connection is routed through a private connector agent, check its status under **Settings > Agents** before anything else.

## Error reference

| Code | Meaning for a database connection | First action |
|---|---|---|
| CONN-401 | The server rejected credentials that used to work: the password was changed or the account was disabled or locked. The connection shows **Needs attention**. | Enter the new password and click **Reconnect**. |
| CONN-403 | The database user may sign in but lacks the privilege the statement needs (SELECT, INSERT, UPDATE, DELETE or EXECUTE). | Grant the privilege on the object named in the message. |
| CONN-404 | The table, view, schema or stored procedure named in the step doesn't exist, or isn't visible to this user. | Check the object name and schema, including case. |
| CONN-503 | The database server, or the private connector agent the connection is routed through, is unavailable. | Check the server, then the agent. |
| WF-200 | A query ran for more than 10 minutes and the step was stopped. | Narrow the query or add an index. |

## Fixes

### TLS and credentials

Switch TLS on at the server: `ssl = on` in `postgresql.conf` for PostgreSQL, a server certificate with `require_secure_transport = ON` for MySQL, and **Force Encryption** with a certificate in SQL Server Configuration Manager for Microsoft SQL Server. If the certificate comes from the client's own CA, paste the CA certificate (PEM) into **Server CA certificate** and set **Host** to the name the certificate was issued for.

Connection credentials are encrypted and never shown again after saving, so a changed password can't be edited in place. Open the connection, click **Reconnect**, enter the new password and save; the test runs automatically. The Microsoft SQL Server connector signs in with SQL authentication only, so the client needs a SQL login rather than a Windows or Entra ID account. Recommend a dedicated database user for Nimbus, so that a password rotation for a person doesn't break workflows.

### Permissions and private networks

Grant the Nimbus database user the privileges its steps need, and nothing more:

```sql
-- PostgreSQL
GRANT USAGE ON SCHEMA sales TO nimbus_sync;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sales TO nimbus_sync;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT SELECT, INSERT, UPDATE ON TABLES TO nimbus_sync;

-- MySQL
GRANT SELECT, INSERT, UPDATE ON sales.* TO nimbus_sync;

-- Microsoft SQL Server
ALTER ROLE db_datareader ADD MEMBER nimbus_sync;
GRANT INSERT, UPDATE ON SCHEMA::sales TO nimbus_sync;
```

A database server that isn't reachable from the internet can be used only through the private connector agent, which is an Enterprise feature. The client runs the agent inside their network, registers it under **Settings > Agents**, and then selects it in the connection's **Route through agent** field. On other tiers the server must accept TLS connections from Nimbus directly, which is a decision for the client's own network team. See [Private Connector Agent](nimbus-tier-private-connector-agent.md) for setup and [Troubleshooting the Private Connector Agent](nimbus-troubleshooting-private-agent.md) if the agent is the problem.

## Escalating to support

Before opening a ticket, collect:

- the workspace id (`ws_...`) and the connection id (`con_...`);
- the database engine and its version, and whether it is self-hosted or a managed cloud service;
- the stage and message returned by `POST /connections/{id}/test`, with the time in UTC;
- for run-time failures, the run id and the step key from run history;
- whether the connection is routed through a private connector agent, and that agent's name and status.

Never ask the client for the database password; support doesn't need it and will refuse it.
