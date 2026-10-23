---
id: nimbus-admin-creating-a-workspace
title: Creating a Workspace
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-09-08
owner: Workspace Administration Team
---

Clients don't create OmniCorp Nimbus workspaces themselves. When a contract is signed, or an existing client needs a second workspace, the CSM submits a workspace request and OmniCorp's provisioning team creates the workspace, assigns its Plan Tier and invites the client's first Admin. From then on the client's Admins run the workspace from the admin console.

This guide is for the CSM: what to collect from the client, which choices are permanent, what the client receives, and what they should do in their first session.

## Before you begin

Gather the following from the client before you open a request. The provisioning team won't start on an incomplete one.

| Detail | Example | Can it change later? |
|---|---|---|
| Workspace name | Northwind Finance Automation | Yes, by an Admin under **Settings > Workspace** |
| First Admin's name and work email | Sofia Lindqvist, sofia.lindqvist@northwind.example | The person can be replaced once other Admins exist |
| Data region | EU | **No** |
| Time zone (IANA name) | `Europe/Stockholm` | Yes, by an Admin |
| Plan Tier | Business, as in the contract | Yes, through an upgrade or downgrade |
| Signed contract reference | The order form number | — |

Check the data region carefully with the client's security or legal contact. Which tiers can use which region is listed in [Plan Tiers and Entitlements](nimbus-plan-tiers.md); a request for a region the contracted tier doesn't include is sent back.

The first Admin should be a named person at the client who will stay involved, not a shared mailbox. If the client plans to use single sign-on, the first Admin's email should be the address their identity provider will send, so that the account matches when SSO is switched on later.

## How it works

Provisioning sets up four things that every workspace needs:

1. **A workspace id.** The new workspace gets a `ws_` id, used in API responses, SAML URLs and support tickets. Record it in the CRM as soon as you receive it.
2. **A data region.** The workspace stores its workflows, run history, audit logs and user data in the region chosen in the request. The region is chosen when the workspace is created and can't be changed afterwards; moving region later means creating a new workspace and migrating the workflows.
3. **A Plan Tier.** The tier sets the workspace's limits and features from the first minute. All new workspaces run the current Platform Version, v3.
4. **The first Admin.** Nimbus sends that person an invitation with the Admin role. Like every invitation, it expires after 7 days.

The welcome email comes from `notifications@nimbus.omnicorp.example` with the subject "Your Nimbus workspace is ready". It contains the workspace name, the console address `https://app.nimbus.omnicorp.example`, the data region, and an **Accept and set password** button. Accepting creates the first Admin's account and takes the first seat.

Enterprise clients also get one sandbox workspace for testing, which doesn't count against the client's limits. It isn't requested here: once the production workspace exists, its Admin creates the sandbox under **Settings > Workspace > Sandbox**.

## Step-by-step

1. Open the CSM portal and choose **Requests > New workspace**.
2. Select the client account. The contracted Plan Tier is filled in from the CRM; check it against the order form.
3. Enter the workspace name, the first Admin's name and email, the data region and the time zone.
4. Leave the sandbox out of the request; an Enterprise client's Admin creates it later from the production workspace.
5. Submit the request. The provisioning team normally completes it within one business day, and the portal shows the new `ws_` id when it is done.
6. Tell the client's first Admin to expect the welcome email, and to accept it within 7 days.

The request is stored as a structured record that the provisioning team works from. If you raise requests in bulk through the portal's import, use the same fields:

```yaml
client_account: ACME-00417
workspace_name: Northwind Finance Automation
plan_tier: business
data_region: eu
time_zone: Europe/Stockholm
first_admin:
  name: Sofia Lindqvist
  email: sofia.lindqvist@northwind.example
contract_reference: OF-2025-1182
```

There is no public API call that creates a workspace. Once the first Admin has created an API key, `GET /workspace` and `GET /workspace/entitlements` confirm what was provisioned.

### First steps for the client

Suggest this order to the first Admin for their first session:

- Invite at least one more Admin, so that the workspace never depends on one person; see [Inviting Users and Assigning Roles](nimbus-admin-inviting-users.md).
- Confirm the name and time zone under **Settings > Workspace**.
- Set up single sign-on if the contracted tier includes it, before inviting the rest of the organisation.
- Add the first connections under **Connections**, and store any shared credentials in the secrets vault.
- Set failure-notification recipients under **Settings > Notifications**.

## Verifying the change

After the first Admin accepts, **Settings > Workspace** shows the workspace id, the data region and the creation date, and **Settings > Plan** shows the contracted Plan Tier. The CSM portal shows the request as **Completed** with the first Admin's acceptance time. `GET /workspace/entitlements` returns the limits for the tier, which should match the order form.

## Troubleshooting

| Problem | What to do |
|---|---|
| The first Admin didn't receive the welcome email | Ask them to check spam and quarantine for `notifications@nimbus.omnicorp.example`. The provisioning team can resend it from the request. |
| The welcome link has expired | The 7-day invitation lapsed. Ask provisioning to resend it; a new link is issued. |
| The wrong data region was requested | Region can't be edited. If nothing has been built yet, ask provisioning to delete and recreate the workspace; otherwise plan a migration. |
| The request was returned as "Region not in contracted tier" | The chosen region isn't part of the Plan Tier. Agree a different region or a contract change with the client. |
| The first Admin has left before accepting | Update the request with a new first Admin; provisioning revokes the old invitation and sends a new one. |
