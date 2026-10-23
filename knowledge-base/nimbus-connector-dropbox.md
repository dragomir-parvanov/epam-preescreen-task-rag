---
id: nimbus-connector-dropbox
title: Dropbox Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-09-29
owner: Integrations Team
---

The Dropbox connector reacts to file changes in a Dropbox folder and works with files: it uploads and downloads them, creates shared links and moves them between folders. It works with personal Dropbox accounts and with Dropbox teams, including team folders and team spaces.

The connection is authorised with OAuth 2.0 by a Dropbox user. Changes reach Nimbus as push notifications, so a run normally starts within seconds of a file being added or changed.

## Prerequisites

1. A Dropbox account to authorise the connection. For a Dropbox team, use a member account that the team owns rather than a personal one, so the connection survives staff changes.
2. Edit access to every folder the workflows use. In a team space or team folder, the account needs the **Can edit** permission on that folder; **Can view** is enough only for triggers and downloads.
3. Team policy that allows the actions you plan to use. If the team admin has restricted shared links to team members only, Create shared link can only create team-only links.
4. A Builder or Admin role in Nimbus. The connector is available on every Plan Tier.

Nimbus requests these Dropbox scopes:

| Scope | Why |
|---|---|
| `files.metadata.read` | Listing folders and detecting changes |
| `files.content.read` | Download |
| `files.content.write` | Upload and move |
| `sharing.write` | Creating shared links |
| `account_info.read` | Showing the connected account and its team |

## Creating the connection

1. Open **Connections**, click **New connection**, and choose **Dropbox**.
2. Click **Connect to Dropbox** and sign in as the account chosen above.
3. On Dropbox's consent screen, check the requested permissions and click **Allow**.
4. For a team member account, Nimbus asks for the **Root**: choose **Personal folder** to work in the member's own Dropbox, or **Team space** to see team folders and the team space at the top level. Paths in every step are resolved from this root.
5. Click **Test connection**. Nimbus lists the top level of the chosen root.
6. Click **Save**.

The root can't be changed on an existing connection. To switch between Personal folder and Team space, create a second connection.

## Triggers and actions

| Name | Type | Notes |
|---|---|---|
| File changed in folder | Push trigger | Fires for added and modified files in a folder; optional **Include subfolders** and **Include deletions** |
| Upload file | Action | Writes a file to a path; mode **Add** (rename on conflict) or **Overwrite** |
| Download file | Action | Returns the file content for later steps |
| Create shared link | Action | Returns an existing link if the file already has one with the same settings |
| Move file or folder | Action | Moves or renames; optional **Rename on conflict** |

The trigger output includes `path_display`, `path_lower`, `id`, `rev`, `size` and `server_modified` for each changed file, and a `change` value of `added`, `modified` or `deleted`. Deleted entries only appear when **Include deletions** is on, and carry no `id` or `rev`.

## Field mapping

Dropbox paths always start with `/`, use `/` as the separator and have no trailing slash; the root itself is the empty string `""` rather than `/`. Paths are case-insensitive but case-preserving: `/Invoices/2026` and `/invoices/2026` are the same folder, and Dropbox keeps whichever capitalisation the folder was created with. That has two practical effects. First, compare paths with `path_lower`, never with `path_display`, because a user can change the display case without the path changing. Second, a workflow can't create two files whose names differ only in case; the second upload is renamed or overwrites the first, depending on the mode.

A file ID (`id:a4ayc_80_OEAAAAAAAAAXw`) stays the same when a file is moved or renamed, so prefer it to a path when a later step must find the same file again.

```yaml
- step: file_invoice
  action: Upload file
  path: "/Finance/Invoices/{{lower(trigger.body.customer_code)}}/{{trigger.body.invoice_number}}.pdf"
  content: "{{steps.render_pdf.output.file}}"
  mode: add
- step: share_with_customer
  action: Create shared link
  path: "{{steps.file_invoice.output.id}}"
  audience: public
  expires: "{{steps.compute_expiry.output.date}}"
```

Characters that Dropbox doesn't allow in names, such as `\`, `:`, `?`, `*`, `"`, `<`, `>` and `|`, make the step fail with WF-400 when they appear in a mapped path; strip them in a transform first.

## Limits and behaviour

- **Push triggers.** Dropbox notifies Nimbus that something changed, and Nimbus then reads the folder's changes from its last position. Each changed file starts one run, so a sync client uploading 300 files starts 300 runs; queued runs beyond the workspace's concurrent-run limit wait as queued (WF-310).
- **File size.** Upload file and Download file handle files of up to 100 MB. A trigger still fires for larger files, with their metadata, but Download file fails for them.
- **Moves.** Moving a folder moves everything in it in one call; large folders can take several minutes on Dropbox's side, which counts towards the 10-minute step limit (WF-200).
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. Upload in **Overwrite** mode and Create shared link are safe to retry; Upload in **Add** mode can leave a renamed copy if the first attempt actually succeeded.

## Troubleshooting

| Code | Dropbox reason | Fix |
|---|---|---|
| CONN-401 | The app was removed under **Settings > Connected apps**, or a team admin unlinked the member | Click **Reconnect** and authorise again. |
| CONN-403 | The account has **Can view** only, or team policy blocks the shared-link audience | Grant **Can edit**, or use a team-only audience. |
| CONN-404 | `path/not_found`: the path or ID doesn't exist from this connection's root | Check the root (Personal folder or Team space) and the path. |
| CONN-429 | `too_many_write_operations`: many writes to the same namespace at once | Nimbus backs off and retries; reduce parallel uploads into one folder. |
| WF-400 | An empty or invalid path, for example a missing customer code | Add `default()` or a condition before the step. |

When a team folder is used, a run that fails with CONN-404 straight after a reorganisation usually means the folder moved; file IDs keep working, paths don't. For Box, see [Box Connector](nimbus-connector-box.md).
