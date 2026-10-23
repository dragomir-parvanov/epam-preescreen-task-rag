---
id: nimbus-connector-jira-cloud
title: Jira Cloud Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-04-13
owner: Integrations Team
---

The Jira Cloud connector connects a Nimbus workspace to one Atlassian site, such as `acme.atlassian.net`, so that workflows can open issues, move them through their workflow and comment on them, and start when issues change. It authorises with OAuth 2.0 (Atlassian's three-legged flow) and receives issue events as push triggers. It has been available since 3.0.0. Jira Data Center and Server aren't supported by this connector; use [HTTP Request Connector](nimbus-connector-http-request.md) for those.

## Prerequisites

| What | Requirement |
|---|---|
| Atlassian account | A licensed Jira user on the site. A dedicated account such as `nimbus-integration@acme.com` is recommended, since every comment and transition is shown under its name. |
| Project permissions | **Browse Projects** for triggers; **Create Issues**, **Edit Issues**, **Transition Issues** and **Add Comments** for the matching actions. They are granted through the project's permission scheme. |
| App access | If the site restricts third-party apps under **Atlassian Administration > Security > Connected apps**, an organisation admin must allow OmniCorp Nimbus. |
| Webhooks | Push triggers need the connecting account to be a Jira user with access to the projects being watched; no Jira admin rights are needed. |
| Nimbus | A Builder or Admin creates the connection; it counts towards the active-connector limit of the Plan Tier ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)). |

The consent screen asks for the scopes `read:jira-work`, `write:jira-work`, `read:jira-user`, `manage:jira-webhook` and `offline_access`.

## Creating the connection

1. Go to **Connections**, click **New connection** and pick **Jira Cloud**.
2. Enter a name, for example `Jira – acme.atlassian.net`.
3. Click **Authorise** and sign in to Atlassian with the integration account.
4. If the account can reach several sites, choose the site from the **Use app on** list, then click **Accept**.
5. Nimbus shows the site URL and cloud id with the status **Connected**.
6. Click **Test connection**; Nimbus lists the projects the account can browse.

One connection reaches one site. A client with a second site creates a second connection.

## Triggers and actions

| Name | Kind | Behaviour |
|---|---|---|
| Issue created | Push trigger | Fires for each new issue. An optional **JQL filter** limits it, e.g. `project = OPS AND issuetype = Incident`. |
| Issue updated | Push trigger | Fires on any field change; the output includes a `changelog` listing old and new values. |
| Issue transitioned | Push trigger | Fires only when the status changes; choose **To status** to narrow it, e.g. `Done`. |
| Create issue | Action | Needs project key, issue type and summary; returns the issue key and id. |
| Transition issue | Action | Moves an issue by transition name or id, optionally setting fields on the transition screen. |
| Add comment | Action | Adds a comment in Atlassian Document Format. For Jira Service Management projects, **Internal** makes it visible to agents only. |

Issue updated fires on the integration account's own edits too. A workflow that edits the issue it was triggered by should check `{{trigger.body.user.accountId}}` in a condition step and stop when it is the integration account.

## Field mapping

Standard fields use their Jira names (`summary`, `priority`, `labels`). Custom fields are mapped by **field id**, `customfield_` followed by a number. Find the id under **Settings > Issues > Custom fields**: open the field's menu and the id is in the address of the edit page. Select-list fields take an object with `value`, user fields take an `accountId`, and descriptions and comments take Atlassian Document Format (ADF), not plain text or wiki markup.

```json
{
  "project": { "key": "OPS" },
  "issuetype": { "name": "Incident" },
  "summary": "Failed sync for {{trigger.body.customer_name}}",
  "priority": { "name": "High" },
  "labels": ["nimbus", "{{lower(trigger.body.region)}}"],
  "customfield_10042": { "value": "{{default(trigger.body.tier, 'Standard')}}" },
  "customfield_10057": "{{trigger.body.order_id}}",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      { "type": "paragraph", "content": [
        { "type": "text", "text": "Run {{trigger.body.run_id}} failed at step {{trigger.body.step}}." }
      ] }
    ]
  }
}
```

The step editor offers a **Plain text** switch for description and comment fields; when it is on, Nimbus wraps the text in a single ADF paragraph for you.

## Limits and behaviour

Nimbus registers a Jira webhook for each active workflow with a push trigger and removes it when the workflow is deactivated. Jira expires these webhooks after 30 days; Nimbus extends them before that happens, so nothing needs doing on the client side. Events normally start a run within seconds.

- Searches that the builder runs for pickers are paged 50 issues at a time.
- Attachments added through a later step can be up to 100 MB in Nimbus, but the site's own **Attachment settings** maximum applies first.
- A failed action is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Create issue isn't idempotent, so a retry after a timeout can create a second issue; set a unique label or custom field and check for it first if that matters.
- When Atlassian throttles the site, the step shows CONN-429 and Nimbus backs off before retrying.

## Troubleshooting

| Code | Cause in Jira | Fix |
|---|---|---|
| CONN-401 | The account removed OmniCorp Nimbus under **Atlassian account > Connected apps**, lost its product access, or the refresh token expired after long inactivity. | **Reconnect** with the integration account. |
| CONN-403 | The account lacks a project permission, e.g. **Transition Issues**. | Add it to the project's permission scheme. |
| CONN-404 | The issue key doesn't exist or the account can't browse the project. Jira hides issues it can't see. | Check the key and the account's **Browse Projects** permission. |
| WF-400 | A required field, such as a mandatory custom field on the create screen, resolved to empty. | Map the field or add `default()`. |
| (step error) "Transition id is not valid" | The issue's current status has no such transition. | Use the transition name from the issue's workflow, or add a condition on status. |
| (step error) "Operation value must be an Atlassian Document" | Description was sent as plain text. | Use ADF or turn on **Plain text**. |
