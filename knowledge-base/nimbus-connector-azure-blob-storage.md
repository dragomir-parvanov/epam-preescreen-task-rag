---
id: nimbus-connector-azure-blob-storage
title: Azure Blob Storage Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-23
owner: Integrations Team
---

The Azure Blob Storage connector, added in 3.1.0, connects workflows to containers in an Azure storage account. A workflow can start when a new blob appears in a container and can upload, download, list and delete blobs. The connection authenticates with either the storage account's connection string or a shared access signature (SAS) token.

Most connection failures with this connector come from SAS tokens reaching their expiry time, so read the SAS notes below before choosing.

## Prerequisites

Before you connect, decide which credential to use:

| Credential | Scope of access | Expires | Good for |
|---|---|---|---|
| Connection string (account key) | Every container in the storage account | Never, until the key is rotated | Storage accounts dedicated to the integration |
| Account SAS token | Chosen services and resource types | At its `se` (signed expiry) time | Broad access with a known end date |
| Container (service) SAS token | One container | At its `se` time | Least privilege for a single container |

A SAS token must carry the permissions the workflows use:

| Permission | Letter | Needed for |
|---|---|---|
| Read | `r` | Download blob |
| Add / Create | `a` / `c` | Upload blob (new blobs) |
| Write | `w` | Upload blob (overwrite) |
| Delete | `d` | Delete blob |
| List | `l` | New blob trigger, List blobs, Test connection |

An account SAS also needs **Allowed services** set to Blob and **Allowed resource types** set to Container and Object. You also need a Nimbus Builder or Admin to create the connection, and room under the active-connector limit of the Plan Tier ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)). Storage accounts with public network access turned off can't be reached from Nimbus over the internet; on Enterprise, a private connector agent registered under **Settings > Agents** can reach them from inside the client's network instead.

## Creating the connection

1. In the Azure portal, open the storage account. For a connection string, go to **Security + networking > Access keys** and copy **Connection string** under key1. For an account SAS, go to **Security + networking > Shared access signature**, choose the permissions above, set an end date, and click **Generate SAS and connection string**. For a container SAS, open the container, choose **Shared access tokens**, and generate one there.
2. In Nimbus, open **Connections > New connection** and select **Azure Blob Storage**.
3. Enter a **Connection name** and choose **Connection string** or **SAS token** under **Authentication**.
4. Paste the connection string, or paste the **Storage account name** and the SAS token (with or without the leading `?`).
5. Optionally set a **Default container**, for example `invoices`.
6. Click **Save** and then **Test connection**, which lists one blob in the default container (or one container in the account) and shows **Connected**. For a SAS token, the connection page also shows the token's expiry date, read from its `se` parameter.

The two formats look like this:

```text
DefaultEndpointsProtocol=https;AccountName=acmefinance;AccountKey=<base64 account key>;EndpointSuffix=core.windows.net

sv=2022-11-02&ss=b&srt=co&sp=rwdlac&se=2027-01-31T23:59:59Z&spr=https&sig=<signature>
```

## Triggers and actions

| Name | Kind | Inputs and outputs |
|---|---|---|
| New blob | Polling trigger | Container and optional **Prefix** (a virtual folder such as `inbound/2026/`). Outputs `container`, `name`, `size`, `content_type`, `etag`, `last_modified`. |
| Upload blob | Action | Container, blob name, file from an earlier step, optional content type and **Overwrite** (off by default). Uploads block blobs. |
| Download blob | Action | Container and blob name; outputs a file for later steps. |
| List blobs | Action | Container and optional prefix; outputs names, sizes and last-modified times. |
| Delete blob | Action | Container and blob name; **Include snapshots** deletes the blob's snapshots too. |

With soft delete turned on in the storage account, deleted blobs stay recoverable in Azure for the account's retention period.

## Field mapping

Blob names are built with expressions. Azure treats `/` in a name as a virtual folder, so a date-based layout keeps the container browsable:

```yaml
# Step: Upload blob
container: invoices
name: "processed/{{trigger.body.supplier_id}}/{{lower(trigger.body.invoice_number)}}.pdf"
file: "{{steps.render_pdf.output.file}}"
content_type: application/pdf
overwrite: false
```

To move a blob after processing, chain **Download blob**, **Upload blob** to the new name and **Delete blob** on the old one.

## Limits and behaviour

The **New blob** trigger polls every 5 minutes and starts one run for each block blob whose creation time is after the previous poll. Overwriting an existing blob doesn't start a run, and blobs already in the container when the workflow is activated are skipped. Append and page blobs are ignored.

Azure returns up to 5,000 blobs per list page; **List blobs** follows the continuation marker up to **Max results** (default 1,000, maximum 50,000). Uploads and downloads are limited to 100 MB per blob, the Nimbus limit for files passed between steps.

Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Azure's `ServerBusy` answers are shown as CONN-429 and retried after a back-off.

## Troubleshooting

| Code | Azure error code | Cause and fix |
|---|---|---|
| CONN-401 | `AuthenticationFailed` ("Signature not valid in the specified time frame") | The SAS token has expired. Generate a new token with a later `se`, paste it into the connection, and click **Test connection**. Every step using the connection fails with CONN-401 until then. |
| CONN-401 | `AuthenticationFailed` (signature mismatch) | The account key was rotated, which invalidates the connection string and any SAS signed with it. Paste the new credential. |
| CONN-403 | `AuthorizationPermissionMismatch` | The SAS lacks a permission letter, e.g. `d` for Delete blob. |
| CONN-403 | `AuthorizationFailure` | The storage account's firewall rejects the call. |
| CONN-404 | `ContainerNotFound`, `BlobNotFound` | The container or blob name is wrong, or the blob was deleted. |
| CONN-429 | `ServerBusy` | Azure throttled the account; Nimbus retries. |
| (step error) `BlobAlreadyExists` | **Overwrite** is off and the name exists. | Turn on **Overwrite** or make the name unique. |

Set a reminder before a SAS token's expiry and replace it ahead of time; the connection's **Needs attention** status and the `connector.disconnected` event only appear once it has already expired.
