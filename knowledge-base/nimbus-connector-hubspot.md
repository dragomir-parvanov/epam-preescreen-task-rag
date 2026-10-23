---
id: nimbus-connector-hubspot
title: HubSpot Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-02-09
owner: Integrations Team
---

The HubSpot connector links a Nimbus workspace to one HubSpot account (portal) so that workflows can start on CRM events and keep contacts, companies, deals and tickets in step with other systems. It uses OAuth 2.0 and HubSpot's push notifications, so runs start within seconds of the change in HubSpot. It has been available since 3.0.0.

A Nimbus connection is tied to a single HubSpot account id. Clients with several HubSpot accounts, for example one per region, create one connection for each.

## Prerequisites

- **A HubSpot super admin** to install the Nimbus app. HubSpot only lets super admins grant an app access to the whole account, and the connection fails to install for anyone else.
- **HubSpot seats and objects**: tickets need Service Hub; deals and pipelines need Sales Hub or the free CRM's deal pipeline. Lists are available on every HubSpot subscription, though list counts vary.
- **A Nimbus Builder or Admin** to create the connection in the console.
- **Room under the active-connector limit** of the workspace's Plan Tier; see [Plan Tiers and Entitlements](nimbus-plan-tiers.md).

During the install HubSpot asks the super admin to approve these scopes:

| Scope | Used for |
|---|---|
| `crm.objects.contacts.read`, `crm.objects.contacts.write` | Contact triggers and actions |
| `crm.objects.companies.read`, `crm.objects.companies.write` | Company triggers and associations |
| `crm.objects.deals.read`, `crm.objects.deals.write` | Deal triggers and actions |
| `tickets` | Creating and updating tickets |
| `crm.lists.read`, `crm.lists.write` | Adding contacts to lists |
| `crm.schemas.contacts.read`, `crm.schemas.deals.read` | Reading custom property definitions for the mapping editor |

## Creating the connection

1. Open **Connections** in the Nimbus console and click **New connection**.
2. Choose **HubSpot** from the catalogue and give the connection a name, such as `HubSpot – EMEA portal`.
3. Click **Authorise**. HubSpot's account picker opens.
4. Sign in as a super admin, pick the HubSpot account and click **Connect app** after reviewing the scopes.
5. Nimbus returns to the connection page, which shows the HubSpot account id (the Hub ID) and the status **Connected**.
6. Click **Test connection** to confirm Nimbus can read the contact properties.

Uninstalling the app in HubSpot under **Settings > Integrations > Connected Apps** revokes the connection at once.

## Triggers and actions

| Trigger or action | Kind | Details |
|---|---|---|
| Contact created | Push trigger | One run per new contact. |
| Contact property changed | Push trigger | Pick one property, e.g. `lifecyclestage`; fires when its value changes. |
| Company created | Push trigger | One run per new company. |
| Deal created | Push trigger | One run per new deal. |
| Deal stage changed | Push trigger | Fires when `dealstage` changes; optional pipeline filter. |
| Create or update contact | Action | Matches on email address; creates the contact if none matches. |
| Create or update deal | Action | Updates by deal id, or creates; can associate the deal with a company and contacts. |
| Create ticket / Update ticket | Action | Needs a pipeline id and a pipeline stage id. |
| Add contact to list | Action | Adds contacts by id to a static (manual) list. Active lists are filter-based and can't be added to. |

Push triggers carry only the object id and the changed property. Nimbus fetches the full record before the run starts, so `{{trigger.body.properties.<name>}}` holds the current values.

## Field mapping

HubSpot properties are mapped by their **internal name**, not the label shown in HubSpot. A custom property labelled "Account tier" might have the internal name `account_tier` or `nimbus_account_tier`; find it under **Settings > Properties**, open the property and copy **Internal name**. Enumeration properties (dropdowns, radio buttons) take the option's internal value, not its label.

```yaml
# Step: Create or update contact
email: "{{lower(trigger.body.email)}}"
properties:
  firstname: "{{trigger.body.first_name}}"
  lastname: "{{trigger.body.last_name}}"
  lifecyclestage: "customer"            # internal value, not "Customer"
  account_tier: "{{default(trigger.body.tier, 'standard')}}"
  renewal_date: "{{trigger.body.renewal_date}}"   # YYYY-MM-DD
associations:
  company_id: "{{steps.find_company.output.id}}"
```

Date properties take a `YYYY-MM-DD` value, which HubSpot stores as midnight UTC. Multi-checkbox properties take the internal values joined with semicolons. The mapping editor lists custom properties once the connection is saved; a property created afterwards appears after clicking **Refresh fields**.

## Limits and behaviour

HubSpot delivers events to Nimbus within seconds and may batch several events into one delivery; Nimbus starts one run per event and drops repeats of the same event id. Events for records changed by the same connection are delivered as well, so a workflow that updates the property it listens on can loop. Guard such workflows with a condition step on the value, or listen on a different property.

| Behaviour | Value |
|---|---|
| Trigger delivery | Push, within seconds |
| Search and lookups | Paged with HubSpot's `after` cursor, up to 1,000 records per step |
| List membership changes | Up to 100 contact ids per **Add contact to list** call; longer lists are split by Nimbus |
| Files between steps | Up to 100 MB each |
| Step retries | 3 by default (0 to 5), after 30 seconds, 2 minutes and 10 minutes |

HubSpot enforces its own API call limits per account and per app. When it throttles the connector, the step reports CONN-429, and Nimbus backs off and retries it without counting that as a failed attempt.

## Troubleshooting

| Code | Typical HubSpot cause | What to do |
|---|---|---|
| CONN-401 | The app was uninstalled, or the super admin who installed it lost access. | A super admin clicks **Reconnect** and installs the app again. |
| CONN-403 | A scope is missing, usually after Nimbus added a feature that needs a new scope, or tickets are used without Service Hub. | Reconnect to approve the new scopes; check the HubSpot subscription. |
| CONN-404 | The record was deleted or merged into another; merged contacts keep only the surviving id. | Look the record up by email before updating it. |
| CONN-429 | HubSpot throttled the account. | No action; Nimbus retries. Spread large loops over several runs if it recurs. |
| WF-400 | `email` resolved to empty in Create or update contact. | Map a non-empty email or add a condition step. |
| `PROPERTY_DOESNT_EXIST` | A property was mapped by its label. | Use the internal name from **Settings > Properties**. |
