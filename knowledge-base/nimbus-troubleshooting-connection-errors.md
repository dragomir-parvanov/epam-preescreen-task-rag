---
id: nimbus-troubleshooting-connection-errors
title: Troubleshooting Connector Authorization Errors
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-11
owner: Support Engineering
---

Every connector step acts through a connection: a client's authorised account in a third-party app such as Salesforce, Jira Cloud or Zendesk. When the third-party app stops accepting that authorisation, or accepts it but refuses a particular action, the step fails with CONN-401 or CONN-403. The two look alike in a failed run but have different causes and different fixes.

This reference is for CSMs whose client reports that "a connector stopped working". For the other connector codes, such as throttling, see the error reference below and the Articles it links to.

## Symptoms

CONN-401 and CONN-403 present differently, which is often the quickest way to tell them apart.

With **CONN-401** the whole connection is broken. Every step that uses it fails, in every workflow, from one moment onwards. Under **Connections** the connection's status changes from *Connected* to **Needs attention**, an amber banner appears on each workflow that uses it, and Nimbus sends the `connector.disconnected` webhook event to any endpoint subscribed to it. Clients who route that event into Slack or their monitoring often see it before they see a failed run.

With **CONN-403** the connection stays *Connected*. Only some actions fail, typically writes to one object type or access to one project or channel, while other steps through the same connection keep succeeding. No `connector.disconnected` event is sent.

## Common causes

| Cause | Typical example | Code |
|---|---|---|
| The third-party admin revoked the app's access | A Salesforce admin revokes Nimbus under **Setup > Connected Apps OAuth Usage** | CONN-401 |
| The connected account was deactivated | The employee who made the HubSpot or Asana connection left and their account was disabled | CONN-401 |
| A token, key or secret expired or was replaced | A GitLab project access token passed its expiry date; a Marketo client secret was reset; an Azure Blob Storage SAS token expired | CONN-401 |
| Admin consent was withdrawn in Microsoft Entra ID | The enterprise application for Microsoft Teams or SharePoint Online was deleted or its consent revoked | CONN-401 |
| A key-based credential was deleted | The Zendesk API token or BambooHR API key used by the connection was removed | CONN-401 |
| The account lost a permission | A Salesforce profile no longer has *Edit* on Opportunity; a Jira user was removed from the project's role | CONN-403 |
| The app was never given access to the target | The Slack app isn't a member of the private channel the step posts to | CONN-403 |
| An action needs a scope the connection wasn't granted | A HubSpot connection made before a workflow started using a step that writes to deals | CONN-403 |

Expired OAuth refresh tokens are the most common single cause. Some apps expire refresh tokens that go unused for a period, so a connection used only by a quarterly workflow can be broken by the time it next runs.

## Diagnosing the problem

1. In the failed run, open the failed step and read the error code and the third-party message on its **Log** tab. The third-party wording (for example `invalid_grant` or `INSUFFICIENT_ACCESS_OR_READONLY`) is the most useful clue.
2. Open **Connections** and find the connection the step uses. Check its status, the **Connected account** and **Last authorised** fields, and the list of workflows using it.
3. Run a connection test, either with **Test connection** on the connection page or through the API:

```http
POST /connections/con_8F2KQ1/test HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{"id": "con_8F2KQ1", "connector": "salesforce", "status": "needs_attention", "result": "failed", "error": {"code": "CONN-401", "message": "invalid_grant: expired access/refresh token"}}
```

4. If the test passes but steps still fail with CONN-403, the connection itself is fine. Compare what the step does with the permissions the connector's Article lists, for example [Salesforce Connector](nimbus-connector-salesforce.md) or [Jira Cloud Connector](nimbus-connector-jira-cloud.md), and check the connected account's permissions in the third-party app.
5. To find out who changed something on the Nimbus side, search **Settings > Audit log** for connection events around the time of the first failure.

## Error reference

| Code | Meaning | Connection status | Webhook event |
|---|---|---|---|
| CONN-401 | The connection's authorisation expired or was revoked; reconnect it. | Needs attention | `connector.disconnected` |
| CONN-403 | The connected account lacks permission in the third-party app for this action. | Connected | None |
| CONN-404 | The record, file or object the step refers to doesn't exist in the third-party app. | Connected | None |
| CONN-429 | The third-party app throttled the connector; Nimbus backs off and retries the step. See [Troubleshooting Third-Party Throttling](nimbus-troubleshooting-third-party-throttling.md). | Connected | None |
| CONN-503 | The third-party app is unavailable; the step can be retried once the app is back. | Connected | None |

## Fixes

### Reconnecting

A CONN-401 is fixed by reauthorising the connection. Only a Builder or Admin can do it.

1. Open **Connections**, select the connection marked **Needs attention**, and click **Reconnect**.
2. For OAuth connectors, sign in to the third-party app as the same account that made the connection, and approve the requested access. Signing in as a different account works, but records created afterwards will show that account as their creator or owner.
3. For key-based connectors (Zendesk, BambooHR, Marketo, Snowflake and similar), enter a new token, key or secret. Saved credentials are never shown again, so the client needs the new value from the third-party app.
4. Wait for the status to return to *Connected*, then click **Test connection**.

Reconnecting keeps the connection's id (`con_...`), so the workflows that use it need no edits. Runs that failed before the reconnect are not retried automatically; run them again as described in [Troubleshooting Failed Workflow Runs](nimbus-troubleshooting-failed-runs.md).

### Fixing permissions

A CONN-403 is fixed in the third-party app, not in Nimbus: give the connected account the missing object permission, project role or channel membership. Reconnecting isn't needed, except when the step needs an OAuth scope the connection was never granted; in that case **Reconnect** shows the new scope on the consent screen. To avoid both problems recurring, recommend that clients connect with a dedicated integration user rather than a person's account, so that staff changes don't break workflows.

## Escalating to support

Escalate when a connection still fails its test straight after a successful reconnect, or when CONN-401 returns within hours of every reconnect. Collect:

- the connection id (`con_...`), the connector name and the connected account;
- the time of the first CONN-401 or CONN-403, in UTC, and a run id that shows it;
- the full third-party message from the step log and the result of **Test connection**;
- what changed in the third-party app around that time, if the client knows.

Never ask the client for passwords, tokens or secrets, and never paste them into a ticket.
