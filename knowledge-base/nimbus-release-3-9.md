---
id: nimbus-release-3-9
title: Nimbus 3.9 Release Notes
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: release-notes
status: current
last_updated: 2026-10-05
owner: Release Management
---

Nimbus 3.9.0 reached every workspace on 2026-10-05. It has two headline additions: Admins can invite up to 500 people at a time by uploading a CSV file, and workflows can read and write Microsoft Dynamics 365 data through a new connector.

Nothing in this release changes how existing workflows, API calls or webhooks behave. The notes below are mainly for CSMs helping clients onboard a large team or replace hand-built Dataverse integrations.

## Highlights

| Change | Who gets it | Where |
|---|---|---|
| Bulk user import from CSV | Every Plan Tier | Settings > Users > Import CSV |
| Microsoft Dynamics 365 connector | Every Plan Tier, within its active connector limit | Connections > New connection |
| Invitation status filter and resend | Every Plan Tier | Settings > Users |

## New features

Both features are available as soon as the release is live; neither needs to be switched on.

### Bulk user import

An Admin opens Settings > Users, clicks **Import CSV** and uploads a UTF-8 file with a header row. One file can hold up to 500 rows; larger teams are split into several files. The file has four columns:

| Column | Required | Notes |
|---|---|---|
| email | Yes | The address the invitation is sent to. |
| firstName | Yes | Shown in the user list and on workflows the user owns. |
| lastName | Yes | As above. |
| role | No | Admin, Builder or Viewer. A blank cell gives the user Viewer. |

Before anything is sent, Nimbus validates the whole file and shows a preview with the number of valid rows and a list of row errors (for example *row 37: role "Editor" is not Admin, Builder or Viewer*). Rows whose address already belongs to a user or to a pending invitation are skipped and listed in the report. The import also checks the seat limit: if the active users plus the new invitations would go over what the workspace's Plan Tier allows, the import stops before any invitation goes out, and the preview says how many rows to remove. The limits themselves are in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

When the Admin confirms, every valid row gets an ordinary invitation email. The usual rules apply: each invitation expires after 7 days, and an invited user takes a seat only once they accept. The import report can be downloaded as a CSV with one result per row (`invited`, `skipped` or `error`). There is no bulk endpoint in the API; scripts keep calling `POST /invitations` once per user. The step-by-step guide is [Importing Users in Bulk from CSV](nimbus-admin-bulk-user-import.md).

### Microsoft Dynamics 365 connector

The connector signs in with OAuth 2.0 through a Microsoft Entra ID app registration. In the client's tenant, an administrator registers the app, creates a client secret, and then adds an application user for that app in the Power Platform admin center (Environments > *environment* > Settings > Users + permissions > Application users). The application user needs a security role that can read and write the tables the workflows use; a copy of *Basic User* with Organisation-level access to Account and Contact is a common starting point. The connection form asks for the environment URL (for example `https://contoso.crm4.dynamics.com`), the directory (tenant) ID, the application (client) ID and the client secret.

Triggers poll the environment every 5 minutes for new rows or updated rows in a chosen table. Actions create, update and upsert rows; upsert matches on an alternate key defined in Dynamics 365. Fields are addressed by their logical name (`emailaddress1`, `parentcustomerid`), not the display name shown in the Dynamics 365 forms, and the builder's field picker shows both. More detail is in [Microsoft Dynamics 365 Connector](nimbus-connector-dynamics-365.md).

## Improvements

- Settings > Users can be filtered by invitation status: Pending, Accepted or Expired.
- A **Resend** action on expired invitations sends a fresh invitation valid for another 7 days, without deleting and recreating it.
- `GET /invitations` accepts a `status` query parameter with the values `pending`, `accepted` and `expired`.
- **Test connection** under Connections now shows the third-party app's own error message alongside the Nimbus code, which makes CONN-403 easier to explain to the client.
- Run history CSV exports include the workflow version number of each run.
- The Approvals inbox shows the date on which each pending approval will expire.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-6377 | Changing a user's role from Builder to Viewer did not refresh their open builder tab, which kept showing the Publish button until reload. |
| NIM-6381 | Invitation emails used the inviter's display language instead of the workspace default. |
| NIM-6394 | The HubSpot trigger for updated contacts fired twice when two properties changed in the same second. |
| NIM-6402 | `GET /runs` returned `next_cursor` on the last page when exactly 100 runs matched with `limit=100`. |
| NIM-6415 | A transform step's expression preview showed an empty value for `{{default(x, y)}}` when `x` was missing. |
| NIM-6420 | Workflows moved into a folder disappeared from the workflow list's search results until the page was reloaded. |

## Deprecations and breaking changes

Nothing breaks in 3.9. No endpoint, field, event or console path was removed or renamed, and the CSV import adds a button rather than changing the existing **Invite users** dialog, which still works for a handful of addresses.

Clients that reach Dynamics 365 today through the HTTP Request connector can keep those workflows as they are. Moving to the new connector is optional; it mainly saves building OAuth token requests and paging by hand.

## Upgrade notes

To run a first import for a client:

1. Export the people to invite from the client's HR or identity system into a spreadsheet, one person per row.
2. Rename the columns to `email`, `firstName`, `lastName` and `role`, and fill `role` only where someone needs more than Viewer.
3. Save as CSV in UTF-8 and split the file if it has more than 500 rows.
4. Open Settings > Users > Import CSV, upload the file and fix every row error the preview lists.
5. Confirm the import, download the import report and keep it with the onboarding notes.
6. After 7 days, filter the user list by **Expired** and resend the invitations that weren't accepted.

A valid file looks like this:

```csv
email,firstName,lastName,role
amira.haddad@example.com,Amira,Haddad,Admin
tomas.novak@example.com,Tomas,Novak,Builder
li.wen@example.com,Li,Wen,
grace.okafor@example.com,Grace,Okafor,Viewer
```

To check which invitations are still open after the import, call the Invitations API with the new filter:

```http
GET /invitations?status=pending&limit=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```
