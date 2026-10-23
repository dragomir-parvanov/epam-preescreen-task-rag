---
id: nimbus-plan-tiers
title: Plan Tiers and Entitlements
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-09-02
owner: Product Operations
---

Every OmniCorp Nimbus workspace is on exactly one Plan Tier: Starter, Business or Enterprise. The Plan Tier decides how many people can use the workspace, how much automation it can run, which identity and integration features are switched on, how long audit logs are kept and where the workspace's data can live. This reference lists those entitlements in one place, so you can tell a client what their current tier includes and what an upgrade would change.

The values below are the entitlements Nimbus enforces in the product. If a client's contract names a different limit, the contract wins for that client, and the workspace has a custom override that support can see in the admin tools.

## Tier overview

The three Plan Tiers are aimed at different stages of a client's adoption:

- **Starter** is for a single team trying Nimbus out. It covers the core workflow builder and the most common connectors, signs users in with a Nimbus password, and keeps everything in the EU or US data region.
- **Business** is for a department running Nimbus in production. It adds single sign-on, API access and longer audit history, and raises the seat, run and connector limits.
- **Enterprise** is for organisation-wide rollouts. It adds automated user provisioning, the APAC data region, the highest API rate limit and a full year of audit history, and removes the seat, run and connector limits.

A workspace's Plan Tier is shown on the **Settings > Plan** page of the admin console, and it is returned by the entitlements endpoint described under "Checking a client's Plan Tier" below.

## Feature matrix

The matrix is the authoritative list of what each Plan Tier includes. "No" means the feature can't be switched on for that tier; it isn't hidden behind a setting.

| Entitlement | Starter | Business | Enterprise |
|---|---|---|---|
| Seats | Up to 10 | Up to 250 | Unlimited |
| Workflow runs per month | 5,000 | 100,000 | Unlimited |
| Active connectors | 5 | 50 | Unlimited |
| Single sign-on (SAML 2.0) | No | Yes | Yes |
| SCIM provisioning | No | No | Yes |
| API access | No | Yes | Yes |
| API rate limit | No API access | 600 req/min | 3,000 req/min |
| Audit-log retention | 30 days | 90 days | 365 days |
| EU and US data regions | Yes | Yes | Yes |
| APAC data region | No | No | Yes |

Single sign-on (SAML 2.0) is available on the Business and Enterprise tiers. Setting it up is described in [Configuring SSO with SAML 2.0](nimbus-sso-saml.md).

SCIM provisioning is available on the Enterprise tier only. A Business-tier workspace can't turn it on, even with single sign-on configured. The setup is described in [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md).

API access is available on the Business and Enterprise tiers. Starter workspaces can't create API keys or register webhook endpoints. Limits and webhook behaviour are covered in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).

## Data regions

A workspace stores its workflows, run history, audit logs and user data in one data region. Nimbus offers three:

| Region | Available on |
|---|---|
| EU | Starter, Business and Enterprise |
| US | Starter, Business and Enterprise |
| APAC | Enterprise only |

The region is chosen when the workspace is created, and it can't be changed afterwards. A client that needs to move region creates a new workspace in the target region and migrates its workflows into it. Plan the move with the client before the new workspace goes live, because run history and audit logs stay in the old workspace.

Because APAC is an Enterprise entitlement, a workspace in the APAC data region can't be downgraded below Enterprise. The client would first have to move to a new workspace in the EU or US region.

## Audit-log retention

The audit log records administrative and security events: sign-ins, role changes, SSO and SCIM configuration changes, API key creation and webhook endpoint changes. Admins can search it under **Settings > Audit log** and export the visible range as CSV.

Each event is kept for the retention period of the workspace's Plan Tier, counted from the day the event happened:

- Starter keeps audit-log events for 30 days.
- Business keeps them for 90 days.
- Enterprise keeps them for 365 days.

When an event passes its retention period it is permanently deleted, and there is no way to restore it. Clients with a longer compliance requirement should export the audit log on a schedule shorter than their retention period.

## Checking a client's Plan Tier

You can confirm a client's Plan Tier and its effective limits in the admin console, or ask an Admin on the client side to call the entitlements endpoint.

1. Open the client's workspace in the admin console.
2. Go to **Settings > Plan**.
3. Read the **Plan Tier** field and the limits table below it. Limits that differ from the matrix above are marked **Custom**.
4. If the client is on Business or Enterprise, an Admin can also call the entitlements endpoint with an API key, as shown below.

```http
GET /workspace/entitlements HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "plan_tier": "business",
  "seats": { "limit": 250, "used": 184 },
  "workflow_runs_per_month": { "limit": 100000, "used": 61250 },
  "features": {
    "single_sign_on": true,
    "scim_provisioning": false,
    "api_access": true
  },
  "api_rate_limit_per_minute": 600,
  "audit_log_retention_days": 90,
  "data_region": "eu"
}
```

## Changing Plan Tiers

A Plan Tier change is requested by the client's account owner and applied by OmniCorp. The workspace keeps its id, users, workflows and data region through the change.

### Upgrading

An upgrade takes effect immediately. New entitlements, such as single sign-on on Business or SCIM provisioning on Enterprise, become available as soon as the change is applied, and the new seat, run and connector limits apply straight away. Audit-log events that are still inside the old retention period are kept for the longer new period.

### Downgrading

A downgrade takes effect at the end of the current billing period. Before it does, check what the client will lose:

1. Seats, workflow runs and active connectors above the new tier's limits must be reduced first, or the downgrade is held.
2. Audit-log events older than the new tier's retention period are deleted when the downgrade takes effect.
3. A downgrade from Enterprise stops SCIM sync. Users provisioned by SCIM keep their accounts, but changes in the identity provider no longer reach Nimbus.
4. A downgrade to Starter turns off single sign-on and API access. Users sign in with a Nimbus password again, and existing API keys stop working.
