---
id: nimbus-release-3-7
title: Nimbus 3.7 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2026-06-01
owner: Release Management
---

Nimbus 3.7.0 was released on 2026-06-01 for every v3 workspace. It introduces the private connector agent for Enterprise workspaces, which lets workflows reach databases and SFTP servers inside a client's own network, and adds the ServiceNow connector for all tiers.

The agent is the answer to a question CSMs hear often from Enterprise clients: how to connect Nimbus to a system that is deliberately not exposed to the internet, without opening an inbound port in the firewall.

## Highlights

Enterprise clients can now run a small Nimbus agent as a Docker container next to their private systems. The agent connects out to Nimbus over TLS and carries connector traffic for the PostgreSQL, MySQL, Microsoft SQL Server and SFTP connectors, so those systems never need to accept connections from outside. ServiceNow joins the catalogue with polling triggers on table records and actions for creating, updating and querying records, authenticated with OAuth 2.0 or an integration user.

## New features

### Private connector agent

The agent is the Docker image `omnicorp/nimbus-agent`. Once started with a registration token, it opens an outbound TLS connection to Nimbus and keeps it open; Nimbus sends connector requests down that connection, and the agent performs them against the private system and returns the results. No inbound firewall rule is needed, and the agent can use an outbound proxy set with `HTTPS_PROXY`.

| Item | Detail |
|---|---|
| Tier | Enterprise only |
| Image | `omnicorp/nimbus-agent`, tagged with the release, e.g. `3.7.0` |
| Network | Outbound TLS on port 443 to Nimbus; no inbound ports |
| Supported connectors | PostgreSQL, MySQL, Microsoft SQL Server, SFTP |
| Registration | One-time registration token from **Settings > Agents** |
| Health | Shown as **Offline** after 2 minutes without a heartbeat |
| Suggested host | 2 vCPU and 2 GB of memory per agent |

An Admin creates the agent record under **Settings > Agents > Register agent**, which shows the registration token once. The token is used on the agent's first start and can't be reused; the agent then holds its own credential in its data volume. When a Builder creates or edits a connection for one of the supported connectors, a new **Connect through** field lets them pick **Direct** or a registered agent.

If an agent stops sending heartbeats, it is shown as **Offline** after 2 minutes, and steps that use a connection through it fail with CONN-503, which is retried like other failed connector steps. Registering a second agent and moving connections to it is the quickest recovery when a host must be replaced. Setup and sizing are in [Private Connector Agent](nimbus-tier-private-connector-agent.md), and common faults in [Troubleshooting the Private Connector Agent](nimbus-troubleshooting-private-agent.md).

### ServiceNow connector

The ServiceNow connector supports two authentication methods:

- **OAuth 2.0.** A ServiceNow administrator creates an endpoint for external clients under **System OAuth > Application Registry** and gives the client ID and client secret to the Nimbus Builder, who then signs in as the integration user.
- **Basic auth with an integration user.** A dedicated ServiceNow user with **Web service access only** ticked, whose password is entered in the connection.

Either way, the integration user needs read and write access to the tables the workflow uses, typically through the `itil` role for incidents and change requests. Polling triggers check every 5 minutes for new or updated records in a chosen table, such as `incident`, `change_request` or `sc_req_item`, optionally narrowed with an encoded query. Actions create, update, get and query records through the ServiceNow Table API (`/api/now/table/{table}`). See [ServiceNow Connector](nimbus-connector-servicenow.md).

## Improvements

- The **Connections** page shows which connections go through an agent, and each agent's page lists its connections.
- `GET /connections/{id}` returns an `agent_id` field for connections that use an agent.
- `POST /connections/{id}/test` reports whether a failure happened at the agent or at the target system.
- The PostgreSQL, MySQL and Microsoft SQL Server connection forms accept a custom CA certificate for servers with an internal certificate authority.
- Run detail pages show the agent that handled each step.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-5204 | Audit-log streaming to Datadog dropped events whose `actor` field contained non-ASCII characters. |
| NIM-5209 | **Verify access** for an Azure Key Vault key succeeded even when the Unwrap Key permission was missing. |
| NIM-5211 | The SFTP polling trigger re-processed files whose modification time changed without a content change. |
| NIM-5216 | The HTTP Request connector ignored a `Content-Type` set in a custom header for `PATCH` requests. |
| NIM-5220 | Invitations resent from **Settings > Users** kept the original expiry instead of a fresh one. |
| NIM-5225 | The Microsoft SQL Server trigger failed on queries that returned a `datetimeoffset` column. |

## Deprecations and breaking changes

Nothing breaks in 3.7. Existing connections stay **Direct** until a Builder changes them. Connections that go through an agent count towards active connectors in the same way as direct connections, and step timeouts are unchanged: a step that takes longer than 10 minutes through an agent still fails with WF-200.

## Upgrade notes

To run a first agent:

1. Under **Settings > Agents**, select **Register agent**, name it after its host or site, and copy the registration token.
2. On a host that can reach the private database or SFTP server, start the container:

```bash
docker run -d --name nimbus-agent --restart unless-stopped \
  -e NIMBUS_AGENT_REGISTRATION_TOKEN=<registration-token> \
  -v nimbus-agent-data:/var/lib/nimbus-agent \
  omnicorp/nimbus-agent:3.7.0
```

3. Wait for the agent to show **Online** under **Settings > Agents**, with its version and last heartbeat.
4. Edit the connection, set **Connect through** to the new agent, enter the private host name, and select **Test**.
5. Run the workflow once with **Run now** before relying on its schedule.

Keep the `nimbus-agent-data` volume when upgrading the image to a later tag; without it, the agent has to be registered again with a new token.
