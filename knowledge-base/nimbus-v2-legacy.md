---
id: nimbus-v2-legacy
title: Nimbus v2 Legacy Reference
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2026-05-12
owner: Platform API Team
---

This reference describes the legacy OmniCorp Nimbus platform for clients whose workspaces haven't moved to the current platform yet. It covers the platform's support timeline, its API limits, how its webhooks are signed, the SAML attributes it reads and its known limitations, and it ends with the steps for moving a workspace to the current platform.

The legacy platform receives security fixes only. New features, connectors and Plan Tier entitlements are released on the current platform, and the articles linked from "Upgrading to v3" describe it.

## End of support

Support for the legacy platform ends on 2027-03-31. The timeline is:

| Date | What changes |
|---|---|
| Until 2027-03-31 | Security fixes only. Workflows, API, webhooks and sign-in keep working as described here. |
| 2027-03-31 | End of support. No more fixes of any kind, and OmniCorp support no longer handles tickets about the legacy platform. |

Workspaces still on the legacy platform after that date keep running, but nothing that breaks will be fixed. Every client still on it should have an upgrade date agreed with their CSM well before the end of support.

## API limits (v2)

The API allows 300 req/min per workspace. The limit is the same for every Plan Tier: Starter, Business and Enterprise workspaces all get 300 req/min, and there is no burst allowance above it.

| Plan Tier | Limit |
|---|---|
| Starter | 300 req/min |
| Business | 300 req/min |
| Enterprise | 300 req/min |

A request over the limit is rejected with HTTP 429 and a `Retry-After` header giving the number of seconds to wait. The limit is counted per workspace across all of its API keys, so a busy integration can slow down every other integration in the same workspace. Spread batch jobs over time, and cache read results that don't change often.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 20

{"error": "rate limit exceeded"}
```

## Webhooks (v2)

Webhook deliveries are signed with HMAC-SHA1. The signature is computed over the raw request body with the endpoint's signing secret and sent in the `X-Nimbus-Signature` header as `sha1=` followed by the hex digest.

To verify a delivery:

1. Read the raw request body as bytes, before any JSON parsing.
2. Compute the HMAC-SHA1 of the body with the endpoint's signing secret.
3. Prefix the hex digest with `sha1=` and compare it with the `X-Nimbus-Signature` header using a constant-time comparison.
4. Reject the request if they don't match.

```python
import hashlib
import hmac


def is_from_nimbus(body: bytes, signature_header: str, signing_secret: str) -> bool:
    digest = hmac.new(signing_secret.encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(f"sha1={digest}", signature_header)
```

The signing secret is shown once, when the endpoint is registered. To replace it, delete the endpoint and register it again, then update the client's verification code with the new secret.

## SAML attributes (v2)

Single sign-on uses SAML 2.0. The service provider reads these attributes from the assertion, and the names are case-sensitive:

| Attribute | Required | Used for |
|---|---|---|
| `mail` | Yes | Login and unique identity |
| `firstName` | Yes | Display name |
| `lastName` | Yes | Display name |

The user's email address must arrive in the `mail` attribute. An assertion that carries the address under any other attribute name is rejected, even if the Name ID is an email address. Group attributes are ignored: roles are assigned by an Admin in the console.

Users are created by just-in-time provisioning on their first sign-in. As with any just-in-time setup, removing a user in the identity provider blocks their sign-in but leaves their account active until an Admin suspends it.

## Known limitations

- **No SCIM provisioning.** Users can't be created, updated or deprovisioned automatically from an identity provider. Clients who need automated leaver handling must upgrade.
- **No APAC data region.** Workspaces live in the EU or US region only.
- **No rate-limit headers.** Responses don't report the remaining request budget; clients find out only when they receive a 429.
- **No webhook auto-disable.** A failing endpoint keeps receiving delivery attempts until an Admin removes it.

## Upgrading to v3

Upgrading moves a workspace onto the current platform. Workflows, connectors, users and run history are carried over, and the workspace keeps its data region. Three things change for the client's own systems, so plan them first:

1. **Webhook verification.** The current platform uses a different signature header and algorithm. Update the client's verification code as described in [API Rate Limits and Webhooks](nimbus-api-webhooks.md) before the upgrade date.
2. **API rate limits.** Limits on the current platform depend on the Plan Tier, and Starter workspaces have no API access. Check the client's tier in [Plan Tiers and Entitlements](nimbus-plan-tiers.md) and the limits in [API Rate Limits and Webhooks](nimbus-api-webhooks.md).
3. **SAML attributes.** The email attribute name changes. Update the attribute statements in the identity provider as described in [Configuring SSO with SAML 2.0](nimbus-sso-saml.md), and run a test sign-in straight after the upgrade.

Once those are ready, the client's CSM books the upgrade window with OmniCorp support. The upgrade itself takes under an hour, during which workflow runs are paused and queued. After the upgrade, Enterprise clients can also set up [Automated User Provisioning with SCIM 2.0](nimbus-scim-provisioning.md).
