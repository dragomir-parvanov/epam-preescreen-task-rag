---
id: nimbus-troubleshooting-notifications
title: Troubleshooting Missing Notifications
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2025-10-13
owner: Support Engineering
---

Nimbus sends two kinds of operational notification. Failure alerts tell people that a workflow run failed or timed out, by email and optionally as a post in a Slack or Microsoft Teams channel; they are configured under **Settings > Notifications**. Quota emails warn Admins when the workspace has used 80% and 100% of its monthly workflow runs. When a client says "we never heard about it", the cause is nearly always one of the recipient settings, the client's mail filtering, or a broken channel connection.

How to set alerts up in the first place is in [Configuring Failure Notifications](nimbus-admin-failure-notifications.md).

## Symptoms

- A workflow failed overnight and nobody received the failure alert.
- A Builder expected the 80% quota warning but only Admins got it.
- Alerts reach some recipients but not others in the same company.
- Alerts used to appear in a Slack or Microsoft Teams channel and stopped, with no change on the Nimbus side that anyone remembers.
- Emails arrive, but in a junk or quarantine folder, or hours late.

## Common causes

| Cause | Typical clue |
|---|---|
| The person isn't a recipient | They aren't in the workflow's recipients or in the default notification recipients under **Settings > Workspace**. |
| The event doesn't trigger an alert | The run was cancelled, ran as a builder test, or only waited in `queued`. |
| The quota email is Admin-only | The person asking is a Builder or Viewer. |
| The recipient's account isn't active | The user is suspended, deleted or hasn't accepted their invitation. |
| Mail filtering | The **Delivery log** shows **Sent**, but the person can't find the message. |
| Channel connection broken | The **Delivery log** shows **Failed** for channel posts, with a CONN- code. |

Some of these need a word of explanation. Failure alerts are sent for runs that end as `failed` or `timed_out`. Cancelled runs, test runs in the builder and runs that wait as `queued` under the concurrent-run limit don't produce one. Rejections at 100% of the run quota produce the quota email to Admins, not a failure alert per rejected run.

Recipients are resolved when the alert is sent, from the workflow's own recipient list if it has one, otherwise from the workspace default. Only active users and plain email addresses on the list receive anything.

All notification emails come from `notifications@nimbus.omnicorp.example`. Filters that quarantine automated mail, or that distrust messages sent on behalf of a third-party domain, catch them regularly, especially after a client changes mail security vendor.

Channel posts go through an ordinary Slack or Microsoft Teams connection, so they break for the same reasons any connector step breaks: the Slack app was removed from the workspace, the Teams admin consent was withdrawn, or the channel was archived, deleted or made private.

## Diagnosing the problem

1. Confirm there was something to alert on. List the workflow's runs in the period, and check that at least one ended as `failed` or `timed_out`:

```http
GET /runs?workflow_id=wf_7Bq4Hs9P&status=failed&from=2025-10-06T00:00:00Z
Authorization: Bearer <api-key>
```

2. Open **Settings > Notifications > Delivery log** and find the run. Each email and channel post has a status: **Sent**, **Bounced** or **Failed**, with the recipient and time.
3. If the status is **Sent**, ask the recipient to search all folders, including quarantine, for the sender address. The message header identifies it:

```text
From: OmniCorp Nimbus <notifications@nimbus.omnicorp.example>
Subject: [Nimbus] Run failed: Sync invoices to NetSuite (run_8Jd3Wq6T)
```

4. If the status is **Bounced**, read the bounce reason in the log; a mistyped address or a full mailbox shows here.
5. If a channel post shows **Failed**, note the CONN- code and open the Slack or Teams connection under **Connections**.
6. For a missing quota email, check the person's role under **Settings > Users**.

## Error reference

These codes appear in the **Delivery log** for channel posts, and in run history where relevant.

| Code | Meaning for notifications |
|---|---|
| CONN-401 | The Slack app was uninstalled or the Microsoft Teams admin consent was revoked; the connection shows **Needs attention**. |
| CONN-403 | The Nimbus Slack app isn't a member of the channel (usually a private channel it was never invited to), or the Teams connection lacks permission to post there. |
| CONN-404 | The channel or team no longer exists, or the channel was archived. |
| CONN-503 | Slack or Microsoft Teams was unavailable; the post is retried. |
| WF-310 | A run waited as `queued` under the concurrent-run limit. This is a notice, not a failure, so no alert is sent. |
| WF-300 | Runs were rejected because the monthly quota was used. Admins get the 100% quota email rather than per-run alerts. |

## Fixes

- **Missing recipients:** add the person to the workflow's recipients in the builder (**Settings** tab, **Failure alerts**), or to the default recipients under **Settings > Workspace**. Distribution lists are a good choice, as they survive staff changes.
- **Quota emails for non-Admins:** quota emails go to Admins only. Builders who need the warning can watch **Settings > Usage**, or a recipient can set up a mail rule that forwards the Admin's message.
- **Spam filtering:** ask the client's mail administrator to trust `notifications@nimbus.omnicorp.example` and release any quarantined messages. A rule keyed on the sender address alone is enough.
- **Slack:** for CONN-403, invite the app to the channel by typing `/invite @Nimbus` in it. For CONN-401, reinstall the app and click **Reconnect** on the Slack connection; see [Slack Connector](nimbus-connector-slack.md).
- **Microsoft Teams:** for CONN-401, a Microsoft Entra ID administrator grants admin consent again, then a Builder reconnects; see [Microsoft Teams Connector](nimbus-connector-microsoft-teams.md).
- **Deleted or archived channel:** choose a new channel under **Settings > Notifications > Channels** and send a test with **Send test alert**.

## Escalating to support

If the **Delivery log** shows **Sent** and the client's mail administrator confirms the message never reached their gateway, escalate with:

- workspace id and the run id the alert was for;
- the recipient address and the **Delivery log** entry (status and time in UTC);
- the client's mail gateway trace for that time, if they can provide one;
- for channel posts, the connection id and the CONN- code shown.
