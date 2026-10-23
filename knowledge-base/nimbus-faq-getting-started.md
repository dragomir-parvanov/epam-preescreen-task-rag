---
id: nimbus-faq-getting-started
title: Getting Started FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-09-07
owner: Customer Success Enablement
---

This FAQ collects the questions new clients ask in their first weeks on OmniCorp Nimbus: who to invite and with which role, how to make the first connection, how to build and test the first workflow, and where templates help. Answers assume the client signs in to the admin console at https://app.nimbus.omnicorp.example with an Admin account.

For anything that depends on the client's Plan Tier, such as how many seats or active connectors they have, check [Plan Tiers and Entitlements](nimbus-plan-tiers.md) or the client's own Settings > Plan page rather than quoting a number from memory.

## General questions

**What does a client need in place before the first workflow can run?**

Three things: at least one user with the Builder or Admin role, a connection for every app the workflow touches, and a trigger. The person who created the workspace is its first Admin. Everything else can be added in any order, but most clients go people first, then connections, then workflows.

**Which role should each person get?**

Nimbus has three roles. Give people the lowest role that lets them do their job; an Admin can change it later from Settings > Users.

| Role | Can do | Typical holder |
|---|---|---|
| Admin | Manages users, roles, SSO, SCIM, API keys, webhooks and the Plan Tier, and everything a Builder can do | IT owner, platform lead |
| Builder | Creates, edits and runs workflows and connectors | Operations analyst, integration developer |
| Viewer | Views workflows, runs and run history; can't edit | Team lead, auditor, support agent |

Every active user takes a seat, whatever their role, so a Viewer is not free in seat terms.

**Are there ready-made workflows to start from?**

Yes. Workflow templates are available on every Plan Tier. In Workflows, click New workflow > From template, pick one (for example "Post new HubSpot contacts to Slack"), and Nimbus creates a draft copy in the workspace. The draft asks for a connection on each connector step before it can be published. A template is only a starting point: once copied, the workflow belongs to the client and doesn't change when the template does.

## Setup questions

**How do I make the first connection?**

Open Connections, click New connection and choose the connector. OAuth connectors such as HubSpot, Slack or Jira Cloud open the app's own consent screen; others ask for a token, key or username and password. Name the connection after the account it uses (for example "HubSpot – Sales EU") so Builders can tell connections apart later. Credentials are encrypted when saved and are never shown again, so keep the source of any key or token in the client's own password manager.

**What does a simple first workflow look like?**

A workflow is one trigger followed by ordered steps. A common first build posts each new CRM contact to a team channel. In the builder it reads like this, with each step's key in brackets:

```text
Trigger   HubSpot > Contact created (push event)
Step 1    Transform                         [shape_contact]
            full_name = {{trigger.body.firstname}} {{trigger.body.lastname}}
            owner     = {{default(trigger.body.owner_email, "sales-ops@client.example")}}
Step 2    Slack > Post message              [notify_channel]
            channel   = #new-leads
            text      = New lead: {{steps.shape_contact.output.full_name}} (owner {{steps.shape_contact.output.owner}})
```

Click Test run to try it with a sample payload, then Publish to create the first version, and Activate so the trigger starts firing.

### How do I invite my team?

Invitations are sent from the admin console by an Admin:

1. Go to Settings > Users and click Invite users.
2. Enter one or more email addresses, separated by commas or new lines.
3. Choose a role for the batch. If no role is chosen, the invitees get Viewer.
4. Click Send invitations. Each person receives an email with a personal link.

An invitation expires after 7 days. The invited person takes a seat only once they accept, so outstanding invitations don't use up the workspace's seats. Pending invitations are listed on the same page with a Resend and a Revoke action. If the client plans to sign in through their identity provider, set that up first with [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) so that new users never have to create a password.

## Limits and edge cases

**Do test runs count against the monthly run quota?**

No. Test runs in the builder don't count. A run counts when it starts, so a live run that fails on its first step still counts once. The client's quota and current usage are under Settings > Usage.

**How often can a scheduled workflow run?**

Schedules are cron expressions in the workspace time zone, or in an IANA time zone chosen on the trigger. The shortest interval depends on the Plan Tier: 15 minutes on Starter, 5 minutes on Business and 1 minute on Enterprise. A cron expression that fires more often than the tier allows is refused when the workflow is published.

**Can one person own the first workflows and leave later?**

Yes, but plan for it. Every workflow has an owner, a Builder or Admin. If the owner is suspended or deleted, the workflow keeps running and an Admin must transfer ownership to someone else; see [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md).

## Troubleshooting questions

**A new colleague says their invitation link doesn't work.**

The invitation has most likely expired. In Settings > Users > Pending invitations, click Resend; this issues a fresh link valid for another 7 days. If the person already accepted with a different email address, revoke the pending invitation instead.

**The first test run fails with CONN-403.**

The account behind the connection lacks permission in the third-party app for the action the step performs, for example posting to a private Slack channel the Slack app hasn't been added to. Grant the permission in the app itself, then test again; reconnecting won't help.

**The first test run fails with WF-400.**

A data-mapping expression resolved to empty where a value is required. Check that the field names in `{{trigger.body.<field>}}` match the sample payload exactly, or wrap the expression in `{{default(x, y)}}`.

**A scheduled workflow never ran.**

Check that it was activated, not only published, and that the cron expression is valid: an invalid expression is reported as WF-100 on the trigger. See [Troubleshooting Scheduled Workflows](nimbus-troubleshooting-schedules.md) for time-zone issues.

## Where to find more

- [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md) for invitations in detail.
- [Workflow Templates](nimbus-tier-workflow-templates.md) for the template catalogue.
- [Scheduling Workflows](nimbus-admin-scheduling-workflows.md) for cron syntax and time zones.
- [Workflow Builder FAQ](nimbus-faq-workflow-builder.md) and [Connectors FAQ](nimbus-faq-connectors.md) for the next round of questions.
