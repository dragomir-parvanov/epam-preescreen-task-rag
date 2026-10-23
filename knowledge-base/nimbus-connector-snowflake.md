---
id: nimbus-connector-snowflake
title: Snowflake Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-12
owner: Integrations Team
---

The Snowflake connector, added in 3.4.0, lets workflows read from and write to a Snowflake account: run a query and use the rows in later steps, insert rows, or merge rows into a table. It signs in with key-pair authentication as a Snowflake service user, so no password is stored in Nimbus.

The connector has no triggers. A workflow that loads data into Snowflake starts from another trigger, usually a schedule or an event from another connector, and uses Snowflake actions in its steps.

## Prerequisites

The Snowflake side needs a service user with its own role and warehouse. A Snowflake user with `SECURITYADMIN` (for the user and role) and `SYSADMIN` (for the warehouse and grants) sets these up once. In Nimbus, a Builder or Admin creates the connection, which counts towards the active-connector limit of the Plan Tier ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

| Object | Example name | Grants it needs |
|---|---|---|
| Role | `NIMBUS_ROLE` | Granted to the service user |
| Warehouse | `NIMBUS_WH` (X-Small is enough for most workflows) | `USAGE` to `NIMBUS_ROLE` |
| Database and schema | `ANALYTICS.CRM` | `USAGE` on both |
| Tables | `ANALYTICS.CRM.ACCOUNTS` | `SELECT` for queries; `INSERT` for Insert rows; `INSERT`, `UPDATE` and, if used, `DELETE` for Merge rows |
| Service user | `NIMBUS_SVC` | `TYPE = SERVICE`, default role and warehouse set, RSA public key assigned |

### Generating the key pair

Generate a 2048-bit RSA key pair on a trusted machine. The private key goes into Nimbus and the public key into Snowflake.

```bash
# Private key in PKCS#8 format (add -v2 aes256 instead of -nocrypt to encrypt it with a passphrase)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out nimbus_rsa_key.p8 -nocrypt

# Matching public key
openssl rsa -in nimbus_rsa_key.p8 -pubout -out nimbus_rsa_key.pub
```

Then create the user and assign the public key, pasting the contents of `nimbus_rsa_key.pub` without the `BEGIN` and `END` lines:

```sql
USE ROLE SECURITYADMIN;
CREATE ROLE IF NOT EXISTS NIMBUS_ROLE;
CREATE USER NIMBUS_SVC
  TYPE = SERVICE
  DEFAULT_ROLE = NIMBUS_ROLE
  DEFAULT_WAREHOUSE = NIMBUS_WH
  RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv3...';
GRANT ROLE NIMBUS_ROLE TO USER NIMBUS_SVC;

USE ROLE SYSADMIN;
GRANT USAGE ON WAREHOUSE NIMBUS_WH TO ROLE NIMBUS_ROLE;
GRANT USAGE ON DATABASE ANALYTICS TO ROLE NIMBUS_ROLE;
GRANT USAGE ON SCHEMA ANALYTICS.CRM TO ROLE NIMBUS_ROLE;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ANALYTICS.CRM TO ROLE NIMBUS_ROLE;
```

To rotate the key later without downtime, set the new public key as `RSA_PUBLIC_KEY_2`, update the connection in Nimbus, and then unset the old one.

## Creating the connection

1. Open **Connections > New connection** and select **Snowflake**.
2. Enter a **Connection name**, for example `Snowflake – analytics`.
3. Enter the **Account identifier** in the `orgname-accountname` form, such as `acme-analytics`. It is the first part of the account URL.
4. Enter **User** (`NIMBUS_SVC`), **Role** (`NIMBUS_ROLE`), **Warehouse** (`NIMBUS_WH`), and optionally a default **Database** and **Schema**.
5. Paste the whole private key, including its `BEGIN PRIVATE KEY` and `END PRIVATE KEY` lines, into **Private key**. If the key is encrypted, enter its **Passphrase**.
6. Click **Save**, then **Test connection**. Nimbus signs in and runs `SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE()`, then shows the result with the status **Connected**.

The private key is encrypted at rest and never shown again. To change it, paste a new one over it.

## Triggers and actions

| Action | Input | Output |
|---|---|---|
| Run query | A SQL statement with `?` bind parameters and a list of values | `rows` (list of objects keyed by column name), `row_count`, `query_id` |
| Insert rows | Target table and a list of row objects | `rows_inserted`, `query_id` |
| Merge rows | Target table, key columns, and a list of row objects | `rows_inserted`, `rows_updated`, `query_id` |

There are no triggers. To react to new data in Snowflake, schedule a workflow with a query that selects rows newer than a stored watermark.

## Field mapping

Bind parameters keep values out of the SQL text, which avoids quoting problems and SQL injection. Pass them in order in **Parameters**:

```yaml
# Step: Run query
statement: >
  SELECT account_id, name, arr, updated_at
  FROM ANALYTICS.CRM.ACCOUNTS
  WHERE region = ? AND updated_at > ?
parameters:
  - "{{trigger.body.region}}"
  - "{{default(steps.watermark.output.rows[0].LAST_SYNC, '2026-01-01T00:00:00Z')}}"
```

For **Insert rows** and **Merge rows**, each object's keys are column names. Snowflake folds unquoted names to upper case, so `account_id` matches a column `ACCOUNT_ID`. Timestamps should be ISO 8601 strings; `VARIANT` columns take a JSON object.

## Limits and behaviour

**Run query** returns results in pages. Each page holds up to 1,000 rows (set **Page size** from 100 to 10,000), and the output carries a `next_page_token` while more rows remain. Feed that token into the next **Run query** step inside a loop to read the rest, or set **Fetch all pages** to read up to the **Max rows** limit of 100,000 in one step. A step's output is limited to 100 MB, the same as files passed between steps.

A step that runs longer than 10 minutes fails with WF-200, so long transformations belong in Snowflake tasks rather than in a workflow step. Setting `STATEMENT_TIMEOUT_IN_SECONDS = 540` on the service user makes Snowflake cancel the query first, which leaves the warehouse idle sooner. If the warehouse is suspended and has auto-resume on, the first query waits for it to resume. Failed steps are retried 3 times by default. A retried **Insert rows** can add the same rows twice, so prefer **Merge rows** on a key column wherever a duplicate would matter.

## Troubleshooting

| Code | Snowflake message | Fix |
|---|---|---|
| CONN-401 | `JWT token is invalid` | The private key doesn't match the user's `RSA_PUBLIC_KEY`, or the account identifier or user name is wrong. Recheck all three. |
| CONN-403 | `Insufficient privileges to operate on table` | Grant the missing privilege to `NIMBUS_ROLE`. |
| CONN-404 | `Object does not exist or not authorized` | Snowflake returns this for missing grants as well as missing objects; check `USAGE` on the database and schema. |
| CONN-503 | Snowflake is unavailable | Nimbus retries the step. |
| WF-200 | – | The query ran over 10 minutes; reduce it or move the work to a Snowflake task. |
| (step error) `No active warehouse selected` | The warehouse is missing from the connection, or `USAGE` was revoked. | Set **Warehouse** and check the grant. |
