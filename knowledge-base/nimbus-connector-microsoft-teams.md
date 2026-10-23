---
id: nimbus-connector-microsoft-teams
title: Microsoft Teams Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-19
owner: Integrations Team
---

The Microsoft Teams connector, added in 3.3.0, lets workflows post to Teams channels and chats and start when a new message appears in a channel. It authorises through Microsoft Entra ID with OAuth 2.0 and needs tenant-wide admin consent once per tenant. Approval steps also use it to tell approvers that a decision is waiting.

The connection acts as the Microsoft 365 account that signs in, so posts appear under that account's name. Use a dedicated, licensed service account such as `nimbus-notify@contoso.com` rather than a person's own account.

## Prerequisites

You need three things before you start:

- **Admin consent in Entra ID.** A Global Administrator or Privileged Role Administrator of the tenant must grant consent to the OmniCorp Nimbus enterprise application. Without it, ordinary users see "Need admin approval" (AADSTS90094) when they try to authorise.
- **A Teams-licensed account** that is a member of every team the workflows post to. Membership is what lets it read and post in that team's channels.
- **A Nimbus Builder or Admin**, with room under the Plan Tier's active-connector limit ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)). To use the connector in approval steps, the workspace needs a tier with approval steps.

The consent covers these Microsoft Graph delegated permissions:

| Permission | Purpose |
|---|---|
| `Team.ReadBasic.All`, `Channel.ReadBasic.All` | Fill the team and channel pickers |
| `ChannelMessage.Send` | Post to channels |
| `ChannelMessage.Read.All` | Receive new channel messages for the trigger |
| `Chat.ReadWrite` | Send one-to-one and group chat messages |
| `User.ReadBasic.All` | Resolve recipients by user principal name |
| `offline_access` | Keep the connection signed in with a refresh token |

## Creating the connection

1. An Entra administrator opens **Connections > New connection > Microsoft Teams** in Nimbus, clicks **Grant admin consent**, signs in and accepts the permissions for the organisation. This is needed once per tenant.
2. Sign out of Microsoft, then, as a Builder or Admin in Nimbus, start **New connection > Microsoft Teams** again.
3. Name the connection, for example `Teams – notifications account`.
4. Click **Authorise** and sign in with the service account. Because consent is already granted, no further prompt appears.
5. Nimbus shows the tenant id, the signed-in account and the status **Connected**.
6. Click **Test connection**; Nimbus lists the teams the account belongs to.

Conditional Access policies apply to the service account like any other. If a policy requires a compliant device or MFA for every sign-in, exclude the account from that policy or authorise from a device that meets it.

## Triggers and actions

| Name | Type | What it does |
|---|---|---|
| New channel message | Push trigger | Starts a run for each new top-level message in the chosen team and channel. Replies are included only if **Include replies** is on. |
| Post to channel | Action | Posts an HTML-formatted message to a channel, or a reply to a message id. |
| Send chat message | Action | Sends to an existing chat by id, or starts a one-to-one chat with a user principal name. |
| Post adaptive card | Action | Posts an adaptive card to a channel or chat. |

### Approval notifications

When an approval step has **Notify via** set to a Microsoft Teams connection, Nimbus sends each approver a chat message with an adaptive card that shows the request and an **Open in Nimbus** button. The approver decides in the Nimbus **Approvals** inbox; the card doesn't record the decision itself. An approval that nobody decides within 7 days expires, and the run fails with WF-410. Approvers must be members of the same tenant as the connection.

## Field mapping

Adaptive cards are written as JSON in the **Card** field, with Nimbus expressions inside string values. Teams renders card schema version 1.5; use an older `version` if some clients are on older Teams builds.

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "size": "Medium", "weight": "Bolder",
      "text": "New order {{trigger.body.order_id}}" },
    { "type": "FactSet", "facts": [
      { "title": "Customer", "value": "{{trigger.body.customer.name}}" },
      { "title": "Amount", "value": "{{trigger.body.total}}" },
      { "title": "Received", "value": "{{now()}}" }
    ] }
  ],
  "actions": [
    { "type": "Action.OpenUrl", "title": "Open in ERP",
      "url": "https://erp.contoso.example/orders/{{trigger.body.order_id}}" }
  ]
}
```

Mentions in **Post to channel** use the user principal name in the **Mentions** list; Nimbus builds the `<at>` tags.

## Limits and behaviour

The trigger is pushed: Nimbus subscribes to change notifications for the channel when the workflow is activated, renews the subscription automatically before it lapses, and removes it on deactivation. New messages normally start a run within seconds. If a renewal fails, for example because the account lost membership of the team, the connection shows **Needs attention**.

A Teams message, including an adaptive card, can be at most about 28 KB. Larger content should be stored elsewhere and linked; files passed between Nimbus steps can be up to 100 MB, but Teams posts don't carry attachments from this connector. Picker lists of teams and channels are paged and load as you scroll. When Microsoft Graph throttles the tenant, the step shows CONN-429 and Nimbus backs off and retries it. Other failures are retried 3 times by default.

## Troubleshooting

| Error | Likely cause | Resolution |
|---|---|---|
| AADSTS90094 / AADSTS65001 during **Authorise** | Admin consent hasn't been granted, or was granted before a new permission was added. | An Entra administrator repeats step 1 of Creating the connection. |
| CONN-401 | The service account's password was reset, its sessions were revoked, or consent was removed. | Click **Reconnect** and sign in again. |
| CONN-403 | The account isn't a member of the team, or the channel is a private or shared channel it can't see. | Add the account to the team or channel. |
| CONN-404 | The channel or chat was deleted, or the team archived. | Pick a current channel in the step. |
| CONN-429 | Microsoft Graph throttled the request. | No action; Nimbus retries. |
| WF-410 | An approval card went unanswered for 7 days. | Re-run the workflow, or add more approvers. |
