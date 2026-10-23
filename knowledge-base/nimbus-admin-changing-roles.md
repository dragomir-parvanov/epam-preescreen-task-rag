---
id: nimbus-admin-changing-roles
title: Changing a User's Role
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-16
owner: Workspace Administration Team
---

Every member of an OmniCorp Nimbus workspace has exactly one role: Admin, Builder or Viewer. The role decides what the person can see and change, and an Admin can change it at any time from the admin console or the API. Clients usually ask for this when someone moves teams, takes over a set of workflows, or should no longer be able to edit production automation.

A role change applies immediately, but where the role is controlled matters. If the client assigns roles through their identity provider, a change made in Nimbus is only temporary; the sections below explain how to tell which case you are in.

## Before you begin

- You need the Admin role in the workspace. Admins can change anyone's role, including their own.
- Role changes are available on every Plan Tier, and a role change doesn't use an extra seat: every active user takes one seat whatever their role.
- Find out whether the workspace assigns roles from identity-provider groups. Open **Settings > Security > Single sign-on** and **Settings > Security > User provisioning (SCIM)**; if either has group-to-role mapping switched on, change the user's group membership in the identity provider rather than the role in Nimbus.
- If you are about to turn a Builder or Admin into a Viewer, check which workflows they own. A Viewer can't own a workflow, so those workflows have to move to someone else first.

## How it works

The three roles are cumulative: an Admin can do everything a Builder can, and a Builder everything a Viewer can.

| Capability | Viewer | Builder | Admin |
|---|---|---|---|
| View workflows, runs and run history | Yes | Yes | Yes |
| Create, edit, publish and run workflows | No | Yes | Yes |
| Create and reconnect connections | No | Yes | Yes |
| Own a workflow | No | Yes | Yes |
| Invite, suspend and delete users; change roles | No | No | Yes |
| Configure SSO, SCIM, API keys and webhooks | No | No | Yes |
| Change the Plan Tier | No | No | Yes |

A new role takes effect on the user's next request to Nimbus. If they have the console open, the next page they load reflects the new permissions; there's no need for them to sign out. A Builder demoted to Viewer who has unsaved edits open in the workflow builder loses the ability to save them.

A workspace must keep at least one Admin. Nimbus refuses any change that would leave it with none, whether that change is a demotion, a suspension or a deletion. It is good practice to keep at least two Admins, so that the client isn't locked out of user management if one of them leaves.

### Roles managed by the identity provider

When roles come from identity-provider groups, the identity provider is the source of truth. With single sign-on, a role set in the console is overwritten the next time the user signs in; with SCIM provisioning, it is overwritten at the next sync. In both cases the console shows a **Managed by identity provider** badge next to the role. The group mapping itself is covered in [Configuring SSO with SAML 2.0](nimbus-sso-saml.md) and [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md).

## Step-by-step

To change a role in the console:

1. Open **Settings > Users** and search for the person by name or email.
2. Open the row menu (**⋯**) and choose **Change role**.
3. Pick the new role from **Admin**, **Builder** or **Viewer**.
4. If you picked Viewer and the person owns workflows, the dialog lists them under **Workflows to transfer**. Choose a new owner for them, as described in [Transferring Workflow Ownership](nimbus-admin-transferring-workflow-ownership.md).
5. Click **Save role**. The new role shows in the user list straight away.

Through the API, send `PATCH /users/{id}` with the new role:

```bash
curl -X PATCH https://api.nimbus.omnicorp.example/users/usr_83k2qd \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

`role` takes `admin`, `builder` or `viewer`. The response is the updated user object. The API applies the same rules as the console: it won't demote the last Admin, and it won't make a workflow owner a Viewer until their workflows have been transferred.

## Verifying the change

The user's row on **Settings > Users** shows the new role, and `GET /users/{id}` returns it in the `role` field. Each change also writes a `user.role_changed` event to **Settings > Audit log**, with the old role, the new role and the Admin who made the change; [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md) shows how to filter for it.

For a workspace whose roles come from the identity provider, check again after the user's next sign-in or the next sync. If the role has reverted, the group mapping is still assigning the old one.

## Troubleshooting

| Symptom | What's going on | Fix |
|---|---|---|
| **Save role** is greyed out with "At least one Admin is required" | The user is the workspace's only Admin. | Promote another user to Admin first, then change this one. |
| API returns 409 `conflict` with "A workspace must keep at least one Admin" | Same as above, through the API. | Promote a second Admin before demoting this one. |
| API returns 409 `conflict` with "User owns workflows" | The user owns workflows and you asked for Viewer. | Transfer their workflows with `PATCH /workflows/{id}` and an `owner_id`, then retry. |
| The role reverts to the old value | Group-to-role mapping in the identity provider overwrote it. | Move the user to the right group in Okta or Microsoft Entra ID instead. |
| The user still can't edit after being made a Builder | Their browser tab is showing a page loaded before the change. | Ask them to reload the page. |
| **Change role** is missing from the row menu | You are signed in as a Builder or Viewer. | Ask one of the workspace's Admins to make the change. |
