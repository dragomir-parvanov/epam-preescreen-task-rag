---
id: nimbus-connector-zendesk
title: Zendesk Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-11-24
owner: Integrations Team
---

The Zendesk connector connects a Nimbus workspace to a Zendesk Support account so that workflows can open and update tickets, add public replies or internal notes, and start as soon as a ticket is created or changed. It authenticates with a Zendesk API token together with the email address of the agent the token acts for, and it has been available since 3.0.0.

Every change Nimbus makes appears in the ticket's events as made by that agent. Most clients create a dedicated agent such as `nimbus@acme.zendesk.example` for this.

## Prerequisites

1. **Token access turned on.** In Zendesk, **Admin Center > Apps and integrations > APIs > Zendesk API > Settings**, the **Token access** switch must be on.
2. **An API token.** On the same page, click **Add API token**, give it a description such as `OmniCorp Nimbus`, and copy it; Zendesk shows it once.
3. **An agent account.** The connection's email must belong to an agent with access to the groups and brands the workflows touch. For push triggers the agent must be a Zendesk **Admin**, because Nimbus creates a Zendesk webhook for each triggered workflow.
4. **Nimbus access.** A Builder or Admin creates the connection; the connector counts towards the active-connector limit of the workspace's Plan Tier ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

Light agents can be used for actions that only add internal notes, but they can't add public comments or change ticket fields.

## Creating the connection

1. In Nimbus, go to **Connections** and click **New connection**.
2. Choose **Zendesk** and enter a **Connection name**.
3. Enter the **Subdomain**, the part before `.zendesk.com` (for example `acme`).
4. Enter the **Agent email** and paste the **API token**.
5. Click **Save**, then **Test connection**. Nimbus calls Zendesk's current-user endpoint and shows the agent's name and role with the status **Connected**.

A wrong email and token pair fails the test with "Couldn't authenticate you". Zendesk expects the email followed by `/token` as the user name; Nimbus adds that suffix itself, so don't type it.

## Triggers and actions

| Trigger or action | Kind | What you set |
|---|---|---|
| Ticket created | Push trigger | Optional filters: brand, group, form, tags. |
| Ticket updated | Push trigger | Optional **Changed field** (status, priority, assignee, a custom field) to fire only on that change. |
| Create ticket | Action | Subject, first comment, requester email, and any ticket fields. |
| Update ticket | Action | Ticket id and the fields to change; unmapped fields are left alone. |
| Add comment | Action | Ticket id, body, and **Public**. Off makes it an internal note visible to agents only. |
| Set custom fields | Action | Ticket id and a list of custom field ids and values. |

When a workflow with a push trigger is activated, Nimbus creates a webhook in Zendesk under **Admin Center > Apps and integrations > Webhooks**, named `OmniCorp Nimbus – <workflow name>`, subscribed to Zendesk's ticket events. Deactivating the workflow deletes it. Don't edit or delete these webhooks by hand; if one is removed, deactivate and reactivate the workflow to recreate it.

## Field mapping

Custom ticket fields are set by numeric **field id**. Find it under **Admin Center > Objects and rules > Tickets > Fields**; the id is shown in the field list. Drop-down fields take the option's **tag**, not its display name, and checkbox fields take `true` or `false`.

```json
{
  "ticket_id": "{{trigger.body.ticket.id}}",
  "status": "open",
  "priority": "{{default(trigger.body.priority, 'normal')}}",
  "tags": ["nimbus", "renewal"],
  "custom_fields": [
    { "id": 360012345678, "value": "{{trigger.body.contract_number}}" },
    { "id": 360012345679, "value": "tier_gold" },
    { "id": 360012345680, "value": true }
  ],
  "comment": {
    "body": "Renewal record {{steps.crm.output.id}} created by Nimbus.",
    "public": false
  }
}
```

Note that sending `tags` replaces the ticket's tags. To add one without losing the others, use **Update ticket** with **Add tags** instead of the `tags` field.

## Limits and behaviour

| Topic | Behaviour |
|---|---|
| Trigger delivery | Push; runs start within seconds of the ticket change. |
| Duplicate events | Nimbus ignores a repeated Zendesk event id, so one change starts one run. |
| Self-triggering | Updates made by the connection's own agent are skipped by **Ticket updated** unless **Include own changes** is on. |
| Attachments | Nimbus passes files up to 100 MB between steps, but Zendesk's own attachment limit for the account applies when uploading. |
| Closed tickets | A ticket in **Closed** status can't be updated; create a follow-up ticket instead. |
| Update conflicts | If an agent saves the same ticket at the same moment, Zendesk rejects the step with a conflict and Nimbus retries it. |
| Retries | 3 by default, after 30 seconds, 2 minutes and 10 minutes. |

Ticket searches used by lookups are paged with Zendesk's cursor pagination, 100 tickets a page. When Zendesk throttles the account the step shows CONN-429; Nimbus waits for Zendesk's `Retry-After` and tries again.

## Troubleshooting

| Code | Cause | Fix |
|---|---|---|
| CONN-401 | The API token was deleted, **Token access** was turned off, or the agent was downgraded to an end user. | Create a new token, update the connection, and click **Test connection**. |
| CONN-403 | The agent has no access to the ticket's group or brand, or a light agent tried a public comment or field change. | Widen the agent's group access or use a full agent. |
| CONN-404 | The ticket id doesn't exist, or the ticket was deleted or archived. | Check the id; archived tickets can't be updated. |
| CONN-429 | Zendesk throttled the account. | No action; Nimbus retries. |
| WF-400 | A required ticket field resolved to empty. | Map the field, or give a default. |
| (step error) "Status: closed prevents ticket update" | The ticket is closed. | Create a follow-up ticket. |
