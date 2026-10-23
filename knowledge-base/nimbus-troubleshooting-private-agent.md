---
id: nimbus-troubleshooting-private-agent
title: Troubleshooting the Private Connector Agent
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-03
owner: Support Engineering
---

The private connector agent is a small service that an Enterprise client runs inside their own network from the Docker image `omnicorp/nimbus-agent`. It opens an outbound TLS connection to Nimbus and keeps it open, and Nimbus sends steps for databases and SFTP servers that aren't reachable from the internet down that connection. The agent sends a heartbeat over the same connection; when Nimbus hasn't received one for 2 minutes, the agent is shown as Offline under **Settings > Agents**.

Installing and registering an agent is described in [Private Connector Agent](nimbus-tier-private-connector-agent.md). This reference starts from an agent that is installed but not working.

## Symptoms

- **Settings > Agents** shows the agent as **Offline**, with a "Last heartbeat" time more than 2 minutes ago.
- The agent flips between **Online** and **Offline** every minute or so.
- Steps on connections routed through the agent fail with CONN-503, while steps on other connections work.
- A newly installed agent never appears as **Online**, and its status stays **Waiting for first connection**.
- The connection test for a database behind the agent fails at the `connect` stage, although the database is up.

## Common causes

**The container isn't running.** The host was restarted, the container was started without a restart policy, or it was stopped during maintenance. This accounts for most Offline agents.

**A proxy blocks or inspects the outbound TLS connection.** Many corporate networks send outbound traffic through an HTTPS proxy. If the agent isn't told about the proxy, it can't connect at all. If the proxy decrypts and re-encrypts TLS for inspection, the agent rejects the proxy's certificate, because it only trusts Nimbus's own certificate chain unless told otherwise.

**The registration token has expired or was already used.** A registration token is shown once, works once, and expires 24 hours after it was created if it hasn't been used. After registering, the agent keeps its own credential in its data directory, `/var/lib/nimbus-agent`. If that directory isn't on a persistent volume, the agent loses its credential when the container is recreated and tries to register again with the old token, which fails.

**Two containers share one identity.** Copying the data volume, or starting a second container from the same compose file with the same volume, gives two running containers the same agent credential. Nimbus accepts one connection per agent, so each new connection replaces the other and the status flaps.

**The agent is fine, but the target isn't.** The agent forwards CONN-503 when it can't reach the database or SFTP server inside the network, for example because the hostname on the connection only resolves on a different network segment.

## Diagnosing the problem

1. Open **Settings > Agents** and note the agent's status, its **Last heartbeat** time and the **Host name** it last reported. A host name the client doesn't recognise points to a duplicated identity.
2. On the host, confirm the container is running and read its recent log:

```bash
docker ps --filter name=nimbus-agent
docker logs --since 30m nimbus-agent
```

3. Match the log against the lines below. Each points to one cause:

```text
2026-08-01T07:12:04Z ERROR connect failed: proxyconnect tcp: lookup proxy.corp.example: no such host
2026-08-01T07:12:34Z ERROR tls handshake failed: x509: certificate signed by unknown authority
2026-08-01T07:13:02Z ERROR registration rejected: token already used or expired
2026-08-01T07:14:10Z WARN  session replaced by another agent with the same identity
2026-08-01T07:15:45Z ERROR target unreachable: dial tcp erp-db.internal.example:5432: i/o timeout
```

4. If the log is clean and the agent is **Online**, test the affected connection with `POST /connections/{id}/test` and check which stage fails.
5. Ask whether anyone changed the proxy, the host or the container definition around the time the agent went **Offline**.

## Error reference

| Code or status | Meaning |
|---|---|
| CONN-503 | The private connector agent, or the system behind it, is unavailable. The step is retried on the step's normal schedule before the run fails. |
| CONN-401 | The agent is working, but the database or SFTP server rejected the connection's credentials. |
| WF-200 | A step routed through the agent ran for more than 10 minutes and was stopped, usually a slow query or a large file transfer. |
| **Offline** | No heartbeat for 2 minutes. Steps routed through the agent fail with CONN-503 until it reconnects. |
| **Waiting for first connection** | The agent was created in the console but no container has registered with its token yet. |

## Fixes

**Restart and persist.** Run the agent with a restart policy and a named volume for its data directory, so it survives host restarts and container upgrades without registering again:

```bash
docker run -d --name nimbus-agent --restart unless-stopped \
  -e NIMBUS_AGENT_REGISTRATION_TOKEN=<registration-token> \
  -e HTTPS_PROXY=http://proxy.corp.example:3128 \
  -v nimbus-agent-data:/var/lib/nimbus-agent \
  omnicorp/nimbus-agent:latest
```

**Proxy.** Set `HTTPS_PROXY` as above. If the proxy inspects TLS, ask the network team to exempt Nimbus's agent hostname, `agents.nimbus.omnicorp.example`, from inspection. Where policy forbids that, mount the proxy's CA certificate into the container and set `NIMBUS_AGENT_CA_BUNDLE` to its path.

**Expired or used token.** Tokens can't be extended. Under **Settings > Agents**, select the agent and click **New registration token**, then recreate the container with the new token and a persistent volume. The agent keeps its name, and connections routed through it don't need editing.

**Running two agents.** To run a second agent for redundancy, don't copy the first one's volume. Click **Add agent** to register it with its own token, then add both agents to the same agent group under **Settings > Agents > Groups** and route connections through the group. Nimbus sends each step to an Online agent in the group, so one agent can be restarted without CONN-503 errors. For a flapping status caused by a copied volume, stop the extra container, delete its volume and register it as a new agent.

**Target unreachable.** Use a hostname for the database or SFTP server that resolves from the agent's host, and test the connection again.

## Escalating to support

Collect the following before escalating:

- workspace id, the agent's name and its status history from **Settings > Agents**;
- the output of `docker logs --since 30m nimbus-agent`, with tokens removed;
- the container definition (`docker run` command or compose file), again without tokens;
- whether an HTTPS proxy is in the path and whether it inspects TLS;
- a run id and step key for a step that failed with CONN-503.
