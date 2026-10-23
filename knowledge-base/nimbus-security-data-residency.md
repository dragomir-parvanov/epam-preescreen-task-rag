---
id: nimbus-security-data-residency
title: Data Residency
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-05-18
owner: Security & Compliance
---

Data residency questions usually arrive as "Where is our data stored, and can it leave that region?" This note gives a CSM the answer for a v3 workspace: which data stays in the workspace's data region, how the region is chosen, why it can't be changed later, and which data leaves the region because the client has told a workflow to send it somewhere.

Nimbus hosts workspaces in three data regions: EU, US and APAC. Which regions a given workspace can use depends on its Plan Tier, which is set out in [Plan Tiers and Entitlements](nimbus-plan-tiers.md); this note doesn't repeat that table.

## Scope

The note covers the data Nimbus stores for a workspace and the places Nimbus sends data while running workflows. It applies to production workspaces and, where a client has one, to the sandbox workspace, which is created in the same region as the workspace it belongs to.

It doesn't cover the data a connected third-party app keeps on its own platform. Once a workflow writes a record to Salesforce or uploads a file to Box, that copy is governed by the client's contract with that vendor. Encryption of the stored data is covered in [Encryption in Transit and at Rest](nimbus-security-encryption.md).

## Controls in place

Everything Nimbus stores for a workspace is stored and processed in the workspace's region, and backups are kept in the same region:

| Data | Stored in the workspace's region |
|---|---|
| Workflow definitions, folders and version history | Yes |
| Runs: trigger payloads, step inputs, outputs and logs | Yes |
| Connection credentials, OAuth tokens and secrets vault values | Yes |
| Users, roles, invitations and SSO configuration | Yes |
| Audit log | Yes |
| Backups of all of the above | Yes, in the same region |

Workflow runs are executed by workers in the same region, so the data a run handles isn't processed elsewhere either. Inbound webhook triggers sent to `https://hooks.nimbus.omnicorp.example/t/<trigger-token>` are routed to the region that owns the trigger token before the payload is stored.

### Data that leaves the region

Some data leaves the region by design, because a workflow or a setting tells Nimbus to send it:

- **Connector steps.** A step that calls a third-party app sends the step's input to that app, wherever the app hosts the client's account. A Jira Cloud site hosted in the US receives data from an EU workspace if a workflow writes to it.
- **Webhook deliveries.** Event payloads such as `workflow.run.failed` go to the endpoints the client registered, wherever those endpoints are hosted.
- **Audit-log streaming.** On Enterprise, streamed audit events go to the Splunk, Datadog or HTTPS destination the client configures.
- **Notification emails.** Failure alerts and quota alerts contain the workflow name, run id and error code, and are delivered by email to the recipients the client sets.

A client who wants database or SFTP data to stay inside its own network can run the private connector agent, which reaches those systems from inside the client's network over an outbound TLS connection; see [Private Connector Agent](nimbus-tier-private-connector-agent.md).

### The region is fixed

The region is chosen when the workspace is created and can't be changed afterwards. Moving to another region means creating a new workspace there and migrating the workflows. Connection credentials and secrets can't be copied across, because they are never shown again after saving, so the client re-authorises every connection and re-enters every secret in the new workspace.

## Admin settings

An Admin chooses the region once, at creation. The full procedure is in [Creating a Workspace](nimbus-admin-creating-a-workspace.md); the residency-relevant steps are:

1. On the **Create workspace** page, enter the workspace name and time zone.
2. Under **Data region**, choose **EU**, **US** or **APAC**. Only the regions the Plan Tier includes can be selected.
3. Read the confirmation, which states that the region can't be changed, and click **Create workspace**.
4. After creation, open **Settings > Workspace** and check the read-only **Data region** field. Keep a screenshot for the client's records.

The region is also returned by the Workspace API, which is the easiest way to record it in a client's asset inventory:

```http
GET /workspace HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "ws_8Kq2Lm4Tz",
  "name": "Acme Operations",
  "data_region": "eu",
  "time_zone": "Europe/Berlin",
  "created_at": "2025-09-15T08:12:44Z"
}
```

`data_region` is one of `eu`, `us` or `apac`. It can't be changed with `PATCH`; see [Workspace API](nimbus-api-workspace.md).

## Shared responsibilities

| Responsibility | OmniCorp | Client |
|---|---|---|
| Choosing the region | Offers the regions the Plan Tier includes and fixes the choice at creation | Picks the region that matches its residency obligations before creating the workspace |
| Storage and processing | Stores, processes and backs up workspace data only in that region | Nothing further |
| Connected apps | Sends data only to the apps and accounts a workflow uses | Confirms where each connected app hosts its account, and whether that meets its obligations |
| Webhooks, streaming and email | Delivers only to the destinations the client configures | Chooses endpoints, streaming destinations and notification recipients with residency in mind |
| On-premises systems | Provides the private connector agent on Enterprise | Runs the agent inside its own network |
| Changing region | Supports migration through the CSM | Creates the new workspace, rebuilds connections and secrets, and deletes the old workspace |

## Evidence for auditors

A client can show its auditors the **Data region** field under **Settings > Workspace**, or the `data_region` value from `GET /workspace`, captured on the day of the review. For the controls behind it, the CSM can share OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate under NDA; both describe the hosting regions and backup locations. The data processing agreement that is part of every contract lists where processing happens and which sub-processors are involved; see [GDPR and Data Processing](nimbus-security-gdpr.md).

For data that leaves the region, the evidence sits with the client: the list of active connections under **Connections**, the registered endpoints under **Settings > Developers > Webhooks**, and any streaming destination under **Settings > Audit log > Streaming** together show every place a workspace sends data.
