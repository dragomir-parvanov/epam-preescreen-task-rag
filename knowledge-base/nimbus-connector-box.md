---
id: nimbus-connector-box
title: Box Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-10-27
owner: Integrations Team
---

The Box connector moves files and their metadata in and out of Box. Workflows can start the moment a file is uploaded to a folder or a folder changes, and can upload files, move them, create shared links and apply metadata templates. A common pattern is an intake folder in Box: a file arrives, a workflow classifies it, applies metadata, and moves it to its final folder.

Box events reach Nimbus as push events, usually within seconds. The connection is authorised with OAuth 2.0, either as an individual Box user or as the service account of a Box app approved by the client's Box administrator.

## Prerequisites

Choose the identity first, because it decides what the connector can see:

| Identity | When to use it | What it can reach |
|---|---|---|
| Box user | Small teams; workflows that act on one person's folders | Everything that user can access |
| Service account | Production workflows that shouldn't depend on one employee | Only folders where the service account has been added as a collaborator |

Whichever identity is used, it must be a **collaborator** on every folder the workflows read from or write to, with the **Editor** or **Co-owner** role. Viewer and Previewer can't upload, move or apply metadata, and Uploader can't read. Collaboration is set from the folder's **Sharing** panel in Box by inviting the user or the service account's email address.

The service account option also needs a Box administrator to authorise the Nimbus app once in the **Box Admin Console** under **Apps > Platform Apps Manager**. Nimbus requests the `root_readwrite` and `manage_webhook` scopes; applying an enterprise metadata template also needs the template to exist already, created by a Box admin under **Content > Metadata**.

The connector is available on every Plan Tier, and a Builder or Admin role is needed to create the connection.

## Creating the connection

1. Go to **Connections > New connection** and choose **Box**.
2. Under **Authorise as**, pick **Box user** or **Service account**.
3. For **Box user**, click **Connect to Box**, sign in to Box and click **Grant access to Box**. For **Service account**, enter the **Enterprise ID** shown in the Box Admin Console under **Account & Billing**, then click **Connect to Box**; a Box administrator signs in and confirms.
4. Click **Test connection**. Nimbus shows the authorised identity and the number of top-level folders it can see. A service account that hasn't been collaborated on any folder shows zero, which is expected until collaboration is set.
5. Click **Save**.

## Triggers and actions

| Name | Kind | Box event or call |
|---|---|---|
| File uploaded | Push trigger | `FILE.UPLOADED` in the chosen folder |
| Folder event | Push trigger | Any of `FOLDER.CREATED`, `FOLDER.RENAMED`, `FOLDER.MOVED`, `FILE.MOVED`, `FILE.TRASHED` in the chosen folder |
| Upload file | Action | Uploads a file, or a new version if the name exists |
| Move item | Action | Moves a file or folder to another folder |
| Create shared link | Action | Creates or updates a shared link with access level and optional expiry |
| Add metadata | Action | Applies an enterprise metadata template instance to a file |

When a workflow with a Box trigger is activated, Nimbus registers a Box webhook on the chosen folder; deactivating the workflow removes it. Events in subfolders are included, because Box webhooks on a folder cover its whole tree.

## Field mapping

Box identifies files and folders by numeric ID, not by path. The folder ID is the number at the end of the folder's URL in the Box web app (`https://app.box.com/folder/214093877112`); the root folder is always `0`. The builder's folder picker fills IDs in for you, and expressions can pass them on from earlier steps.

This step sequence takes the file from a File uploaded trigger, applies a `contractInfo` template and creates a link that expires:

```yaml
- step: tag_contract
  action: Add metadata
  file_id: "{{trigger.body.source.id}}"
  template: enterprise.contractInfo
  fields:
    counterparty: "{{steps.classify.output.counterparty}}"
    contractType: "{{default(steps.classify.output.type, 'Other')}}"
    receivedOn: "{{now()}}"
- step: share_for_review
  action: Create shared link
  item_id: "{{trigger.body.source.id}}"
  access: company
  unshared_at: "{{steps.compute_expiry.output.date}}"
```

Metadata fields are addressed by the template's field keys (`contractType`), not by the labels shown in Box. For an enum field, the value must be one of the template's options exactly. The link URL is available afterwards as `{{steps.share_for_review.output.shared_link.url}}`. Box allows the `open` access level only if the enterprise's sharing settings permit public links; otherwise use `company` or `collaborators`.

## Limits and behaviour

- **Event delivery.** Push events normally arrive within seconds. Box may deliver the same event twice; the trigger output includes Box's event ID, which a condition step can use to skip duplicates when a workflow must not run twice.
- **File size.** Files of up to 100 MB can be uploaded or passed between steps. Uploads over 50 MB use Box's chunked upload automatically.
- **Name conflicts.** Upload file has an **If the name exists** setting: upload a new version (the default), rename with a suffix, or fail the step.
- **Paging.** Folder listings are read 1,000 items at a time.
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Upload file and Add metadata are safe to retry; Move item fails harmlessly with CONN-404 if the item has already moved.

## Troubleshooting

| Code | What it usually means for Box | What to do |
|---|---|---|
| CONN-401 | Access was revoked under **Account Settings > Apps** in Box, the Box user was deactivated, or the refresh token went unused for too long | Click **Reconnect** on the connection, or reconnect with a different identity. |
| CONN-403 | The identity isn't a collaborator on the folder, or has a role below Editor | Invite it to the folder as Editor. |
| CONN-404 | The file or folder ID doesn't exist, or the item is in the trash | Check the ID; restore the item from the trash if needed. |
| CONN-429 | Box throttled the connection | Nothing; Nimbus waits and retries. |
| WF-400 | A metadata field value isn't one of the template's options, or a required field is empty | Map a valid option or add a `default()`. |

A trigger that stops firing after its folder was moved to another owner usually means the webhook was removed by Box; deactivate and reactivate the workflow to register it again. For the Dropbox equivalent, see [Dropbox Connector](nimbus-connector-dropbox.md).
