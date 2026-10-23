---
id: nimbus-connector-slack
title: Slack Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-05-04
owner: Integrations Team
---

The Slack connector installs the OmniCorp Nimbus app into a Slack workspace so that workflows can post messages, open channels and react to what people say. It authorises with OAuth 2.0 through the standard Slack app install and receives events from Slack's Events API, so its triggers are push triggers. It has been in the catalogue since 3.0.0.

Messages are posted by the Nimbus bot user, shown in Slack as **Nimbus**, not by the person who installed the app.

## Prerequisites

The person installing the app needs permission to install apps in the Slack workspace. On workspaces where app approval is turned on, a Slack Workspace Owner or an approved App Manager must approve the request under **Manage apps > Requests** first; until then the install stops with "This app requires approval". On Enterprise Grid, the app is installed per workspace, not at the organisation level.

On the Nimbus side, a Builder or Admin creates the connection, and the connector counts towards the workspace's active-connector limit once a running workflow uses it (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

The app requests these bot token scopes:

| Scope | Why Nimbus needs it |
|---|---|
| `chat:write` | Post messages as the Nimbus bot |
| `channels:read`, `groups:read` | List public and private channels in the channel picker |
| `channels:history`, `groups:history` | Receive message events from channels the bot is in |
| `reactions:read` | Receive reaction events |
| `channels:manage`, `groups:write` | Create channels and invite users |
| `users:read`, `users:read.email` | Look up members by email address for invites and mentions |

## Creating the connection

1. In the Nimbus console, go to **Connections > New connection** and choose **Slack**.
2. Name the connection after the Slack workspace, for example `Slack – acme.slack.com`.
3. Click **Authorise**. Slack shows the permissions page for OmniCorp Nimbus.
4. Check the workspace shown in the top-right corner of that page, switch if needed, and click **Allow**.
5. Nimbus shows the Slack workspace name and team id with the status **Connected**.
6. Invite the bot to every private channel a workflow will read from or post to: in the channel, type `/invite @Nimbus`.

Public channels need no invite for posting. To receive message events from a public channel, though, the bot still has to be a member, so invite it there too.

## Triggers and actions

| Name | Kind | Notes |
|---|---|---|
| New message in channel | Push trigger | Fires for each new message in the chosen channel. Options: **Include thread replies** and **Include bot messages**, both off by default. |
| Reaction added | Push trigger | Fires when a chosen emoji (e.g. `white_check_mark`) is added to a message in the channel; the output includes the message timestamp and the reacting user. |
| Post message | Action | Plain text with Slack mrkdwn; optional thread timestamp to reply in a thread. |
| Post message with Block Kit | Action | Takes a `blocks` array; the plain `text` field is still required as the notification fallback. |
| Create channel | Action | Public or private; returns the new channel id. |
| Invite users to channel | Action | Takes Slack user ids or email addresses. |

Leaving **Include bot messages** off stops a workflow from triggering itself when it posts to the channel it listens on.

## Field mapping

A Block Kit step takes the blocks as JSON, with Nimbus expressions inside string values. Mention a user with `<@U…>` and a channel with `<#C…>`; Nimbus doesn't translate names to ids, so look users up first with an email address.

```json
{
  "channel": "C05QX7K2M1A",
  "text": "Run {{steps.load.output.run_id}} failed",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*{{trigger.body.workflow_name}}* failed at {{now()}}\nOwner: <@{{steps.lookup_owner.output.user_id}}>"
      }
    },
    {
      "type": "actions",
      "elements": [
        { "type": "button", "text": { "type": "plain_text", "text": "Open run" },
          "url": "https://app.nimbus.omnicorp.example/runs/{{steps.load.output.run_id}}" }
      ]
    }
  ]
}
```

Use the channel id rather than the name in **channel**: ids survive a channel rename, names don't. The channel picker in the builder fills in the id for you.

## Limits and behaviour

Message events arrive within seconds. Slack expects every event to be acknowledged quickly, so Nimbus acknowledges first and starts the run afterwards; a slow workflow never causes Slack to resend the event. If Slack does resend one, Nimbus recognises the event id and doesn't start a second run.

- A message can hold up to 40,000 characters of text and up to 50 blocks; longer messages are cut by Slack.
- File shares arrive with the file's metadata only. Download links need the bot to be in the channel, and files passed between steps are limited to 100 MB.
- Channel and user lookups are paged with Slack's cursor; the picker loads the first 1,000 channels and offers a search for the rest.
- When Slack throttles the app, it answers HTTP 429 with its own `Retry-After`. The step shows CONN-429 and Nimbus waits at least that long before retrying.
- Other failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes.

## Troubleshooting

| Code | Slack error | Cause and fix |
|---|---|---|
| CONN-401 | `token_revoked`, `account_inactive` | The app was removed from the workspace. Click **Reconnect** and install it again. |
| CONN-403 | `not_in_channel` | The bot isn't a member of the channel. Run `/invite @Nimbus` there. |
| CONN-403 | `missing_scope` | The install predates a scope the action needs. Reconnect to approve it. |
| CONN-404 | `channel_not_found` | The channel was deleted, or it is private and the bot was never invited; Slack hides private channels from non-members. |
| CONN-404 | `users_not_found` | An email address in **Invite users** doesn't belong to a workspace member. |
| WF-400 | – | `text` resolved to empty; Slack needs it even when `blocks` are sent. |
| (step error) | `invalid_blocks` | The Block Kit JSON doesn't validate. Paste it into Slack's Block Kit Builder to find the bad block. |
| (step error) | `name_taken` | **Create channel** used a name that exists, possibly archived. |

For the legacy platform, see [Slack Connector (v2)](nimbus-v2-connector-slack.md).
