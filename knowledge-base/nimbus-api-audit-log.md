---
id: nimbus-api-audit-log
title: Audit Log API
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-22
owner: Platform API Team
---

The audit log records who changed what in a Nimbus workspace: sign-ins, user and role changes, security settings, API keys, webhooks, workflows and connections. `GET /audit-log/events` reads it, filtered by actor, action and time range. It returns the same events an Admin searches under **Settings > Audit log**, as JSON instead of the console table or CSV export.

The endpoint is read-only; events can't be edited or deleted through the API or the console. How long events are kept depends on the workspace's Plan Tier, and events past that point simply aren't returned; the periods are listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md). Authenticate with an API key in `Authorization: Bearer <api-key>`. Every call made with that key is itself recorded, with the key as the actor.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/audit-log/events` | List audit events, newest first, with optional `actor`, `action`, `from` and `to` filters. |

There is one endpoint, and no event-by-id lookup; to fetch a known event, filter on its exact `occurred_at` and `action`. Clients who want events pushed to their own tooling as they happen, rather than polling this endpoint, can use audit-log streaming to Splunk, Datadog or an HTTPS endpoint, which is an Enterprise feature; see [Audit Log Streaming](nimbus-tier-audit-log-streaming.md). For the console search and CSV export, see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

### Action names

Actions are written `<area>.<past_tense>`. A selection of the most-asked-about ones:

| Action | Recorded when |
|---|---|
| `auth.sign_in_succeeded` | A user signs in to the console, by password or single sign-on. |
| `auth.sign_in_failed` | A sign-in attempt fails, e.g. a wrong password. |
| `user.invited` | An invitation is sent. |
| `user.role_changed` | A user's role changes; `changes.role` holds the old and new role. |
| `user.suspended`, `user.reactivated`, `user.deleted` | An account changes state. |
| `api_key.created`, `api_key.revoked` | An API key is created or revoked. |
| `webhook_endpoint.created`, `webhook_endpoint.updated` | An endpoint is registered or changed. |
| `workflow.published`, `workflow.activated`, `workflow.deleted` | A workflow is published, switched on or removed. |
| `connection.created`, `connection.deleted` | A connection is made or removed. |
| `sso.configuration_updated`, `security.two_factor_policy_updated` | Security settings change. |
| `workspace.plan_changed` | The Plan Tier changes. |

Workflow runs are not audit events; they live in run history and the [Runs API](nimbus-api-runs.md).

## Object fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Event id, prefixed `evt_`. |
| `action` | string | The action name, as above. |
| `occurred_at` | string | When it happened, ISO 8601 in UTC. |
| `actor` | object | Who did it: `type` (`user`, `api_key`, `scim` or `system`), `id`, and `display` (an email address or key name). |
| `target` | object or null | What it was done to: `type`, `id` and `display`, e.g. a user, a workflow or a key. |
| `changes` | object or null | For updates, each changed field as `{"from": ..., "to": ...}`. Secrets and credentials are never included. |
| `source` | string | Where it came from: `console`, `api`, `scim` or `sso`. |
| `reason` | string or null | For `auth.sign_in_failed`, why the sign-in failed, e.g. `invalid_password` or `invalid_second_factor`. |
| `user_agent` | string or null | The browser or HTTP client string, when there was one. |

Changes made by the platform itself, such as an endpoint switched off after failed deliveries, have an actor of type `system`. Changes pushed by an identity provider over SCIM have actor and source `scim`.

## Example request and response

Who changed roles during the first week of June:

```http
GET /audit-log/events?action=user.role_changed&from=2026-06-01T00:00:00Z&to=2026-06-08T00:00:00Z HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

```json
{
  "data": [
    {
      "id": "evt_01J0D8RZ2KXH",
      "action": "user.role_changed",
      "occurred_at": "2026-06-04T14:31:09Z",
      "actor": {"type": "user", "id": "usr_1180", "display": "m.okafor@clientco.example"},
      "target": {"type": "user", "id": "usr_2045", "display": "priya.raman@clientco.example"},
      "changes": {"role": {"from": "viewer", "to": "builder"}},
      "source": "console",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Firefox/126.0"
    },
    {
      "id": "evt_01J0B2TQ8MNA",
      "action": "user.role_changed",
      "occurred_at": "2026-06-02T08:02:47Z",
      "actor": {"type": "api_key", "id": "key_3307", "display": "HR onboarding script"},
      "target": {"type": "user", "id": "usr_2311", "display": "l.chen@clientco.example"},
      "changes": {"role": {"from": "builder", "to": "admin"}},
      "source": "api",
      "user_agent": "python-requests/2.32.3"
    }
  ],
  "next_cursor": null
}
```

## Filtering and pagination

All four filters are optional and combine with AND:

- `actor`: a `usr_` or `key_` id, or the literal `system` or `scim`.
- `action`: an exact action, a comma-separated list, or a prefix ending in `.*` such as `api_key.*`.
- `from`: inclusive lower bound on `occurred_at`.
- `to`: exclusive upper bound on `occurred_at`.

Without `from` and `to`, the list starts at the newest event and runs back as far as the workspace's retention allows. Pages hold `limit` events (default 25, maximum 100) and continue with `cursor`. A cursor pins the result set when the first page is read, so events recorded while a client is paging don't shift later pages.

For a large range, such as a quarterly access review, page week by week rather than asking for the whole quarter at once:

1. Choose the first window, for example `from=2026-04-01T00:00:00Z&to=2026-04-08T00:00:00Z`, and add `limit=100`.
2. Request it and store the events in `data`.
3. While `next_cursor` is not null, request again with the same window and `cursor=<next_cursor>`.
4. Move both bounds forward by a week and repeat until the end of the range.

Small windows keep each export resumable: if the job stops halfway, it restarts from the last finished window.

## Errors

| HTTP status | Code | Why |
|---|---|---|
| 400 | `invalid_request` | `from` or `to` isn't ISO 8601, `from` is later than `to`, or `actor` isn't a valid id. |
| 400 | `invalid_request` | A cursor was sent with filters different from the ones it was issued for. |
| 401 | `unauthorized` | The API key is missing, expired or revoked. |
| 429 | `rate_limited` | The workspace went over its API limit; see [API Rate Limits and Webhooks](nimbus-api-webhooks.md). |
| 500 | `internal_error` | A Nimbus fault; repeat the same request. |

An action name that doesn't exist is not an error; it returns an empty `data` array, so check spelling when a filter finds nothing.
