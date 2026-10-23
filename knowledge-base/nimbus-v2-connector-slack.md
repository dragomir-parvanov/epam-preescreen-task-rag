---
id: nimbus-v2-connector-slack
title: Slack Connector (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: guide
status: deprecated
last_updated: 2024-11-18
owner: Integrations Team
---

The legacy Slack connector posts messages into Slack channels from a workflow. It is deliberately simple: each connection is one Slack incoming-webhook URL, which belongs to exactly one channel, and the connector has a single action that posts a plain-text or markdown message to that channel. It has no triggers and can't read anything from Slack.

Clients typically use it for run notifications, daily digests and alerts. For anything richer, such as Block Kit layouts, posting to a channel chosen at run time, or starting workflows from Slack events, the client needs the current connector described in [Slack Connector](nimbus-connector-slack.md). The legacy platform's support timeline is in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Prerequisites

- **Permission to add apps in the Slack workspace.** Incoming webhooks belong to a Slack app. Either the client already has an internal app for notifications, or someone allowed to install apps creates one. Workspaces that require app approval need a Slack admin to approve it.
- **One target channel per connection.** Decide which channels the workflows post to. Each needs its own webhook URL and therefore its own Nimbus connection.
- **Private channels need care.** A webhook can post to a private channel only if it was created for that channel by a member of it. A webhook can't be pointed at a private channel afterwards.
- **An Admin in the Nimbus workspace**, because connections are added under **Admin > Connections**.

## Creating the connection

First create the webhook in Slack:

1. Go to `https://api.slack.com/apps` and open the client's notification app, or click **Create New App > From scratch**, name it (for example `Nimbus Alerts`) and pick the workspace.
2. Under **Features > Incoming Webhooks**, switch **Activate Incoming Webhooks** on.
3. Click **Add New Webhook to Workspace**, choose the channel, and click **Allow**.
4. Copy the webhook URL. It has the form `https://hooks.slack.com/services/T0XXXXXXX/B0XXXXXXX/<secret>`.

Then add it to Nimbus:

5. In the Nimbus admin console, open **Admin > Connections** and click **Add connection**.
6. Choose **Slack**, give the connection a name that includes the channel (for example `Slack – #finance-alerts`), and paste the webhook URL.
7. Click **Save**, then **Send test message**. A short test message appears in the channel.

The webhook URL is the credential: anyone who has it can post to the channel. It is stored on the connection and can't be read back. To replace it, for example after the client regenerates it, an Admin opens the connection under **Admin > Connections**, clicks **Edit** and pastes the new URL.

## Triggers and actions

| Name | Type | Details |
|---|---|---|
| Post message | Action | Posts `text` to the connection's channel, as plain text or Slack markdown. |

That is the whole connector. In particular:

- **No triggers.** Slack messages, reactions or slash commands can't start a workflow.
- **No Block Kit.** Buttons, sections, images and other blocks aren't supported; only the `text` field is sent.
- **No channel choice at run time.** A message always goes to the channel the webhook was created for. To post to several channels, add one connection per channel and one **Post message** step per connection.
- **No threads, edits or deletes.** Each post is a new top-level message.

## Field mapping

The step has one field, **Message**, which accepts expressions and Slack's markdown (`mrkdwn`): `*bold*`, `_italic_`, `~strike~`, inline `` `code` ``, links written as `<https://example.com|label>`, and user mentions as `<@U024BE7LH>` using the member ID from the person's Slack profile. Plain `@name` text doesn't notify anyone.

A failure alert built from a workflow's previous step:

```json
{
  "text": ":rotating_light: *Invoice sync failed* for {{trigger.body.customer_name}}\nRun: <https://app.nimbus.omnicorp.example/runs/{{trigger.body.run_id}}|open in Nimbus>\nOwner: <@{{steps.lookup_owner.output.slack_member_id}}>"
}
```

Line breaks are written as `\n`. To post literal text without markdown, switch **Format** on the step from **Markdown** to **Plain text**; Nimbus then escapes `*`, `_` and `<` so they appear as typed.

Before building a workflow, a client can confirm a webhook works from any terminal:

```bash
curl -X POST -H 'Content-Type: application/json' \
  --data '{"text":"Test from the Nimbus Slack connection"}' \
  https://hooks.slack.com/services/T0XXXXXXX/B0XXXXXXX/<secret>
```

## Limits and behaviour

| Item | Behaviour |
|---|---|
| Message length | Slack truncates text after 40,000 characters; keep alerts well under 4,000 so they stay readable. |
| Sender name and icon | Set by the Slack app; a `username` or `icon_emoji` in the step is ignored by Slack. |
| Retries | None: a failed step fails the run, which is started again by hand. |
| Run history | Kept for 30 days, including the text that was posted. |

Starting a failed run again by hand can post the same message twice if Slack received the first attempt but its reply didn't reach Nimbus. Check the channel before rerunning a workflow whose alerts page people.

Changes on the Slack side reach Nimbus only through failed steps, because the connector never reads from Slack. Renaming a channel is harmless: the webhook follows the channel. Archiving it, removing the app, or a Slack admin revoking the webhook all make the next **Post message** step fail. Ask clients to keep the Slack app owned by a team account rather than one person, since an app can be removed when its only collaborator leaves the Slack workspace.

## Troubleshooting

Slack answers a webhook call with a short error string, which the step log shows after the run history message.

| Run history message | Slack response | Cause and fix |
|---|---|---|
| Connection authorization failed | `invalid_token` or `no_service` | The webhook was revoked or the app was removed from the workspace. Create a new webhook and paste it into the connection under **Admin > Connections**. |
| Permission denied by Slack | `action_prohibited` | A Slack admin restricted posting in the channel. Ask the client's Slack admin. |
| Channel not found | `channel_not_found` or `channel_is_archived` | The channel was deleted or archived. Create a webhook for a live channel and edit the connection. |
| Message is empty or invalid | `no_text` or `invalid_payload` | The message resolved to empty or broke the JSON. Check the expressions in **Message**. |

If a private channel stops receiving messages after the webhook's creator leaves it, recreate the webhook as a current member of that channel.
