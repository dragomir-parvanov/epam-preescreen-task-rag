---
id: nimbus-connector-sharepoint-online
title: SharePoint Online Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-04-20
owner: Integrations Team
---

The SharePoint Online connector lets workflows watch SharePoint document libraries and lists and write back to them: start a run when a file lands in a library or an item is added to a list, upload files, create list items and update the metadata columns of existing items. Typical uses are filing signed contracts from an e-signature tool into a Legal library, or turning list submissions into tickets.

The connection is authorised with OAuth 2.0 through Microsoft Entra ID, as a Microsoft 365 user. The connector only sees the sites, libraries and lists that this user can see.

## Prerequisites

- **A Microsoft 365 account** for the connection. A dedicated service account such as `nimbus-integration@fabrikam.onmicrosoft.com` is better than a person's account: when a person leaves and their account is disabled, every workflow using it stops.
- **SharePoint permissions** on each site and library the workflows use. Reading files and items needs Read; uploading files, creating items and updating metadata need Contribute (or Edit) on the library or list. Granting the account membership of the site's Members group usually covers both.
- **Consent in Microsoft Entra ID.** The Nimbus app asks for the delegated permissions below. Many tenants only let administrators consent to them, so a Global Administrator, Cloud Application Administrator or Application Administrator may need to grant tenant-wide admin consent once.

| Delegated permission | Used for |
|---|---|
| `Sites.ReadWrite.All` | Reading and writing list items and library metadata |
| `Files.ReadWrite.All` | Reading, uploading and replacing files |
| `offline_access` | Keeping the connection signed in with a refresh token |
| `User.Read` | Showing which account the connection uses |

- **A Builder or Admin role** in Nimbus. The connector is available on every Plan Tier.

## Creating the connection

1. In the Nimbus admin console, open **Connections** and click **New connection**.
2. Select **SharePoint Online** and enter a **Connection name**.
3. Click **Sign in with Microsoft**. A Microsoft sign-in window opens.
4. Sign in as the service account. If the tenant enforces multi-factor authentication or Conditional Access, complete it as usual.
5. Review the permissions on the consent screen and click **Accept**. If the screen says that admin approval is needed, ask a tenant administrator to open **Enterprise applications** in the Microsoft Entra admin centre, find **OmniCorp Nimbus** and choose **Grant admin consent**, then repeat from step 3.
6. Back in Nimbus, click **Test connection**. Nimbus reads the account's profile and lists the sites it can reach.
7. Click **Save**.

Sites are picked per step, not per connection, so one connection can serve every site the account has access to.

## Triggers and actions

| Name | Type | Configuration |
|---|---|---|
| New file in library | Polling trigger | Site, library, optional folder, and whether to include subfolders |
| New list item | Polling trigger | Site and list; optional filter on a column value |
| Upload file | Action | Site, library, folder path, file name and conflict behaviour (replace, rename or fail) |
| Create list item | Action | Site, list and column values |
| Update item metadata | Action | Site, list or library, item ID and the columns to change |

A file uploaded by Upload file is itself an item in the library, so its metadata can be set in a following Update item metadata step using `{{steps.<step-key>.output.item_id}}`.

## Field mapping

SharePoint columns have a display name, which users see, and an internal name, which the API uses. Nimbus maps columns by internal name. The two are often different: a column created as "Contract Owner" has the internal name `Contract_x0020_Owner`, and renaming a column later changes only its display name. The column pickers in the builder show both; when a step is configured by hand or through the API, use the internal name, which can be read from the column's settings page URL (`Field=` parameter).

An Update item metadata step that files a signed contract:

```json
{
  "site": "https://fabrikam.sharepoint.com/sites/Legal",
  "library": "Contracts",
  "item_id": "{{steps.upload_contract.output.item_id}}",
  "fields": {
    "Title": "{{trigger.body.envelope.subject}}",
    "Contract_x0020_Owner": "{{lower(trigger.body.sender.email)}}",
    "Counterparty": "{{trigger.body.recipients.0.company}}",
    "SignedDate": "{{now()}}",
    "Region": "{{default(trigger.body.custom_fields.region, 'Global')}}"
  }
}
```

Column types matter. A Person column takes the user's email address; a Choice column takes one of its configured choices exactly as written; a Date column takes an ISO 8601 value; a Lookup column takes the ID of the item in the source list, not its title. Managed metadata columns can be read but not written by this connector.

## Limits and behaviour

The polling triggers check for changes every 5 minutes using SharePoint's change tracking, so each new file or item starts one run even if many arrive between polls. A file that is still being uploaded or checked out when the poll runs is picked up at the next poll after it is checked in. Moving a file into the watched folder counts as a new file; renaming one doesn't.

Files of up to 100 MB can be uploaded by Upload file or passed from the New file in library trigger to later steps. Files over 4 MB are uploaded in chunks through an upload session, which is transparent to the workflow. A trigger that sees a larger file still starts a run, with the file's metadata, but the file content isn't attached.

Lists are read in pages of 200 items when a step looks items up. Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes, and SharePoint throttling is handled with backoff before those retries are used up.

## Troubleshooting

| Code | Typical cause | Fix |
|---|---|---|
| CONN-401 | The account's password was reset, its sessions were revoked, or a Conditional Access policy now blocks it | Open the connection, click **Reconnect** and sign in again. |
| CONN-403 | The account has Read but not Contribute on the library or list, or admin consent was removed | Grant the account Contribute, or ask the tenant administrator to grant consent again. |
| CONN-404 | The site URL, library or list was renamed or deleted, or the item ID no longer exists | Re-select the site and library in the step; check the item still exists. |
| CONN-429 | SharePoint throttled the tenant | No action; Nimbus backs off and retries the step. Persistent throttling points to other heavy tools in the tenant. |
| WF-400 | A required column resolved to empty, or a Choice value doesn't match a configured choice | Fix the expression or add a `default()`. |

If the sign-in window shows `AADSTS65001`, consent hasn't been granted; see step 5 of Creating the connection. For the Microsoft Teams side of the same tenant, see [Microsoft Teams Connector](nimbus-connector-microsoft-teams.md).
