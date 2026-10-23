---
id: nimbus-admin-deleting-a-workspace
title: Deleting a Workspace
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-10-20
owner: Workspace Administration Team
---

Deleting a workspace shuts down everything in it at once: its workflows stop, its connections and API keys stop working, and its users can no longer sign in to it. An Admin starts the deletion under **Settings > Workspace > Delete workspace**. OmniCorp support can restore a deleted workspace for 14 days; after that, every workflow, run, connection and user in it is permanently deleted and can't be recovered by anyone.

Clients typically delete a workspace after consolidating several workspaces into one, after moving to a new data region, or at the end of a contract. In each case the work worth doing is before the deletion, not after it.

## Before you begin

Check each of these with the client before anyone clicks **Delete**:

| Check | Why it matters |
|---|---|
| The person deleting is an **Admin** of this workspace | Builders and Viewers don't see the **Delete workspace** section. |
| The client's decision is in writing | Deletion is permanent once the restore window closes; the CSM should hold an email or ticket from an authorised contact. |
| Workflows that are still needed have been rebuilt or migrated elsewhere | Moving region or consolidating means creating the workflows in the other workspace first; see [Creating a Workspace](nimbus-admin-creating-a-workspace.md). |
| Everything the client must keep has been exported | Exports are impossible once deletion starts, even during the restore window. |
| Systems that call Nimbus have been told | Anything posting to an inbound webhook trigger or calling the API will start getting errors. |

Deletion is available on every Plan Tier, and there is no API endpoint for it: it can only be done in the console.

### Exporting what the client needs

Before deleting, export:

1. **Run history** as CSV from **Runs**, as described in [Searching and Exporting Run History](nimbus-admin-run-history.md).
2. **The audit log** as CSV from **Settings > Audit log**; see [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).
3. **Workflow definitions**, if the client wants a record of how each was built. `GET /workflows/{id}` returns the full definition as JSON.
4. **The user list**, with each user's email and role, from `GET /users`. It is the starting point for [Importing Users in Bulk from CSV](nimbus-admin-bulk-user-import.md) into another workspace.

Secret values in the vault and connection credentials can't be exported, because Nimbus never shows them after they are saved. The client must hold their own copies.

## How it works

Deletion has two phases.

**Deleted, restorable (first 14 days).** As soon as the Admin confirms:

- Every active workflow is deactivated. Scheduled triggers stop firing, and connector events and inbound webhook triggers are refused. Runs in progress are cancelled.
- Every API key is revoked; calls with them get `401 unauthorized` from the next request.
- Webhook endpoints stop receiving deliveries.
- Users can't sign in to the workspace. Users who also belong to other workspaces keep access to those.

During this phase nothing is wiped yet, so OmniCorp support can put the workspace back exactly as it was, with its workflows, connections, users and history.

**Permanently deleted (after 14 days).** Every workflow, version, run, connection, secret, user and API key in the workspace is erased. Backups that contain the workspace age out on OmniCorp's normal backup cycle and aren't restorable either.

What happens when a restored workspace comes back:

| Item | State after restore |
|---|---|
| Workflows | Restored, but **inactive**. An Admin or Builder reactivates each one. |
| Connections | Restored with their credentials. Any that expired in the meantime show "Needs attention". |
| API keys | Stay revoked. An Admin creates new ones. |
| Users | Can sign in again with the same roles. |

## Step-by-step

1. Complete the exports listed under **Exporting what the client needs**.
2. Go to **Settings > Workspace** and scroll to **Delete workspace**.
3. Click **Delete workspace**. Nimbus shows a summary: the number of active workflows, connections, API keys and users that will be affected.
4. Type the workspace name exactly as shown, for example `Acme Finance Automation`, into the confirmation field.
5. Enter your password, or sign in again with SSO if prompted.
6. Click **Delete permanently**.

Nimbus signs you out and sends a confirmation email to every Admin of the workspace with the deletion time and the date the restore window ends.

Although deletion itself has no endpoint, the API is useful straight before it to record what is about to go:

```bash
# Record the workspace id and region for the support ticket
curl -s https://api.nimbus.omnicorp.example/workspace \
  -H "Authorization: Bearer <api-key>"

# Save every workflow definition, 100 at a time
curl -s "https://api.nimbus.omnicorp.example/workflows?limit=100" \
  -H "Authorization: Bearer <api-key>" > workflows-page-1.json
```

Keep the workspace id (`ws_...`) from the first call. Support asks for it in any restore request.

## Verifying the change

After deletion:

- Signing in to `https://app.nimbus.omnicorp.example` no longer offers the workspace. Users in other workspaces see only those.
- An API call with any of the workspace's keys returns `401`.
- Every Admin has the confirmation email; the CSM should file it with the client's request.

To restore within the window, the client's Admin or the CSM opens a ticket with OmniCorp support quoting the workspace id. Support confirms the request with an Admin of the deleted workspace before restoring.

## Troubleshooting

| Problem | What to do |
|---|---|
| **Delete workspace** isn't visible | The user isn't an Admin. Another Admin must do it, or change their role first. |
| **Delete permanently** stays disabled | The typed name doesn't match exactly, including capitals and spaces. |
| The client deleted the wrong workspace | Open a support ticket with the workspace id straight away; restore is possible only within 14 days. |
| A restore was requested after 14 days | It can't be done; the data is gone. Start again with [Creating a Workspace](nimbus-admin-creating-a-workspace.md). |
| After restore, nothing runs | Restored workflows are inactive. Reactivate them, and create new API keys. |
| A partner system still gets 401 after restore | It uses an old API key, which stays revoked. Issue a new key. |
