---
id: nimbus-admin-bulk-user-import
title: Importing Users in Bulk from CSV
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-10-12
owner: Workspace Administration Team
---

Release 3.9.0 added bulk user import to OmniCorp Nimbus: an Admin uploads a CSV file of people, and Nimbus sends each of them an invitation with the name and role from the file. It replaces typing addresses into the invite dialog when a client onboards a whole department, and it is available on every Plan Tier.

An import only sends invitations; nobody becomes an active user until they accept. Everything in [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md) about expiry, resending and seats therefore applies to imported people as well.

## Before you begin

- You need the Admin role.
- The workspace must be on release 3.9.0 or later, which every v3 workspace is since 5 October 2026. The **Import CSV** button sits next to **Invite users** on **Settings > Users**.
- Prepare the file in UTF-8, comma-separated, with a header row. Spreadsheet tools usually offer this as "CSV UTF-8".
- Count the free seats on **Settings > Usage**. The seat limit for each tier is listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md).
- If the workspace creates users through SCIM provisioning, add people in the identity provider instead; an import would create accounts the identity provider doesn't know about.

## How it works

The file has four columns. The header names must match exactly, in any order:

| Column | Required | Accepted values |
|---|---|---|
| `email` | Yes | A valid email address, unique within the file |
| `firstName` | Yes | Up to 100 characters |
| `lastName` | Yes | Up to 100 characters |
| `role` | No | `Admin`, `Builder` or `Viewer`, in any letter case; an empty cell means Viewer |

A file holds up to 500 rows, not counting the header. For a larger group, split the list into several files and import them one after another.

```csv
email,firstName,lastName,role
amelie.durand@client.example,Amélie,Durand,Builder
tomasz.wojcik@client.example,Tomasz,Wójcik,Viewer
helen.osei@client.example,Helen,Osei,Admin
raj.mehta@client.example,Raj,Mehta,
```

Nimbus processes an upload in two passes. First it validates every row and the file as a whole, without sending anything. Rows that fail validation are set aside as row errors. Then it checks seats: active users plus the valid rows must fit within the seat limit; pending invitations don't count. If they don't, the whole import is stopped before any email goes out, and the report says how many seats are missing. Only when both passes succeed does Nimbus send one invitation per valid row.

An import never changes existing users. A row whose address already belongs to someone in the workspace is skipped, not updated, so an import can't be used to change roles in bulk; for that, see [Changing a User's Role](nimbus-admin-changing-roles.md).

Each imported invitation behaves like one sent by hand: it expires after 7 days, can be resent from the row menu, and takes a seat only once the person accepts.

### The import report

When the import finishes, the page shows a summary (rows read, invitations sent, rows skipped) and a **Download report** link. The report is a CSV with one line per input row and the columns `row`, `email`, `result` and `error`. The row errors you will meet most often:

| `error` | Meaning |
|---|---|
| `invalid_email` | The address isn't a valid email address. |
| `duplicate_in_file` | The same address appears more than once in the file; only the first is used. |
| `already_a_user` | The address belongs to an active or suspended user in this workspace. |
| `pending_invitation` | The address already has an invitation waiting. |
| `invalid_role` | The `role` cell isn't Admin, Builder or Viewer. |
| `missing_name` | `firstName` or `lastName` is empty. |

## Step-by-step

1. Open **Settings > Users** and click **Import CSV**.
2. Click **Download template** if you need a correctly headed empty file, fill it in, and save it as CSV UTF-8.
3. Drag the file onto the upload area or click **Choose file**.
4. Review the preview: Nimbus shows the first 10 rows as it has read them, the number of valid rows, the number of row errors and the seats the import will reserve.
5. Click **Send invitations**. The upload runs in the background; a file of 500 rows usually finishes within a minute.
6. Click **Download report** and keep it with the onboarding records.

There is no bulk import endpoint in the API. A script that needs to do the same sends one `POST /invitations` per row, with an `Idempotency-Key` so that a rerun doesn't invite anyone twice:

```python
import csv
import requests

API = "https://api.nimbus.omnicorp.example"
HEADERS = {"Authorization": "Bearer <api-key>"}

with open("new-starters.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        body = {
            "email": row["email"],
            "first_name": row["firstName"],
            "last_name": row["lastName"],
            "role": (row["role"] or "viewer").lower(),
        }
        r = requests.post(f"{API}/invitations", json=body,
                          headers={**HEADERS, "Idempotency-Key": "import-" + row["email"]})
        print(row["email"], r.status_code)
```

## Verifying the change

Filter **Settings > Users** by **Status: Invited**; every imported person appears with their role and an expiry date. The report's `result` column should read `invited` for each row you expected. On **Settings > Audit log**, the import shows as one `user.imported` event with the file name and row counts, followed by an `user.invited` event per person.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Missing required column: firstName" | The header is misspelt or uses a different case, such as `FirstName` or `first_name`. Use the template's header row. |
| "File has more than 500 rows" | Split the list into files of 500 rows or fewer and import them separately. |
| "Not enough seats: 12 more needed" | Suspend people who have left, or upgrade the Plan Tier, then upload the file again. Nothing was sent. |
| Accented names show as `Ã©` and similar | The file wasn't saved as UTF-8. Export it again as CSV UTF-8. |
| Every row fails with `invalid_email` | The file uses semicolons as separators. Save it again with commas. |
| Some people never got the email | Their row was skipped, or the mail was filtered. Check the report, then use **Resend invitation** for the ones that were sent. |
