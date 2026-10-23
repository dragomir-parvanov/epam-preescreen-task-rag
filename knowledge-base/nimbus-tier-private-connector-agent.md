---
id: nimbus-tier-private-connector-agent
title: Private Connector Agent
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-07-20
owner: Product Operations
---

The private connector agent lets Nimbus workflows reach systems that sit inside a client's own network and aren't reachable from the internet, such as an on-premises PostgreSQL database, a SQL Server behind the corporate firewall or an internal SFTP server. The client runs the agent, a small service shipped as the Docker image `omnicorp/nimbus-agent`, on a host inside that network. The agent opens an outbound TLS connection to Nimbus, and Nimbus sends connector work down that connection, so no inbound port has to be opened.

The agent was introduced in release 3.7.0 and is managed under **Settings > Agents**. This Article covers who can use it, how it behaves and the numbers a client's infrastructure team will ask about.

## Availability by Plan Tier

| | Starter | Business | Enterprise |
|---|---|---|---|
| Private connector agent | No | No | Yes |
| **Settings > Agents** page | Hidden | Hidden | Visible to Admins |
| "Connect through" option on a connection | – | – | Yes |

Starter and Business workspaces can only connect to systems that are reachable over the internet. A client on those tiers who needs an on-premises database usually has two choices: upgrade to Enterprise, or expose the system through their own secured gateway and use the standard connector.

## How it works

An agent belongs to an **agent group**. A connection is pointed at a group rather than at a single agent, and Nimbus hands each piece of work to any agent in the group that is online. This is how a client gets high availability: running two or three agents on different hosts in the same group means a restart or a host failure doesn't stop workflows.

Each agent sends a heartbeat to Nimbus every 30 seconds over its TLS connection. If Nimbus hears nothing from an agent for 2 minutes, the agent is shown as **Offline** on **Settings > Agents**, and no new work is sent to it. When every agent in a group is offline, steps that use a connection through that group fail with CONN-503, the code Nimbus uses when a third-party app or the private connector agent is unavailable. Normal step retries apply, so a short outage is often absorbed by the retry after 30 seconds or 2 minutes.

Connector credentials stay in Nimbus, encrypted like any other connection, and are passed to the agent only for the duration of a step. The agent stores nothing on disk apart from its own identity file. The connectors that can run through an agent are those that talk to systems a client typically hosts privately:

- PostgreSQL, MySQL and Microsoft SQL Server
- SFTP
- HTTP Request, for internal REST APIs

Polling triggers on these connectors (a query or a new file) also run through the agent, so a workflow can start from an event inside the private network.

## Turning it on

An Admin registers the agent in the console first, then the client's infrastructure team starts the container with the token the console gives them.

1. Go to **Settings > Agents** and click **New agent group**. Give it a name that says where the agents run, for example `dc-frankfurt`.
2. In the group, click **Add agent**. Nimbus shows a one-time registration token. Copy it now; it is shown only once, can be used for one registration and expires 24 hours after it was created.
3. On a host inside the network that can reach the target systems, start the agent with the token (see the example below). The host needs outbound HTTPS to `agents.nimbus.omnicorp.example` on port 443.
4. Wait for the agent to appear as **Online** in the group, usually within a minute.
5. Repeat steps 2 to 4 on a second host for high availability.
6. Open the connection under **Connections**, set **Connect through** to the agent group and click **Test connection**.

```yaml
# docker-compose.yml on the agent host
services:
  nimbus-agent:
    image: omnicorp/nimbus-agent:3.9
    restart: unless-stopped
    environment:
      NIMBUS_AGENT_REGISTRATION_TOKEN: "nra_6Z2Q9MRT4K8WC1LD"
      NIMBUS_AGENT_NAME: "dc-frankfurt-01"
      # Optional: route the outbound TLS connection through a corporate proxy
      HTTPS_PROXY: "http://proxy.corp.client.example:3128"
    volumes:
      - nimbus-agent-data:/var/lib/nimbus-agent
volumes:
  nimbus-agent-data:
```

The registration token is needed only for the first start. The agent then writes its identity to `/var/lib/nimbus-agent`, which is why the example keeps that directory on a volume; if the volume is lost, register the agent again with a new token. To retire an agent, stop the container and click **Remove** next to it on **Settings > Agents**.

The connection test runs through the agent group, so a failure here means either the agents can't reach the database or SFTP server, or the credentials are wrong. The error message says which.

## Limits

| Limit | Value |
|---|---|
| Agent groups per workspace | 20 |
| Agents per group | 10 |
| Heartbeat interval | 30 seconds |
| Shown Offline after | 2 minutes without a heartbeat |
| Registration token | Single use, valid for 24 hours |
| Recommended host size per agent | 2 vCPU, 4 GB memory |
| Network requirement | Outbound TLS on port 443 only |

Agents don't count towards active connectors; the connectors that run through them do, in the usual way. A step running through an agent has the same 10-minute step timeout (WF-200) as any other step, and files passed through an agent are subject to the normal 100 MB per-file limit. Keep agents on the latest image tag: Nimbus supports the current and the previous minor release of the agent image, and older agents are shown with an **Update required** badge.

## When the Plan Tier changes

**Upgrade to Enterprise.** The upgrade takes effect immediately, so **Settings > Agents** appears as soon as the change is applied and an Admin can register agents straight away. Existing connections keep connecting directly until someone sets **Connect through** on them.

**Downgrade from Enterprise.** A downgrade takes effect at the end of the current billing period. At that point Nimbus closes every agent's connection and removes the agent groups. Connections that were set to connect through an agent are left in place but can no longer reach their target, so their steps fail with CONN-503 and the connections show "Needs attention". Before the downgrade date, work through these with the client:

1. List the connections that use an agent group (filter **Connections** by **Connect through**).
2. Decide, for each system, whether it can be made reachable from the internet or whether the workflows that use it should be deactivated.
3. Stop the agent containers on the client's hosts after the downgrade takes effect; they can't reconnect to a workspace without the entitlement.

If the client returns to Enterprise later, agents must be registered again with new tokens.
