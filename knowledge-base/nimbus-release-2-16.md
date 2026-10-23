---
id: nimbus-release-2-16
title: Nimbus 2.16 Release Notes
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: release-notes
status: deprecated
last_updated: 2024-09-09
owner: Release Management
---

Nimbus 2.16.0 was released on 2024-09-09. It is the last feature release of the 2.x line: from here on, 2.16 receives maintenance releases numbered 2.16.x that carry security fixes only, and feature work moves to the next platform generation, which CSMs will introduce to clients separately.

The release adds a last sign-in date for every user, a JSON export of individual workflows and per-workflow failure recipients. It also enforces the 10-character password minimum for new passwords.

## Highlights

2.16 closes feature development on this platform. It focuses on things Admins have asked for when tidying up a workspace: seeing who still uses it, keeping a copy of important workflows and sending failure emails to the people who own each workflow. Clients don't need to change any integration for this release.

## New features

**Last sign-in date.** Admin > Users has a new **Last sign-in** column, which records the most recent successful sign-in by password or by single sign-on. Users who were invited but have never signed in show *Never*. The column can be sorted, which makes it quick to find accounts nobody has used for months and suspend them by hand. The same value is returned by the Users API as `last_sign_in_at`, an ISO 8601 timestamp in UTC, or `null` for a user who has never signed in.

**Workflow export.** Any Builder or Admin can download a workflow as a JSON file from the workflow's **⋯** menu with **Export JSON**. The file holds the trigger, every step with its field mappings, and the workflow's name and description. It never contains connection credentials: each step refers to its connection by name only, so a workflow imported elsewhere has to be pointed at a connection there. **Import JSON** on the Workflows page creates a new, inactive workflow from such a file.

**Failure recipients per workflow.** Each workflow's settings have a **Notify on failure** field that takes up to 10 email addresses. When a run of that workflow fails, those recipients get the failure email; the workspace-wide recipients still receive it too unless **Only notify these recipients** is ticked.

| Feature | Where | Who can use it |
|---|---|---|
| Last sign-in | Admin > Users, Users API | Admin |
| Export JSON / Import JSON | Workflow menu, Workflows page | Builder, Admin |
| Notify on failure | Workflow settings | Builder, Admin |

## Improvements

- The Users API accepts `sort=last_sign_in_at` together with the usual `page` and `per_page` parameters.
- Admin > Connections shows how many workflows use each connection, so unused connections are easier to spot and delete.
- Editing a connection's credentials in Admin > Connections now runs a test before saving and keeps the old credentials if the test fails.
- The Runs page remembers its filters for the length of the browser session.
- Workflow names can be up to 120 characters, up from 80.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-2588 | A user removed from a workspace while signed in could keep using the console until their session ended. |
| NIM-2593 | The Run history CSV export introduced in 2.15 used a semicolon separator for some browser locales. |
| NIM-2601 | Copying a workflow dropped the field mappings of steps inside a loop. |
| NIM-2614 | The Salesforce connector failed to update records with picklist values that contained a comma. |
| NIM-2622 | `GET /users` reported a `total` one higher than the real count when the workspace had a pending invitation. |
| NIM-2635 | Failure emails for workflows with non-ASCII names showed garbled subjects in some mail clients. |

## Deprecations and breaking changes

Two things change for clients:

1. **Password minimum.** Every new or changed password must be at least 10 characters. Existing shorter passwords keep working until the user next changes or resets theirs; nobody is signed out because of this. Accounts that sign in only through single sign-on are not affected.
2. **End of feature development.** No new features, connectors or API endpoints will be added to the 2.x line after this release, and any later 2.16.x release carries security fixes only. Requests for new functionality are logged against the next platform generation.

No endpoint, field or webhook event was removed. The deprecated BambooHR **Employee updated** trigger from 2.15 still runs; it will not be removed on this platform.

## Upgrade notes

The release is applied to every workspace automatically. To make use of it:

1. Ask the client's Admin to sort Admin > Users by **Last sign-in** and review users who haven't signed in for a long time.
2. Suspend the accounts that are no longer needed. Remember that users created by single sign-on are not removed when they leave the identity provider, so this review is the only cleanup.
3. Export the client's most important workflows with **Export JSON** and keep the files with the client's own change records.
4. Set **Notify on failure** on workflows owned by a specific team, so failures reach the people who can fix them.
5. Let users with short passwords know they will be asked for at least 10 characters at their next change.

To pull the same list through the API, sorted so the longest-unused accounts come first:

```http
GET /users?sort=last_sign_in_at&page=1&per_page=100 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {"id": "usr_1180", "email": "j.moreau@example.com", "role": "Builder", "last_sign_in_at": null},
    {"id": "usr_0942", "email": "k.lindqvist@example.com", "role": "Viewer", "last_sign_in_at": "2024-02-14T08:31:07Z"}
  ],
  "page": 1,
  "per_page": 100,
  "total": 2
}
```

For user management on this platform see [Inviting and Removing Users (v2)](nimbus-v2-admin-managing-users.md), and for password and session rules see [Password and Session Security (v2)](nimbus-v2-security-sessions.md).
