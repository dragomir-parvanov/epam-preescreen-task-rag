---
id: nimbus-tier-usage-dashboard
title: Usage Dashboard and Quota Alerts
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-03-16
owner: Product Operations
---

The usage dashboard shows how much of its Plan Tier's limits a workspace is using: workflow runs this month, seats, active connectors and secrets, each against the limit that applies. It lives under **Settings > Usage** and was introduced in release 3.5.0, together with the quota alert emails and the `GET /workspace/usage` endpoint.

It is the first place to look when a client asks why runs are being rejected, whether they can add another connector, or whether they are close to needing an upgrade. It is also the page to check before a downgrade, because usage above the new tier's limits holds the downgrade until it is reduced.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Usage dashboard (**Settings > Usage**) | Yes | Yes | Yes |
| Quota alert emails at 80% and 100% | Yes | Yes | Yes |
| `GET /workspace/usage` | No API access | Yes | Yes |

The dashboard and the alerts work the same way on every tier. The endpoint needs an API key, so it is only usable on tiers that include API access; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

## How it works

The dashboard has one meter per limited resource. Each meter shows the current figure, the tier's limit and the percentage used, and turns amber at 80% and red at 100%. Where the tier's limit is Unlimited, the meter shows the figure on its own, with no percentage and no colour change.

| Meter | What is counted | Resets |
|---|---|---|
| Workflow runs this month | Runs that started since the 1st of the month (UTC); test runs in the builder aren't counted | On the 1st of each month (UTC) |
| Seats | Active users, whatever their role; suspended users and pending invitations aren't counted | Doesn't reset |
| Active connectors | Connectors with at least one connection used by an active workflow | Doesn't reset |
| Secrets | Secrets stored in the workspace's secrets vault | Doesn't reset |

Figures are refreshed every 5 minutes, and the time of the last refresh is shown under the page title. Under the run meter, a daily bar chart shows how the month's runs were spread, and a **Top workflows** list ranks the ten workflows that started the most runs this month, which usually explains a sudden jump.

### Quota alerts

When workflow runs reach 80% of the month's quota, Nimbus emails every Admin in the workspace. A second email goes out at 100%. From then on, scheduled, event-triggered and manual runs are rejected with WF-300 until the quota resets on the 1st of the month (UTC) or the tier is upgraded. Each threshold is emailed once per month, so Admins don't get a message for every rejected run. The same 80% and 100% emails are sent for seats, active connectors and secrets when they reach those shares of their limits. Alerts can't be switched off, because they go only to Admins and only twice per resource per month.

## Turning it on

There is nothing to switch on; every workspace has the dashboard. To read it or pull the same figures into a client's own reporting:

1. Sign in to the admin console as an Admin. Builders and Viewers don't see **Settings > Usage**.
2. Go to **Settings > Usage** and read the four meters.
3. To see which workflows are driving runs, open **Top workflows** and click a workflow to go to its run history.
4. To make sure the alerts reach the right people, check the list of Admins under **Settings > Users**; alerts follow the Admin role, not the notification recipients set under **Settings > Workspace**.
5. To collect the figures automatically, call `GET /workspace/usage` with an API key.

```http
GET /workspace/usage HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "period_start": "2026-03-01T00:00:00Z",
  "period_end": "2026-04-01T00:00:00Z",
  "refreshed_at": "2026-03-16T08:25:00Z",
  "workflow_runs": { "used": 81240, "limit": 100000 },
  "seats": { "used": 196, "limit": 250 },
  "active_connectors": { "used": 31, "limit": 50 },
  "secrets": { "used": 74, "limit": 250 }
}
```

For an Unlimited resource, `limit` is `null`. The figures are the same ones the dashboard shows, with the same 5-minute refresh, so polling the endpoint more often than that returns the same values.

## Limits

The dashboard measures against these limits; seat limits are in [Seat Limits and How Seats Are Counted](nimbus-tier-seat-limits.md).

| Resource | Starter | Business | Enterprise |
|---|---|---|---|
| Workflow runs per month | 5,000 | 100,000 | Unlimited |
| Active connectors | 5 | 50 | Unlimited |
| Secrets | 25 | 250 | Unlimited |

Alert thresholds are fixed at 80% and 100%; a client can't add a 50% alert or move the thresholds. The dashboard keeps the current month only. For earlier months, use run history, or record the endpoint's figures at the end of each month. Run quotas and what happens at 100% are covered in detail in [Workflow Run Quotas](nimbus-tier-workflow-run-quotas.md).

## When the Plan Tier changes

**Upgrade.** An upgrade takes effect immediately and the meters switch to the new limits at the next refresh. Runs already used this month stay counted, but the percentage is recalculated against the new quota, so a workspace that was blocked at 100% can run again straight away. If the new figure later crosses 80% or 100% of the higher limit, the alerts are sent again.

**Downgrade.** A downgrade takes effect at the end of the current billing period. Until then the meters show the current tier's limits. Before the date, use the dashboard to compare usage with the new tier's limits: seats and active connectors above the new limits must be reduced first, or the downgrade is held. Secrets above the new limit don't hold it, but no new secret can be added afterwards; see [Secrets Vault Limits](nimbus-tier-secrets-vault.md). Monthly runs are measured against the new quota from the moment the downgrade takes effect, so a downgrade in the middle of a month can push a workspace straight to 100% if it has already used more than the new quota.
