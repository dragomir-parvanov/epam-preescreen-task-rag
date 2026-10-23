---
id: nimbus-release-2-16-2
title: Nimbus 2.16.2 Release Notes
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: release-notes
status: deprecated
last_updated: 2025-11-10
owner: Release Management
---

Nimbus 2.16.2 was applied to every legacy workspace on 2025-11-10. It is a security-fix release: it hardens the console's session cookie, fixes five vulnerabilities and updates third-party components with known security issues. It adds no features.

Because the session cookie changes name and attributes, every user is signed out once when the release is applied and has to sign in again. Clients who embed the console in another page or read its cookie from a script should read Deprecations and breaking changes first.

## Highlights

| Area | Change |
|---|---|
| Session cookie | Renamed to `__Host-nimbus_session` and set with `Secure`, `HttpOnly` and `SameSite=Strict` |
| Sessions | Session id rotated after every sign-in; all users signed out once at release |
| Password reset | Reset links are single-use and expire after 1 hour |
| Dependencies | TLS library, XML parser, templating engine and the run workers' base image updated |
| Features | None |

## New features

There are none in this release. 2.16.2 belongs to the 2.16.x maintenance line, which receives security fixes only. The fixed 12-hour session lifetime and the rest of the password and session rules described in [Password and Session Security (v2)](nimbus-v2-security-sessions.md) are unchanged; only the way the session is carried in the browser is tightened.

## Improvements

The dependency updates are the bulk of the release. None of them changes behaviour that clients can see:

- **TLS library** updated to the current patched release on the console, API and sign-in service. Connections still require TLS 1.2 or later.
- **XML parser** used to read identity providers' sign-in responses updated to a release that refuses external entity references outright.
- **Templating engine** behind the console's pages updated, closing a sandbox escape that could not be reached from any Nimbus page but was flagged by dependency scanning.
- **Run worker base image** rebuilt on a current operating-system release, picking up the outstanding security updates for its system libraries.

## Fixed issues

| Issue | Description |
|---|---|
| NIM-2846 | The session id was not rotated after a single sign-on sign-in, which allowed session fixation if an attacker could plant a cookie in the user's browser. |
| NIM-2851 | The delete form under Admin > API keys did not check the anti-forgery token, so a crafted page could trick a signed-in Admin into deleting a key. |
| NIM-2858 | Password reset links stayed valid after the password had been changed by other means and did not expire. They are now single-use and expire after 1 hour. |
| NIM-2863 | Run history CSV exports wrote cell values starting with `=`, `+`, `-` or `@` unchanged, so a spreadsheet could evaluate them as formulas. Such values are now prefixed with a single quote. |
| NIM-2870 | The session cookie was readable by scripts running in the console page, which raised the impact of any future cross-site scripting bug. |

NIM-2846 and NIM-2870 are the reason for the cookie changes in this release; the other three are independent fixes. NIM-2851 required an Admin to open a malicious page while signed in, and only ever affected the deletion of API keys, never their creation or display. NIM-2863 did not put Nimbus itself at risk: the danger was to whoever opened an export in a spreadsheet application, because a run's error text can contain data copied from a third-party app. Clients who keep older exports should treat them with the same care as any spreadsheet received from outside. None of the five issues is known to have been exploited, and the full advisories are available from OmniCorp support through the client's CSM.

## Deprecations and breaking changes

The cookie change is the only thing that can break a client's set-up. Nothing changes for API integrations, which authenticate with API keys and never use the cookie.

1. **One-time sign-out.** Every console session that existed before the release ended when it was applied. Users sign in again as usual; workflows, schedules and runs were not affected.
2. **Cookie name.** The cookie is now called `__Host-nimbus_session`. Browser extensions, test scripts or monitoring tools that looked for the old `nimbus_session` cookie by name have to be updated.
3. **No cross-site use.** With `SameSite=Strict`, the cookie is not sent when the console is opened inside a frame on another site or reached by a form posted from another site. Intranet portals that framed the console now show the sign-in page in the frame; open the console in its own tab instead.

The cookie a browser now receives after signing in looks like this:

```http
HTTP/1.1 302 Found
Location: https://app.nimbus.omnicorp.example/workflows
Set-Cookie: __Host-nimbus_session=8f3e1c0b9a7d4e26b5c4a1f09d2e7b63; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=43200
```

## Upgrade notes

OmniCorp applied 2.16.2 to every workspace; clients don't install anything. To help a client through it:

1. Warn the client's Admin before the release date that everyone will be asked to sign in again once, so the support desk isn't surprised.
2. If the client opens the console from an intranet portal in a frame, change the portal link so it opens the console in a new tab.
3. Ask the team that owns any browser automation or console monitoring to replace the old cookie name with `__Host-nimbus_session`.
4. Tell users that password reset emails must now be used within 1 hour and only once; a second click shows a "link expired" page and a new reset has to be requested.
5. If the client opens run history exports in a spreadsheet and processes them with macros, check that values starting with a single quote are handled.
6. Remind the client that the legacy platform receives security fixes only, and that their CSM can book the move to the current platform; the steps are in the upgrade section of [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md).
