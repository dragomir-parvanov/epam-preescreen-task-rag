---
id: nimbus-tier-environments
title: Development and Production Environments
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-01-26
owner: Product Operations
---

Environments let a client build and test changes to a workflow in **Development** while the version that handles real data keeps running untouched in **Production**. Each environment has its own connections and its own variables, so the same workflow can write to a Salesforce sandbox org in Development and to the production org in Production without anyone editing the steps.

Environments arrived in release 3.2.0 (2025-08-04), together with the promote endpoint. This guide covers which tiers have them, how the two environments relate, how an Admin switches them on, and what a downgrade does to the Development side.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Development and Production environments | No | Yes | Yes |
| Per-environment connections | No | Yes | Yes |
| Per-environment variables (`{{env.<NAME>}}`) | No | Yes | Yes |
| Promotion in the console and `POST /workflows/{id}/promote` | No | Yes | Yes |

A Starter workspace has a single set of workflows that behaves like Production. `{{env.<NAME>}}` expressions can't be saved on Starter, because there are no variables to resolve them against.

## How it works

A workspace with environments switched on has exactly two: Development and Production. They share the workspace's users, roles, folders, Plan Tier limits and run quota, and they differ in three things:

| | Development | Production |
|---|---|---|
| Workflow definitions | Edited here by Builders and Admins | Read-only; changed only by promotion |
| Connections | Bound per environment | Bound per environment |
| Variables | Development values | Production values |

The builder shows an environment switcher at the top of **Workflows**. Builders edit and publish in Development. When a version is ready, a Builder or Admin promotes it, which copies the workflow definition to Production as a new Production version. Promotion copies steps, the trigger, expressions and the schedule; it never copies connections or variable values, because those belong to the environment.

### Connections and variables

Every connector step in a workflow points at a connection slot, not at a fixed connection. Each slot is bound to one connection per environment under **Workflows > Environments > Connection bindings**. A Salesforce slot, for example, can be bound to the sandbox org in Development and the production org in Production. A workflow can't be promoted while any of its slots has no Production binding.

Variables hold non-secret values that differ by environment, such as a Slack channel name, a SharePoint site path or a feature flag. They are referenced as `{{env.<NAME>}}` and defined under **Workflows > Environments > Variables**. Credentials and tokens belong in the secrets vault instead, referenced as `{{secrets.<NAME>}}`; see [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md).

Runs in both environments are real runs: they count against the monthly run quota and appear in run history with an **Environment** column. Only **Test run** in the builder is free.

## Turning it on

An Admin switches environments on once per workspace. The change can't be reversed from the console while the workspace stays on Business or Enterprise.

1. Go to **Workflows**, open the **Environments** menu and select **Enable environments**.
2. Read the summary. Every existing workflow becomes a Production workflow with its current connections bound to Production, and a Development copy is created with the same bindings.
3. Confirm with **Enable**. Active workflows keep running in Production without a pause.
4. Under **Workflows > Environments > Connection bindings**, rebind the Development side of each slot to test accounts, so Development runs stop touching production systems.
5. Under **Workflows > Environments > Variables**, add the variables your workflows need and give each a value for both environments.
6. Edit a workflow in Development, publish it, run it and check its run history.
7. Promote it from the builder with **Promote to Production**, or through the API.

A variable set, as entered on the Variables page, looks like this:

```yaml
variables:
  ALERT_CHANNEL:
    development: "#nimbus-alerts-test"
    production: "#ops-alerts"
  SHAREPOINT_SITE:
    development: "sites/Finance-UAT"
    production: "sites/Finance"
```

Promotion from the API, for clients with API access who promote from a release pipeline:

```http
POST /workflows/wf_3Hq7Lm/promote HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: release-2026-01-26-invoice-sync

{ "version": 18, "note": "Map PO number to the invoice reference field" }
```

The step-by-step console flow, including how to review differences before promoting, is in [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).

## Limits

| Item | Limit |
|---|---|
| Environments per workspace | 2 (Development and Production); no custom environments |
| Variables per environment | 200 |
| Variable name | Upper-case letters, digits and underscores, up to 64 characters |
| Variable value | Plain text, up to 4 KB; not encrypted, shown to every Builder and Admin |
| Versions kept per workflow | The last 50, counted separately in each environment |

Both environments share the workspace's limits. A connector that is active in either environment counts once towards the active connector limit, and runs in either environment use the same monthly quota.

## When the Plan Tier changes

Upgrading from Starter makes environments available immediately, but nothing changes until an Admin enables them as described above.

A downgrade to Starter takes effect at the end of the current billing period. At that point:

1. Production becomes the workspace's only set of workflows. Active Production workflows keep running unchanged.
2. The Development environment is switched off. Development versions that were never promoted are kept read-only under **Workflows > Archived (Development)** and can't be run or edited.
3. Connections bound only to Development stay on the **Connections** page but are no longer used by any workflow.
4. `{{env.<NAME>}}` expressions in Production workflows keep resolving to their Production values, frozen at the moment of the downgrade, and the Variables page is hidden.

Promote any Development work the client wants to keep before the downgrade date. If the workspace later upgrades again, an Admin can re-enable environments and restore archived Development versions from the same page. A move between Business and Enterprise doesn't affect environments.
