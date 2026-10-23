---
id: nimbus-connector-servicenow
title: ServiceNow Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-07-06
owner: Integrations Team
---

The ServiceNow connector, added in 3.7.0, reads and writes records in a ServiceNow instance through its REST Table API. Workflows can pick up new and changed incidents and change requests, open or update records, and add work notes. The connection signs in either with OAuth 2.0 or with basic auth, and in both cases it should use a dedicated integration user rather than a person's account.

Its triggers poll the instance; ServiceNow doesn't push events to Nimbus.

## Prerequisites

### The integration user

Create a user in ServiceNow under **User Administration > Users**, for example `svc_nimbus`, and set:

- **Web service access only**: checked, so the account can't sign in to the UI.
- **Password needs reset**: unchecked, otherwise the first API call fails.
- **Time zone**: `GMT`, so that date values in API responses are unambiguous.

Then grant it roles under the **Roles** related list:

| Role | Needed for |
|---|---|
| `itil` | Reading and writing incidents and change requests, and adding work notes |
| `snc_platform_rest_api_access` | Only if the instance enforces the REST API access policy (**System Web Services > REST API Access Policies**) |
| `personalize_dictionary` | Optional; lets the Nimbus field picker read column labels on custom tables |

Records on custom tables need whatever role the table's ACLs require. Avoid `admin`: it works, but it grants far more than the connector uses.

On the Nimbus side, a Builder or Admin creates the connection, and it counts towards the Plan Tier's active-connector limit; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

### OAuth or basic auth

Basic auth needs only the user name and password. For OAuth 2.0, a ServiceNow admin first registers Nimbus under **System OAuth > Application Registry > New > Create an OAuth API endpoint for external clients**, with **Redirect URL** `https://app.nimbus.omnicorp.example/oauth/callback`. Copy the **Client ID** and **Client Secret**. Set **Refresh Token Lifespan** high enough for the client's needs; the ServiceNow default is 8,640,000 seconds (100 days), after which the connection needs reconnecting.

## Creating the connection

1. Open **Connections > New connection** and choose **ServiceNow**.
2. Enter a **Connection name** and the **Instance URL**, such as `https://acme.service-now.com`.
3. Choose the **Authentication** method:
   - **OAuth 2.0**: paste the Client ID and Client Secret, click **Authorise** and sign in as `svc_nimbus` in the ServiceNow window.
   - **Basic auth**: enter the integration user's user name and password.
4. Click **Save**. Credentials are encrypted and can't be viewed again.
5. Click **Test connection**. Nimbus reads one record from `sys_user` as the integration user and shows the instance's build name with the status **Connected**.

## Triggers and actions

| Name | Type | Table | Details |
|---|---|---|---|
| New record | Polling trigger | `incident`, `change_request` or any table | Picks up records whose `sys_created_on` is after the last poll. |
| New or updated record | Polling trigger | Same | Picks up records whose `sys_updated_on` is after the last poll. |
| Create record | Action | Any table the user can write | Returns the new `sys_id` and `number`. |
| Update record | Action | Any table | Updates by `sys_id`; only mapped fields change. |
| Add work note | Action | `incident`, `change_request`, other task tables | Writes to the `work_notes` journal field, visible to fulfillers only. Use **Add comment** mode to write to `comments` instead, which the caller sees. |
| Get record | Action | Any table | Reads one record by `sys_id`, or the first record matching an encoded query such as `name=Service Desk`. |

Both triggers take an optional **Encoded query**, the same syntax as a ServiceNow list filter, for example `priority<=2^assignment_group.name=Service Desk`.

## Field mapping

Reference fields (`caller_id`, `assignment_group`, `cmdb_ci`, `assigned_to`) take the referenced record's **sys_id**, a 32-character hex string. Nimbus sends the value exactly as mapped, so a display name such as `Service Desk` in a reference field leaves it empty or, where names repeat, pointing at the wrong record. Look the record up first with **Get record**, or keep fixed sys_ids for groups that rarely change, as below.

```json
{
  "table": "incident",
  "fields": {
    "short_description": "Nimbus sync failed for {{trigger.body.customer}}",
    "caller_id": "{{steps.get_caller.output.sys_id}}",
    "assignment_group": "8a4dde73c6112278017a6a4baf547aa7",
    "cmdb_ci": "{{default(steps.find_ci.output.sys_id, '')}}",
    "urgency": "2",
    "impact": "2",
    "category": "software"
  }
}
```

Choice fields such as `urgency`, `impact` and `state` take the stored value (`2`), not the label (`2 - Medium`). Outputs return values by default; turn on **Include display values** on a step to get both.

## Limits and behaviour

Polling triggers run every 5 minutes. Each poll asks for records with `sys_updated_on` (or `sys_created_on`) later than the last value seen, ordered ascending, and reads them in pages of 100 using `sysparm_limit` and `sysparm_offset`, up to 1,000 records a poll. Any remainder is picked up by the next poll. When the trigger is first activated, the watermark is set to the current time, so older records don't start runs.

Records updated twice between polls start one run with the latest values, not two. Updates the integration user makes itself also move `sys_updated_on`; add `sys_updated_by!=svc_nimbus` to the encoded query to avoid loops.

Attachments can be passed between steps up to 100 MB, subject to the instance's `com.glide.attachment.max_size` property. Failed actions are retried 3 times by default; a throttled call shows CONN-429 and is retried after a back-off.

## Troubleshooting

| Code | What ServiceNow returned | Fix |
|---|---|---|
| CONN-401 | `User Not Authenticated`: the password changed, the account was locked out, or the OAuth refresh token reached its lifespan. | Update the credentials or click **Reconnect**. |
| CONN-403 | `Insufficient rights` or an ACL denial on the table or field. | Add `itil` or the role the table's ACL needs; check the REST API access policy. |
| CONN-404 | `No Record found` for the `sys_id`. | The record was deleted, or the user can't read it through ACLs. |
| CONN-503 | The instance is hibernating (developer instances) or upgrading. | Wake the instance or wait for the upgrade to finish; Nimbus retries the step. |
| WF-400 | A mapped `sys_id` resolved to empty. | Check the lookup step returned a record. |
