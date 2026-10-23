---
id: nimbus-connector-marketo
title: Marketo Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-12-01
owner: Integrations Team
---

The Marketo connector, available since release 3.1.0, connects workflows to Adobe Marketo Engage. It is mostly used to keep leads in step between Marketo and a CRM or product database: new leads and lead activity start runs in Nimbus, and Nimbus pushes leads back into Marketo, adds them to static lists and requests smart campaigns.

The connector talks to Marketo's REST API with the credentials of a LaunchPoint custom service. Marketo doesn't push events to the connector, so both triggers poll.

## Prerequisites

The client's Marketo administrator needs to prepare three things before the connection is made:

- **An API role and an API-only user.** Under **Admin > Users & Roles > Roles**, create a role with **Access API** and the API permissions the workflows need: **Read-Write Lead** for syncing leads and adding them to lists, **Read-Only Activity** for the activity trigger, and **Execute Campaign** for requesting campaigns. Then invite a user with **API Only** ticked and give it that role.
- **A LaunchPoint custom service.** Under **Admin > Integration > LaunchPoint**, click **New > New Service**, choose **Custom** as the service, name it `OmniCorp Nimbus`, and select the API-only user. Marketo then issues a client ID and client secret for the service.
- **The REST endpoint.** Under **Admin > Integration > Web Services**, the **REST API** panel shows the endpoint, built from the instance's Munchkin ID, for example `https://482-QZT-719.mktorest.com/rest`.

On the Nimbus side, the person creating the connection needs the Builder or Admin role. The connector counts towards the workspace's active connectors once an active workflow uses it; [Plan Tiers and Entitlements](nimbus-plan-tiers.md) lists the limits.

## Creating the connection

1. In Marketo, open **Admin > Integration > LaunchPoint**, select the `OmniCorp Nimbus` service and click **View Details**. Copy the **Client Id** and **Client Secret**.
2. In the Nimbus admin console, go to **Connections**, click **New connection** and choose **Marketo**.
3. Paste the REST endpoint into **Endpoint URL**. Enter it without a trailing slash; Nimbus derives the identity URL from it.
4. Paste the client ID and client secret.
5. Click **Save and test**. Nimbus requests an access token and reads one lead field description to confirm the role has API access.

Nimbus requests a new access token whenever the current one expires, so the connection doesn't need reconnecting when Marketo's short-lived tokens run out. It does need reconnecting if the client secret is reset in LaunchPoint or the API-only user is deactivated.

## Triggers and actions

| Name | Kind | Behaviour |
|---|---|---|
| New lead | Polling trigger | One run per lead created since the last poll, with the lead fields chosen in the trigger. |
| New lead activity | Polling trigger | One run per activity of the selected activity types (for example **Fill Out Form**, **Click Email**, **Change Data Value**). |
| Sync lead | Action | Creates or updates a lead, matched on a lookup field (`email` by default). Returns the lead id and whether it was created or updated. |
| Add to list | Action | Adds up to 300 lead ids to a static list in one step. |
| Request campaign | Action | Requests a smart campaign for up to 100 leads, optionally passing My Tokens. |

**Request campaign** works only with a smart campaign whose smart list contains the **Campaign is Requested** trigger with **Source: Web Service API**. Any other smart campaign returns an error from Marketo and the step fails with CONN-404, because Marketo reports the campaign as not found for API requests.

## Field mapping

Marketo fields are referenced by their REST API name, which differs from the label in the Marketo UI: **Job Title** is `title`, **Company Name** is `company`, and custom fields carry the name the administrator gave them in Field Management, such as `nimbusAccountTier`. The field picker in the step editor shows both.

A **Sync lead** step that takes a sign-up from an inbound webhook trigger:

```json
{
  "lookupField": "email",
  "lead": {
    "email": "{{lower(trigger.body.user.email)}}",
    "firstName": "{{trigger.body.user.first_name}}",
    "lastName": "{{trigger.body.user.last_name}}",
    "company": "{{default(trigger.body.account.name, 'Unknown')}}",
    "leadSource": "Product sign-up",
    "nimbusAccountTier": "{{trigger.body.account.tier}}"
  }
}
```

To pass My Tokens to **Request campaign**, map each token by its full name including the braces and the `my.` prefix, for example `{{my.Webinar Date}}`. The step editor escapes these so Nimbus sends them to Marketo literally instead of evaluating them as Nimbus expressions.

## Limits and behaviour

**Daily API quota.** Every Marketo subscription has a daily API quota shared by all of its integrations, and the quota resets at midnight in Marketo's own time zone (US Central), not in the workspace time zone. Nimbus calls count towards it like any other integration. Polling triggers make a few calls on every poll, and each **Sync lead** step makes at least one. The client can see consumption under **Admin > Integration > Web Services > API Call Information**. When the quota is used up, Marketo rejects every call until it resets; Nimbus treats this as CONN-429, backs off and retries, and the step fails once its last retry is used.

**Polling.** Both triggers poll every 5 minutes. Activity polling uses Marketo's paging token, so no activity is skipped between polls, but a rush of form fills after an email send arrives as a batch of runs rather than one at a time.

**Concurrency.** Marketo also caps how many calls it handles at once per subscription. Several workflows calling Marketo at the same moment can see CONN-429 even with quota left.

**Retries.** A failed step is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes, and the count can be set from 0 to 5 per step. Consider lowering retries on high-volume **Sync lead** steps to save quota on days when it is tight.

## Troubleshooting

| Error | What Marketo reported | Fix |
|---|---|---|
| CONN-401 | The client secret was reset, or the API-only user was deactivated. | Copy the new secret from LaunchPoint and click **Reconnect**. |
| CONN-403 | The API role lacks the permission for the call, for example **Execute Campaign**. | Add the permission to the role under **Admin > Users & Roles**. |
| CONN-404 | The list, lead or campaign id doesn't exist, or the campaign isn't requestable through the API. | Check the id and the campaign's **Campaign is Requested** trigger. |
| CONN-429 | The daily quota is used up, or too many calls were in flight. | Check **API Call Information**; spread or reduce calls; wait for the quota reset. |
| WF-400 | The lookup field resolved to empty. | Make sure the mapped `email` (or chosen lookup field) always has a value. |
