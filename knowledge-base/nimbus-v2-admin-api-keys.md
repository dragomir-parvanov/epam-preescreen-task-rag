---
id: nimbus-v2-admin-api-keys
title: Managing API Keys (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: guide
status: deprecated
last_updated: 2024-12-09
owner: Workspace Administration Team
---

API keys let a client's own systems call the Nimbus API: starting workflow runs from an ERP job, reading run results into a data warehouse, or inviting users from an onboarding script. On the legacy console they are created and deleted under **Admin > API keys**.

Keys on this platform never expire. A key works until an Admin deletes it, so the two habits that matter most are giving each integration its own key and deleting keys as soon as they are no longer needed.

## Before you begin

- **Role:** Admin. Only Admins see **Admin > API keys**.
- **Plan Tier:** every tier can create API keys.
- **A safe place for the key.** The full key is shown once, when it is created. Agree with the client beforehand where it will be stored, typically their own secrets manager or the configuration of the system that will use it.
- **One name per integration.** Decide what the key is for and who owns it on the client's side, for example "NetSuite nightly export – Finance IT". The name is the only way to tell keys apart later.

## How it works

A key is a long random string that the caller sends in the `Authorization` header:

```http
GET /workflows?page=1&per_page=50 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

Each key acts with Admin permissions in the workspace that created it. Keys have no scopes and can't be limited to read-only access or to particular workflows, which is one more reason to keep one key per integration: it is the only way to cut off one system without affecting the others.

The key lifecycle is short:

| Stage | What happens |
|---|---|
| Created | The full key is displayed once in a dialog. Nimbus stores only a hash of it and shows the last four characters afterwards. |
| In use | The key works for every request until it is deleted. **Last used** in the list shows when it last made a request. |
| Deleted | The key is revoked. Requests with it are refused with `401` from the next request onwards. Deletion can't be undone. |

There is no expiry date and no rotate action. To rotate a key, create a new one, switch the client's system over, confirm it works, and then delete the old key. During the switch both keys work, so there is no downtime.

API errors come back with the HTTP status and a plain message, for example `{"error": "invalid api key"}`, with no error code. List responses are paged with `page` (from 1) and `per_page` (default 50, maximum 100) and include a `total`. Request limits for keys are described in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Step-by-step

To create a key:

1. Go to **Admin > API keys** and click **Create API key**.
2. Enter a **Name** that says which integration uses it and who owns it.
3. Click **Create**. The dialog shows the full key.
4. Click **Copy** and paste the key straight into the client's secrets manager or the integration's configuration. Don't email it or paste it into a ticket.
5. Tick **I have stored this key** and click **Done**. The key is never shown again.

To revoke a key:

1. Go to **Admin > API keys**.
2. Find the key by its name and last four characters, and check **Last used** to see whether something still depends on it.
3. Click **Delete** and confirm by typing the key's name.

Keys can also be listed, created and deleted with the API, using an existing key:

```bash
# List keys (names, last four characters and last use only)
curl -s "https://api.nimbus.omnicorp.example/api-keys?page=1&per_page=50" \
  -H "Authorization: Bearer <api-key>"

# Create a key for a new integration; the response carries the full key once
curl -s -X POST https://api.nimbus.omnicorp.example/api-keys \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Warehouse loader - Data team"}'

# Delete (revoke) a key
curl -s -X DELETE https://api.nimbus.omnicorp.example/api-keys/key_4Tn8wQ1c \
  -H "Authorization: Bearer <api-key>"
```

A key can delete itself; the call succeeds and the key stops working straight after.

## Verifying the change

After creating a key, make one harmless request with it, such as `GET /workflows?page=1&per_page=1`. A `200` response with a `total` confirms it works, and **Last used** in **Admin > API keys** updates within a minute.

After deleting a key:

1. The key no longer appears in **Admin > API keys**.
2. A request with the old key returns `401` with `{"error": "invalid api key"}`.
3. The client's integration that should now use the replacement key keeps working. Check its own logs, or the run list in the console if it starts workflow runs.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| The client lost the key text | Keys are shown once and can't be retrieved | Create a new key, update the integration, delete the old one. |
| `401` with `invalid api key` | The key was deleted, or was copied with a missing character or extra space | Compare the last four characters with **Admin > API keys**; create a new key if it was deleted. |
| `401` on every request despite a valid key | The header is malformed, for example `Authorization: <api-key>` without `Bearer` | Send `Authorization: Bearer <api-key>`. |
| A security review asks for keys to expire | Keys here never expire | Rotate them on a schedule by hand: create, switch, delete. |
| Nobody knows which system uses an old key | It was shared between integrations or poorly named | Check **Last used**; if it is long unused, delete it. Otherwise create named keys per integration and retire the shared one. |
| The client wants read-only keys | Keys have no scopes and act as Admin | Not available; limit who holds keys instead. |

The current platform adds optional expiry dates to API keys; see [Creating and Rotating API Keys](nimbus-admin-api-keys.md) for clients planning their upgrade.
