---
id: nimbus-security-audit-events
title: Audit Log Event Catalogue
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-06
owner: Security & Compliance
---

The Nimbus audit log records security-relevant changes in a workspace: who signed in, who changed a user or a role, who touched SSO, SCIM, API keys, webhook endpoints, published workflows or secrets. This catalogue lists the event types by area, shows the shape of an event, and explains how a client's Admin and auditors use them. For how long events are kept on each Plan Tier, see [Plan Tiers and Entitlements](nimbus-plan-tiers.md); this note deliberately doesn't repeat it.

## Scope

The catalogue covers the `action` values a client sees in Settings > Audit log, in a CSV export, in `GET /audit-log/events` and in the Enterprise audit-log stream. All four carry the same events with the same names.

Workflow runs are not audit events. What a run did, step by step, lives in run history and is described in [Searching and Exporting Run History](nimbus-admin-run-history.md). Changes made by OmniCorp staff to OmniCorp's own infrastructure are covered by OmniCorp's SOC 2 controls, not by the workspace audit log.

## Controls in place

Every event is written when the change is committed, whether it came from the console, the API or a SCIM request, and events can't be edited or deleted by anyone in the workspace, Admins included. Values of secrets, passwords, API keys, SCIM tokens and webhook signing secrets are never recorded; an event names the object, not its contents.

### Event types by area

| Area | `action` values | Recorded when |
|---|---|---|
| Sign-in | `auth.sign_in_succeeded`, `auth.sign_in_failed`, `auth.account_locked`, `auth.two_factor_enrolled` | A user signs in with a password or SSO, fails to, is locked after repeated failures, or enrols an authenticator app |
| User | `user.invited`, `user.invitation_revoked`, `user.joined`, `user.imported`, `user.suspended`, `user.reactivated`, `user.deleted` | A user's account is created, changed in state or removed, including by CSV import |
| User access | `user.sessions_revoked`, `user.two_factor_reset` | An Admin signs a user out of all sessions or resets their second factor |
| Role | `user.role_changed` | A user's role changes between Admin, Builder and Viewer, by hand or from an IdP group |
| SSO | `sso.configuration_updated`, `sso.certificate_updated`, `sso.enforced`, `sso.enforcement_disabled` | The SAML settings, the IdP signing certificate or SSO enforcement change |
| Security settings | `security.session_timeout_updated`, `security.two_factor_policy_updated` | An Admin changes the console idle timeout or the two-factor requirement |
| Encryption key | `encryption_key.added`, `encryption_key.validated`, `encryption_key.activated` | A customer-managed key is added, passes validation or becomes active (Enterprise) |
| SCIM configuration | `scim.enabled`, `scim.disabled`, `scim.token_created`, `scim.token_revoked`, `scim.group_mapping_updated` | SCIM provisioning is turned on or off, its token is created or revoked, or the group-to-role mapping changes |
| API key | `api_key.created`, `api_key.revoked` | An Admin creates or revokes an API key |
| Webhook endpoint | `webhook_endpoint.created`, `webhook_endpoint.updated`, `webhook_endpoint.secret_rolled`, `webhook_endpoint.deleted` | An endpoint is registered, edited, has its signing secret rolled, or is removed |
| Workflow publish | `workflow.published`, `workflow.version_restored`, `workflow.promoted`, `workflow.ownership_transferred` | A new workflow version is published, an older one restored, a workflow promoted to Production, or its owner changed |
| Workflow | `workflow.activated`, `workflow.deleted`, `workflow.moved` | A workflow is switched on, removed or moved to another folder |
| Connection | `connection.created`, `connection.reconnected`, `connection.deleted` | A connection is made, reconnected or removed |
| Secret | `secret.created`, `secret.updated`, `secret.deleted` | A secret in the secrets vault is added, given a new value or removed |
| Workspace | `workspace.updated`, `workspace.plan_changed`, `workspace.deleted` | Workspace settings or the Plan Tier change, or the workspace is deleted |
| Audit-log streaming | `audit_stream.updated`, `audit_stream.tested` | The stream configuration changes or a test event is sent |

Users created or suspended by SCIM produce the same `user.*` events, with an actor of type `scim`, so an auditor sees leavers handled by the IdP alongside those handled by hand.

### Event shape

Each event has an `evt_` id, a UTC timestamp, the action, the actor, the target and, for changes, the before and after values of the fields that changed:

```json
{
  "id": "evt_01JZ7Q4M2KX8",
  "occurred_at": "2026-06-30T14:02:51Z",
  "action": "user.role_changed",
  "actor": {"type": "user", "id": "usr_5TzW91kD", "display": "anna.berg@examplelogistics.example"},
  "target": {"type": "user", "id": "usr_9PcL22xA", "display": "tom.reyes@examplelogistics.example"},
  "changes": {"role": {"from": "viewer", "to": "builder"}},
  "source": "console",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
```

`actor.type` is `user`, `api_key` (with the `key_` id), `scim` or `system`. `source` is `console`, `api`, `scim` or `sso`. A `secret.updated` event carries the secret's name in `target` and has no `changes` block, because the value is never logged.

## Admin settings

An Admin works with the catalogue in three places:

1. **Search.** Settings > Audit log filters by actor, action and date range. Typing `api_key.` in the action filter shows every key event.
2. **Export.** Export CSV on the same page downloads the filtered result, one row per event with the JSON `changes` column intact; see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).
3. **Stream.** On Enterprise workspaces, Settings > Audit log > Streaming sends every event to Splunk, Datadog or an HTTPS endpoint as it is written; see [Audit Log Streaming](nimbus-tier-audit-log-streaming.md).

The same filters work on the API. This call lists every SSO change in the second quarter:

```http
GET /audit-log/events?action=sso.configuration_updated&from=2026-04-01T00:00:00Z&to=2026-06-30T23:59:59Z&limit=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

The response is a normal list, `{"data": [...], "next_cursor": "..."}`, paged with `cursor` as described in [Audit Log API](nimbus-api-audit-log.md).

## Shared responsibilities

| Responsibility | OmniCorp | Client |
|---|---|---|
| Recording events | Writes every event in the catalogue, tamper-proof | Nothing |
| Keeping events longer than the tier allows | Nothing | Exports or streams them to their own storage |
| Alerting on risky events | Delivers the stream to the client's SIEM | Writes alerts, for example on `sso.enforcement_disabled` or `api_key.created` |
| Reviewing activity | Nothing | Reviews Admin, role and key events regularly |

## Evidence for auditors

The audit log is the client's own evidence that their access controls work. Common requests and the events that answer them:

- "Show that leavers lose access": `user.suspended` or `user.deleted` events matched against the HR leaver list.
- "Show who can change production workflows": `workflow.published` and `workflow.promoted` events with their actors.
- "Show that privileged changes are tracked": `user.role_changed`, `sso.*`, `scim.*` and `api_key.*` events from an export.

For OmniCorp's side of the controls, point the auditor to [Compliance Reports and Certifications](nimbus-security-compliance-reports.md).
