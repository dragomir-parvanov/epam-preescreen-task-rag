---
id: nimbus-connector-intercom
title: Intercom Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-26
owner: Integrations Team
---

The Intercom connector, released in 3.2.0, connects workflows to a client's Intercom workspace. Support teams use it to route new conversations into a ticketing tool, to post an automatic reply or internal note when a conversation matches a rule, to tag conversations from data held elsewhere, and to create contacts in Intercom when someone signs up in the client's own product.

Its triggers are push triggers: Intercom notifies Nimbus as soon as a conversation starts or closes, so runs begin within seconds. The connection is made with OAuth 2.0 by an Intercom admin.

## Prerequisites

- **An Intercom teammate who can install apps.** The person who authorises the connection must be an Intercom admin whose permissions include **Can install, configure and delete apps**. Without it, Intercom shows an error on the consent screen and no connection is created.
- **The Intercom hosting region.** Intercom hosts workspaces in the US, the EU or Australia. The connection form asks for the region, and choosing the wrong one makes the OAuth step fail with an unknown workspace error.
- **Custom data attributes created in advance.** Any custom attribute a workflow writes must already exist in Intercom (see Field mapping).
- **A Builder or Admin in Nimbus** to create the connection.
- **Plan Tier capacity.** The connector counts as an active connector once an active workflow uses it; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md) for the limit on each tier.

## Creating the connection

1. In the Nimbus admin console, go to **Connections > New connection** and choose **Intercom**.
2. Select the **Region** (US, EU or Australia) and give the connection a name, for example `Intercom – Support`.
3. Click **Connect with Intercom**. A new window opens on Intercom's sign-in page.
4. Sign in as the installing admin and, if the account belongs to several Intercom workspaces, choose the right one.
5. Review the requested permissions and click **Authorize access**. Nimbus asks for:
   - Read and list users and companies
   - Write users and companies
   - Read conversations
   - Write conversations
   - Read and write tags
6. Back in Nimbus, the connection shows **Connected** with the Intercom workspace name. Click **Test** to confirm.

The OAuth token is encrypted and never shown again. The installing admin's later permission changes don't affect the connection, but uninstalling the OmniCorp Nimbus app under **Settings > Apps > Installed apps** in Intercom revokes it immediately.

## Triggers and actions

| Name | Type | Details |
|---|---|---|
| New conversation | Push trigger | Fires when a contact starts a conversation. Output includes the conversation id, the contact, the first message (`source.body`) and the inbox it arrived in. |
| Conversation closed | Push trigger | Fires when a teammate or a workflow in Intercom closes a conversation. Output includes the closing admin and the conversation's tags. |
| Create contact | Action | Creates a user or lead with standard and custom data attributes. Returns the contact id. |
| Reply to conversation | Action | Posts a reply or an internal note as a chosen admin. |
| Add tag | Action | Adds a tag to a contact or a conversation. With **Create tag if missing** on, an unknown tag name is created first. |

**Reply to conversation** needs an **Admin ID**, the Intercom teammate the message appears to come from. Pick a dedicated teammate such as "Support Bot" so customers and agents can tell automated replies apart. Set **Message type** to `comment` for a reply the customer sees, or `note` for an internal note.

When a workflow with an Intercom trigger is activated, Nimbus registers a webhook subscription for that trigger in the client's Intercom workspace; deactivating the workflow removes it. Nimbus verifies the signature Intercom puts on each notification with the app's client secret and ignores notifications that fail the check.

## Field mapping

Intercom splits contact fields into standard attributes (`email`, `name`, `phone`, `external_id`, `role`) and custom data attributes, which sit in a `custom_attributes` object. A custom attribute has to be created in Intercom before a workflow writes to it, under **Settings > Data > People** (or **Companies** for company data), with the type it will hold: text, number, true or false, list, or date.

A **Create contact** step fed by an inbound webhook from the client's sign-up service:

```json
{
  "role": "user",
  "external_id": "{{trigger.body.account.user_id}}",
  "email": "{{lower(trigger.body.account.email)}}",
  "name": "{{trigger.body.account.full_name}}",
  "custom_attributes": {
    "plan_name": "{{trigger.body.account.plan}}",
    "seats_purchased": "{{trigger.body.account.seats}}",
    "trial_ends_at": "{{trigger.body.account.trial_end_unix}}"
  }
}
```

Attribute names in `custom_attributes` are the names shown in Intercom's data settings, and they are case-sensitive. Date attributes take a Unix timestamp in seconds; if the source sends ISO 8601 timestamps, convert them in a transform step before **Create contact**. A value of the wrong type, such as text in a number attribute, is rejected by Intercom.

Set `external_id` whenever the client has a stable user id. It prevents duplicate contacts when the same person signs up twice with different email addresses, and it lets later workflows find the contact without searching by email.

## Limits and behaviour

- **Push delivery.** Intercom sends each event once to Nimbus and a run starts within seconds. Each notification starts one run, which counts towards the workspace's monthly workflow runs.
- **Conversation parts.** The **New conversation** trigger carries only the opening message. A workflow that needs the full thread should read it in a later step, because replies arrive after the trigger fires.
- **Message bodies.** Replies accept simple HTML (`<p>`, `<b>`, `<a>`, `<br>`). Other markup is stripped by Intercom.
- **Throttling.** Intercom limits how quickly one app can call a workspace. When it throttles Nimbus, the step reports CONN-429 and is retried after a back-off.
- **Retries.** The default is 3 retries, after 30 seconds, 2 minutes and 10 minutes, configurable from 0 to 5 per step. Consider 0 retries for **Reply to conversation** if a duplicate reply would confuse the customer.
- **Credentials in steps.** Keep any extra tokens a workflow needs, such as a ticketing system's key, in the secrets vault and reference them as `{{secrets.NAME}}`.

## Troubleshooting

| Error | Cause in Intercom | Fix |
|---|---|---|
| CONN-401 | The OmniCorp Nimbus app was uninstalled from the Intercom workspace. | Click **Reconnect** and authorise again as an admin who can install apps. |
| CONN-403 | The connection lacks a permission, for example after Intercom added a new scope. | Reconnect so the admin approves the current permission list. |
| CONN-404 | The conversation, contact or admin id doesn't exist, or a custom data attribute hasn't been created. | Check the id, or create the attribute under **Settings > Data**. |
| CONN-429 | Intercom throttled the app. | Nimbus backs off and retries the step. |
| WF-400 | `email` and `external_id` both resolved to empty on **Create contact**. | Map at least one identifier. |
| No runs from a trigger | The webhook subscription was removed in Intercom's developer settings. | Deactivate and reactivate the workflow to register it again. |
