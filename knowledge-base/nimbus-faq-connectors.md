---
id: nimbus-faq-connectors
title: Connectors FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-29
owner: Customer Success Enablement
---

Connectors are how Nimbus talks to a client's other applications. This FAQ answers the questions CSMs get about them most often: what a connector is compared with a connection, what counts towards the active connector limit, how push and polling triggers differ, how to reconnect a broken connection, what to do for an app Nimbus has no connector for, and when the private connector agent is needed.

Each connector also has its own Article with its authentication steps and actions; those are linked at the end.

## General questions

**What is the difference between a connector and a connection?**

A connector is an integration Nimbus offers, such as Salesforce or SFTP. A connection is one client's authorised account on that connector, for example "Salesforce – Production" signed in as an integration user. A workspace can hold several connections on the same connector, such as a production and a sandbox org. Connections are listed under Connections in the console.

**What counts as an active connector?**

A connector counts as active when at least one of its connections is used by an active workflow. Connections that exist but sit unused, or are used only by deactivated workflows, don't count. Two Salesforce connections used by active workflows count as one active connector, because the limit is per connector. The workspace's current count is on Settings > Usage, and the limit per Plan Tier is in [Active Connector Limits](nimbus-tier-active-connector-limits.md).

**How do push and polling triggers differ?**

With push triggers the app sends events to Nimbus, which starts the run within seconds. Connectors whose apps can't push are polled every 5 minutes, so a new record can take up to that long to start a run. Some examples:

| Connector | Trigger type | Authentication |
|---|---|---|
| HubSpot | Push | OAuth 2.0 |
| Jira Cloud | Push | OAuth 2.0 |
| GitHub | Push | GitHub App installation |
| Salesforce | Polling | OAuth 2.0, production or sandbox org |
| ServiceNow | Polling | OAuth 2.0 or basic auth with an integration user |
| Amazon S3 | Polling, on new objects | Access key or IAM role |
| PostgreSQL | Polling, on a query | Username and password over TLS |
| Snowflake | None (actions only) | Key-pair authentication |

## Setup questions

**What if the client's app has no Nimbus connector?**

Use the HTTP Request connector. It calls any HTTPS API and supports no authentication, an API key header, basic auth, or OAuth 2.0 client credentials. Keep the key in the secrets vault and reference it in the step rather than pasting it in:

```yaml
step: HTTP Request > Send request
key: create_ticket
method: POST
url: https://helpdesk.client.example/api/tickets
headers:
  X-Api-Key: "{{secrets.HELPDESK_API_KEY}}"
  Content-Type: application/json
body: |
  {"subject": "{{trigger.body.subject}}", "requester": "{{lower(trigger.body.email)}}"}
```

HTTP Request has no triggers. To start a workflow from such an app, have it call an inbound webhook trigger instead.

**How is the private connector agent installed?**

The agent is a small service the client runs inside their own network so Nimbus can reach databases and SFTP servers that aren't reachable from the internet. It opens an outbound TLS connection to Nimbus, so no inbound firewall rule is needed. An Admin clicks Register agent under Settings > Agents, copies the one-time registration token, and the client starts the Docker image on a host that can reach the target systems:

```bash
docker run -d --name nimbus-agent --restart unless-stopped \
  -e NIMBUS_AGENT_REGISTRATION_TOKEN=<one-time-token> \
  omnicorp/nimbus-agent:latest
```

When creating a PostgreSQL, MySQL, SQL Server or SFTP connection, the client then picks the agent under Connect through.

### How do I reconnect a connection that needs attention?

When a connection's authorisation expires or is revoked, for example because the user who authorised it changed their password or left, its steps fail with CONN-401 and the connection shows "Needs attention". A Builder or Admin fixes it:

1. Open Connections and filter by Status: Needs attention.
2. Open the connection and click Reconnect.
3. Complete the app's sign-in or consent screen, or enter the new token or key.
4. Click Test connection and wait for the green Connected badge.
5. In Runs, filter by status failed and review the runs that failed while the connection was down; they aren't repeated automatically.

Reconnecting keeps the connection's id, so every workflow that uses it carries on without being edited.

## Limits and edge cases

**Who can use the private connector agent?**

Enterprise workspaces only. Business and Starter clients with an internal database need it exposed over TLS to the internet, or an upgrade.

**Can a saved password or token be viewed later?**

No. Connection credentials are encrypted and never shown again after saving. To change one, open the connection and enter the new value.

**What happens to a polling trigger when a connection is reconnected?**

Polling resumes from where it stopped, so records created while the connection was broken are picked up on the next poll rather than lost.

## Troubleshooting questions

**Steps fail with CONN-403 but the connection tests fine.**

The connection is valid, but the connected account lacks permission in the third-party app for that particular action, for example a Salesforce user without edit access to the Opportunity object. Grant the permission in the app; reconnecting won't change anything.

**Steps fail with CONN-404.**

The record, file or object the step refers to doesn't exist in the app, often because an id from an earlier step was empty or the record was deleted in between.

**Run history shows CONN-429.**

The third-party app throttled the connector. Nimbus backs off and retries the step on its own; if it keeps happening, spread the workflow's schedule or reduce the batch size per run.

**Steps fail with CONN-503 on a database connection.**

The app, or the private connector agent in front of it, is unavailable. Check Settings > Agents: an agent is shown "Offline" after 2 minutes without a heartbeat, usually because its host was restarted or lost its outbound connection.

## Where to find more

- [Troubleshooting Connector Authorization Errors](nimbus-troubleshooting-connection-errors.md) for CONN-401 and CONN-403.
- [Private Connector Agent](nimbus-tier-private-connector-agent.md) and [Troubleshooting the Private Connector Agent](nimbus-troubleshooting-private-agent.md).
- [HTTP Request Connector](nimbus-connector-http-request.md) for every authentication option.
- [How Connection Credentials and Secrets Are Stored](nimbus-security-credential-storage.md).
