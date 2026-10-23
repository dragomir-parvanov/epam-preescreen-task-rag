---
id: nimbus-api-environments
title: Environments and Promotion API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-03-09
owner: Platform API Team
---

Workspaces with environments keep two copies of each workflow: a Development workflow that Builders edit and test, and a Production workflow that runs against live systems. Connections belong to one environment as well, so a Development workflow writes to a Salesforce sandbox org while its Production counterpart writes to the production org. The Environments and Promotion API moves a published Development version into Production and exposes the `environment` field that tells the two sides apart.

Environments arrived in release 3.2.0 and are available on the Business and Enterprise tiers; see [Development and Production Environments](nimbus-tier-environments.md). For the console steps, see [Promoting Workflows from Development to Production](nimbus-admin-promoting-workflows.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/workflows/{id}/promote` | Promote a Development workflow's published version to Production. |
| `GET` | `/workflows?environment=...` | List the workflows of one environment (Workflows API, filtered). |
| `GET` | `/connections?environment=...` | List the connections of one environment (Connections API, filtered). |

Only the first endpoint is specific to environments. The other two are the ordinary list endpoints of the [Workflows API](nimbus-api-workflows.md) and the [Connections API](nimbus-api-connections.md), which both accept the `environment` filter.

### Promoting a workflow

Call `POST /workflows/{id}/promote` with the id of the **Development** workflow. By default Nimbus promotes its latest published version; send `version` to promote an older one. Promotion runs these checks before it changes anything:

1. Every connector used by the version must have a Production connection. If the connector has exactly one Production connection, Nimbus uses it. If it has several, the request must name one in `connection_map`, which maps each Development connection id to a Production connection id.
2. Every `{{env.NAME}}` variable the version references must have a Production value, set under **Workflows > Environments > Variables**.
3. The version must have passed validation when it was published, so its trigger and expressions are known to parse.

If any check fails, nothing is promoted. On success the steps, trigger and mappings are copied into the Production workflow as a new version of it, with Development connections swapped for their Production matches. The first promotion of a workflow creates the Production workflow in the deactivated state; activate it once with `POST /workflows/{id}/activate`. Later promotions go live as soon as they complete, and runs already in progress finish on the version they started with.

Promotion is a `POST`, so send an `Idempotency-Key` header. A client that retries after a timeout then gets the original result instead of a second Production version.

## Object fields

Environments add these fields to existing objects. They are read-only through the API.

| Object | Field | Type | Description |
|---|---|---|---|
| Workflow | `environment` | string | `development` or `production`. |
| Workflow | `counterpart_id` | string or null | The `wf_` id of the paired workflow in the other environment; `null` until the first promotion. |
| Workflow | `promoted_version` | integer or null | Production only: the Development version number currently live. |
| Workflow | `promoted_at` | string or null | Production only: when the last promotion completed (ISO 8601, UTC). |
| Connection | `environment` | string | `development` or `production`. A connection is never shared between environments. |

The promote request body takes `version` (integer, optional) and `connection_map` (object, optional). Variables resolve per run: the same `{{env.ERP_BASE_URL}}` expression returns the Development value in a Development run and the Production value in a Production run. Secrets in `{{secrets.NAME}}` are workspace-wide and are the same in both environments.

## Example request and response

Promote version 22 of an invoice-sync workflow, choosing between the two Production NetSuite connections:

```http
POST /workflows/wf_2nH7cL0p/promote HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json
Idempotency-Key: 6f1c2e0a-promote-invoice-sync-22

{
  "version": 22,
  "connection_map": {
    "con_dev4Ns8": "con_prd9Kw1"
  }
}
```

```json
{
  "workflow_id": "wf_2nH7cL0p",
  "environment": "development",
  "counterpart_id": "wf_9qT4vB6e",
  "promoted_version": 22,
  "production_version": 9,
  "promoted_at": "2026-03-05T14:12:31Z",
  "connections": [
    {"development": "con_dev4Ns8", "production": "con_prd9Kw1", "connector": "netsuite"},
    {"development": "con_devS1a3", "production": "con_prdS7m2", "connector": "slack"}
  ]
}
```

`production_version` is the new version number on the Production workflow, which has its own version history. The `connections` array shows every swap, including the Slack one Nimbus resolved without a mapping.

## Filtering and pagination

`POST /workflows/{id}/promote` returns one object and takes no query parameters. Listing by environment uses the cursor-paginated list endpoints with `environment=development` or `environment=production`, plus the usual `limit` (default 25, maximum 100) and `cursor`. To find Production workflows that are behind Development:

1. Call `GET /workflows?environment=production&limit=100`.
2. For each workflow, read `promoted_version` and fetch its counterpart with `GET /workflows/{counterpart_id}`.
3. Compare the counterpart's latest published version with `promoted_version`; a higher number means unpromoted changes.
4. If `next_cursor` is not `null`, repeat from step 1 with `cursor=<next_cursor>`; stop when it is `null`.

Before a large promotion, `GET /connections?environment=production` shows which connectors already have a Production connection, so missing ones can be created first.

## Errors

Errors use the common envelope; see [API Error Format and Idempotency](nimbus-api-error-format.md). Promotion failures name the step key and connector in the `message`.

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `version` doesn't exist, or `connection_map` names a connection of the wrong connector or environment. |
| 401 | `unauthorized` | Missing, expired or revoked API key. |
| 403 | `forbidden` | The workspace's Plan Tier doesn't include environments. |
| 404 | `not_found` | No workflow with that id. |
| 409 | `conflict` | A connector used by the version has no Production connection, e.g. "No Production connection for connector salesforce (step update_account)". |
| 409 | `conflict` | A connector has several Production connections and `connection_map` doesn't pick one. |
| 409 | `conflict` | An `{{env.NAME}}` variable has no Production value, or the id given is a Production workflow. |
| 500 | `internal_error` | An internal Nimbus error. Retry with the same `Idempotency-Key`. |

Production workflows can't be edited directly: `PATCH /workflows/{id}` on one answers `409 conflict`, because changes reach Production only by promotion.
