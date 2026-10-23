---
id: nimbus-release-2-16-1
title: Nimbus 2.16.1 Release Notes
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: release-notes
status: deprecated
last_updated: 2025-05-12
owner: Release Management
---

Nimbus 2.16.1 is a security-fix release, applied to every workspace on the legacy platform on 2025-05-12. It contains no new features and no functional changes; it closes five vulnerabilities found through internal testing and external reports, and updates the components they came from.

The legacy platform is deprecated and receives security fixes only until its end of support. The dates and what they mean for a client are set out in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md), which CSMs should share with any client asking how long their workspace will be maintained.

## Highlights

- Five security fixes, two of them rated high: a weakness in how signed sign-in responses were checked, and stored cross-site scripting in run history.
- Webhook endpoints can no longer be registered with a URL that points inside OmniCorp's own hosting network.
- A deleted API key is now rejected from the very next request.
- No changes to workflows, connectors, the API's request and response formats or the console's layout.

## New features

None. 2.16.1 is a maintenance release of the 2.16 line and, like every later 2.16.x release, carries security fixes only. Requests for new functionality are answered by the current platform; see the upgrade section of [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).

## Improvements

The only other changes are hardening that clients won't notice in normal use:

- The console sends a stricter Content-Security-Policy header, which blocks inline scripts and limits where the console can be framed.
- Password reset emails now say which workspace the reset was requested for.
- Error pages no longer show the name and version of the web server, which made it easier to match the console against public vulnerability lists.
- Third-party components used by the sign-in service, the run workers and the console were updated to their latest patched versions, including the XML parsing library used to read sign-in responses from identity providers.

## Fixed issues

| Issue | Severity | Description |
|---|---|---|
| NIM-2731 | High | A signed sign-in response from the identity provider could be altered so that the signature check passed on one element while the user details were read from another (XML signature wrapping). Responses are now rejected unless the signed element is the one the user details are read from. |
| NIM-2738 | High | A workflow step name containing HTML was rendered without escaping on the Runs page, allowing stored cross-site scripting by a Builder against other users. |
| NIM-2744 | Medium | A webhook endpoint URL could name a host inside OmniCorp's hosting network, so delivery attempts could be used to probe internal services. |
| NIM-2752 | Medium | The `return_to` parameter of the sign-in page accepted any external URL after sign-in (open redirect). It now accepts only console paths. |
| NIM-2759 | Low | After an API key was deleted under Admin > API keys, requests with it could still succeed for up to a minute while the old value was cached. |

When a client asks whether they were exposed, the answer depends on the issue. NIM-2731 concerned only workspaces that sign users in through single sign-on; workspaces using passwords alone were never affected. NIM-2738 could only be triggered by someone who already had the Builder or Admin role in the same workspace, because only they can name steps. NIM-2744 put OmniCorp's systems at risk rather than client data, and NIM-2759 matters only to a client who deleted a key because they believed it had leaked.

Each issue was reported or found before the release, and none is known to have been exploited. A reporter who wants credit is named in the security advisory that the CSM can request from OmniCorp support.

## Deprecations and breaking changes

Nothing that works correctly today breaks. Two fixes can change what a client sees if they relied on the old behaviour:

1. **Internal webhook URLs.** Registering an endpoint whose hostname resolves to OmniCorp's hosting network now fails, and existing endpoints of that kind stop receiving deliveries. Real client endpoints are never in that network, so this affects only test set-ups that pointed at a Nimbus hostname by mistake.
2. **Sign-in redirects.** Links that sent users to an external site after signing in, through `return_to`, now land on the console's home page instead.

A registration that is refused returns the usual plain-message error:

```http
POST /webhooks HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
Content-Type: application/json

{"url": "https://hooks.internal.nimbus.omnicorp.example/test", "events": ["workflow.run.failed"]}

HTTP/1.1 400 Bad Request
Content-Type: application/json

{"error": "endpoint URL resolves to a reserved network and can't be used"}
```

## Upgrade notes

2.16.1 was applied by OmniCorp to every workspace; there is no version to choose and nothing to install. After the release:

1. Open Admin > Webhooks and confirm that each endpoint still shows recent successful deliveries. An endpoint marked *Refused* was pointing at a reserved host and has to be deleted and registered again with the client's real URL.
2. If the client uses single sign-on, ask their Admin to sign in through it once after the release, to confirm that their identity provider's signed responses are still accepted.
3. If the client deleted an API key in the days before the release because it might have leaked, ask them to check their own logs for calls made with it shortly after the deletion.
4. Use the release as a prompt to agree an upgrade date. The client's CSM books the move to the current platform with OmniCorp support, and the upgrade itself takes under an hour; the preparation steps are listed in [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).
