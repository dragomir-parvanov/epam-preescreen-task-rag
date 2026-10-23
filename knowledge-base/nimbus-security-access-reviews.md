---
id: nimbus-security-access-reviews
title: Running User Access Reviews
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-01-12
owner: Security & Compliance
---

Most security frameworks a client is audited against, SOC 2 and ISO/IEC 27001 among them, expect a periodic review of who can access each business system. For a Nimbus workspace that means checking every user's role, every Admin, every API key and every account that no longer signs in. This note describes the data Nimbus gives a reviewer, a review procedure a client's Admin can follow, and how to keep the result as evidence.

## Scope

An access review of a Nimbus workspace covers four things:

- **Users and roles.** Every active, invited and suspended user, with their role (Admin, Builder or Viewer) and when they last signed in.
- **Admins.** The short list of people who can manage users, roles, SSO, SCIM, API keys, webhooks and the Plan Tier, including the break-glass account where SSO is enforced.
- **API keys.** Every key, because a key acts with Admin permissions in its workspace and has no scopes.
- **Workflow ownership.** Workflows owned by people who are leaving, so ownership is transferred before their account goes.

Connections to third-party apps are reviewed on the third-party side, where the connected account's permissions live. Quarterly reviews are the most common cadence; the client's own policy decides.

## Controls in place

Nimbus doesn't run the review for the client, but it records the data a reviewer needs and makes removing access quick:

| What the reviewer needs | Where Nimbus keeps it |
|---|---|
| Role per user | Settings > Users, Role column; `role` on each user from `GET /users` |
| Last sign-in | Settings > Users, Last sign-in column; `last_sign_in_at` from `GET /users` |
| Account state | `status`: `active`, `invited` or `suspended` |
| API key creator and use | Settings > Developers > API keys; `created_by` and `last_used_at` from `GET /api-keys` |
| History of changes | Audit-log events such as `user.role_changed`, `user.suspended` and `api_key.revoked` |

Suspended users can't sign in and don't take a seat, and their workflows keep running until ownership is transferred. Revoked API keys get 401 from the next request. On Enterprise workspaces where SCIM is set up, leavers are handled from the IdP, so the review there mostly confirms that the IdP assignments are right; see [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md). Workspaces that use SSO with just-in-time provisioning only need the manual steps below for leavers; [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) explains why.

## Admin settings

A client's Admin runs the review like this:

1. Export the user list. Call `GET /users` with `limit=100` and follow `next_cursor` until it is null, keeping `email`, `role`, `status` and `last_sign_in_at` for each user. The script below writes a CSV the reviewer can annotate.
2. Review Admins first. Filter the export to `role` = `admin` and confirm each one with the client's system owner. Anyone who only builds workflows should be a Builder; change roles under Settings > Users as described in [Changing a User's Role](nimbus-admin-changing-roles.md).
3. Flag stale accounts. Mark every active user whose `last_sign_in_at` is empty or older than the threshold in the client's policy, often 90 days.
4. Remove stale access. Suspend each flagged account under Settings > Users or with `POST /users/{id}/suspend`, after transferring any workflows they own. Suspension is reversible, so it is the safer first step than deletion.
5. Review API keys. Under Settings > Developers > API keys, check every key's creator and last use. Revoke keys that are unused, and rotate keys whose creator has left, since keys belong to the workspace and keep working after that Admin is suspended; see [Creating and Rotating API Keys](nimbus-admin-api-keys.md).
6. Withdraw stale invitations from `GET /invitations` with `DELETE /invitations/{id}`.
7. Record the result as described under Evidence for auditors.

```python
import csv
import requests

API = "https://api.nimbus.omnicorp.example"
HEADERS = {"Authorization": "Bearer <api-key>"}

with open("nimbus-access-review.csv", "w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["id", "email", "role", "status", "last_sign_in_at", "decision"])
    cursor = None
    while True:
        params = {"limit": 100, **({"cursor": cursor} if cursor else {})}
        page = requests.get(f"{API}/users", headers=HEADERS, params=params).json()
        for user in page["data"]:
            writer.writerow([user["id"], user["email"], user["role"], user["status"], user["last_sign_in_at"], ""])
        cursor = page["next_cursor"]
        if cursor is None:
            break
```

Run the script with a key created for the review and revoke that key when the review is finished, so the review itself leaves no standing Admin credential behind.

## Shared responsibilities

| Activity | OmniCorp | Client |
|---|---|---|
| Recording roles, sign-ins and key use | Records them and exposes them in the console and API | Exports them for each review |
| Deciding who keeps access | Nothing | The system owner approves every role and key |
| Removing access | Enforces suspension, revocation and SCIM sync immediately | Suspends users, revokes keys and maintains IdP assignments |
| Leavers | Keeps workflows running after the owner is suspended | Transfers ownership and removes the leaver promptly |
| OmniCorp staff access to the workspace | Reviewed under OmniCorp's own SOC 2 controls | Nothing |

## Evidence for auditors

For each review, a client should keep three items together: the annotated CSV with a decision for every user and key, the name of the approver and the date of approval, and an audit-log export covering the days the changes were made. The export shows the `user.role_changed`, `user.suspended` and `api_key.revoked` events that prove each decision was carried out; [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md) explains the filters. Auditors sometimes also ask how OmniCorp reviews its own staff access, which is covered by the reports in [Compliance Reports and Certifications](nimbus-security-compliance-reports.md).
