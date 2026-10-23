---
id: nimbus-tier-active-connector-limits
title: Active Connector Limits
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-12-15
owner: Product Operations
---

The active connector limit caps how many different connectors a workspace can have in live use at once. It is the limit clients most often misread, because it counts connectors rather than connections or workflows: ten workflows writing to the same Salesforce org use one active connector, while one workflow that touches Salesforce, Slack and Jira Cloud uses three.

This guide explains the counting rule, what the console and API do when activating a workflow would go over the limit, and how a client frees up room without losing work.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Active connectors | 5 | 50 | Unlimited |
| Connections you can create | No limit | No limit | No limit |
| Workflows you can build and keep inactive | No limit | No limit | No limit |
| Activation blocked at the limit | Yes | Yes | Never |

The limit is part of the Plan Tier entitlements listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md). Contracts can carry a custom value, which shows as **Custom** next to the limit on **Settings > Plan**.

## How it works

Nimbus separates three things that clients tend to call "integrations":

- A **connector** is an integration Nimbus offers, such as Salesforce, Zendesk or the HTTP Request connector.
- A **connection** is the client's authorised account on a connector, for example the production Salesforce org connected by a Builder on the **Connections** page.
- A **workflow** uses connections in its trigger and steps.

A connector is **active** when at least one of its connections is used by at least one active workflow. Nimbus recalculates the count every time a workflow is activated, deactivated or published with different connections.

The consequences of that rule:

1. Several connections to the same connector count once. A sandbox org and a production org on the Salesforce connector make one active connector.
2. A connection that no active workflow uses doesn't count, however many runs it had in the past.
3. Inactive and draft workflows don't count. A Builder can build and test against any number of connectors; the limit applies only when the workflow is switched on.
4. A connection that shows **Needs attention** after a CONN-401 still counts while an active workflow uses it, because the workflow is still active even though its steps fail.
5. Every connector in the catalogue counts the same way, including the HTTP Request connector and the database connectors.

On workspaces with Development and Production environments, a connector is counted once whichever environment its active workflows run in. See [Development and Production Environments](nimbus-tier-environments.md).

### What happens at the limit

When activating a workflow would bring in a connector that isn't already active, and the workspace is already at its limit, Nimbus refuses the activation. The workflow stays inactive and nothing else changes. In the builder, the **Activate** toggle snaps back and shows:

> Activating "Sync closed-won deals" would use 6 active connectors. Your Starter plan allows 5. Deactivate a workflow that uses another connector, or ask your account owner about upgrading.

The API returns `409 Conflict` from `POST /workflows/{id}/activate` with the same message. Workflows that use only connectors that are already active can be activated as usual, and publishing a change to an active workflow is refused in the same way if the new version adds a connector over the limit.

## Turning it on

The limit is always enforced. When a client hits it, an Admin or Builder frees up a connector like this:

1. Go to **Settings > Plan** and read the **Active connectors** line, which shows the count in use against the limit.
2. Open **Connections** and sort by **Used by active workflows**. Each connection lists the active workflows that use it; connectors whose connections are all at zero aren't counted.
3. Pick a connector with few dependants, for example one used by a single low-value workflow, and open those workflows.
4. Deactivate each of them from the builder, or replace the step with a connector that is already active (a Slack notification can often become a Microsoft Teams one, or the reverse, if the other is already in use).
5. Activate the workflow that was refused. The count on **Settings > Plan** updates straight away.

On workspaces with API access, the same check and deactivation can be scripted. The entitlements endpoint returns the count, and deactivating a workflow is one call:

```bash
curl -s https://api.nimbus.omnicorp.example/workspace/entitlements \
  -H "Authorization: Bearer <api-key>"
# "active_connectors": { "limit": 50, "used": 50 }

curl -s -X POST https://api.nimbus.omnicorp.example/workflows/wf_8Kd2pQ/deactivate \
  -H "Authorization: Bearer <api-key>"
```

Deactivating a workflow doesn't delete its connections, its version history or its run history, so it can be switched back on later without rebuilding anything. Deleting a connection is never necessary to free a connector, and it should be avoided: credentials are encrypted and never shown again, so recreating the connection means authorising the account from scratch.

## Limits

| Plan Tier | Active connectors | Typical fit |
|---|---|---|
| Starter | 5 | One team linking a CRM, a chat tool and a couple of file or ticketing apps |
| Business | 50 | A department with workflows across sales, support, finance and HR systems |
| Enterprise | Unlimited | Organisation-wide use; the count is still shown on **Settings > Plan** |

Points that come up in client conversations:

- The limit counts connectors, so adding a second Jira Cloud site or another Box account to an already-active connector never needs a free slot.
- There is no separate limit on connections or on workflows; those are bounded only by the [monthly run quota](nimbus-tier-workflow-run-quotas.md).
- A deactivated workflow's connections stay on the **Connections** page and keep their authorisation until it expires or is revoked in the third-party app.

## When the Plan Tier changes

An upgrade takes effect immediately. The higher limit applies as soon as the change is applied, so workflows that were refused can be activated straight away.

A downgrade takes effect at the end of the current billing period, and the active connector count must already fit the new tier by then. If a Business workspace with 12 active connectors is downgrading to Starter, the client must bring the count down to 5 before the downgrade is due, or the downgrade is held until they do. Nimbus doesn't choose which workflows to switch off. Work through the steps under "Turning it on" with the client, starting with the connectors that serve the fewest workflows, and confirm the count on **Settings > Plan** a few days before the billing date.

Moving from Enterprise to Business works the same way with a limit of 50. Enterprise clients often have well over 50 connectors in use without noticing, because nothing has ever stopped them, so run the count early rather than in the last week of the billing period.
