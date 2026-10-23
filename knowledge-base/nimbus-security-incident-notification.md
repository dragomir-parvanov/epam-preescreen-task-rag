---
id: nimbus-security-incident-notification
title: Security Incident Notification
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-04-27
owner: Security & Compliance
---

When OmniCorp confirms a security incident that affects a client's Nimbus workspace, the client hears about it from OmniCorp directly and from their CSM. This note sets out what counts as a notifiable incident, who receives the notice, what it contains, the 72-hour commitment for personal-data breaches, and what the CSM does from the first hour onwards.

Clients ask about this process in almost every security questionnaire, and they ask again, more urgently, when an incident is in the news. The answers below are the ones to give in both cases.

## Scope

The note covers incidents on OmniCorp's side of the platform: unauthorised access to workspace data held by Nimbus, compromise of connection credentials or secrets stored by Nimbus, a vulnerability that was actively exploited, or loss of data integrity. A personal-data breach is any of these that involves personal data the client controls.

It doesn't cover incidents in the client's own systems or connected applications, such as a phished Admin password or a compromised Salesforce org. Those are the client's to handle, though OmniCorp support helps with workspace evidence. Vulnerability reports that haven't led to an incident follow [Vulnerability Reporting and Security Fixes](nimbus-security-vulnerability-disclosure.md).

## Controls in place

OmniCorp's incident response team runs a documented procedure that is tested yearly and covered by the SOC 2 Type II report. For clients, the commitments are:

- **Personal-data breaches:** clients are notified without undue delay, and within 72 hours, of a confirmed personal-data breach. The clock starts when OmniCorp confirms the breach, not when the investigation ends.
- **Other security incidents that affect the client's workspace:** notified without undue delay once confirmed, on the same channels.
- **Updates:** at least once every business day while the incident is open, and a final report when it closes.

A notice is sent by email from security-notices@omnicorp.example to the workspace's Security contacts and to every Admin, and it also appears as a banner in the admin console for Admins. The CSM receives a copy at the same time. Notices are never sent only to the CSM to pass on.

Each notice contains:

| Field | What it says |
|---|---|
| Reference | An incident id, for example `SI-2026-014`, used in every update |
| What happened | The nature of the incident and when it started and was detected |
| Data affected | Categories of data and, where known, the approximate number of users or records |
| Likely consequences | What the incident could mean for the client and the people whose data is involved |
| Measures taken | What OmniCorp has done to contain and fix it |
| Client actions | Anything the client should do, such as reconnecting connections or rolling a webhook signing secret |
| Contact | The incident lead in OmniCorp Security & Compliance |

When the full picture isn't known within 72 hours, the first notice says what is known and the rest follows in updates, as GDPR allows.

## Admin settings

Notices only reach the right people if the workspace's contacts are kept current. A client's Admin sets them up once and checks them at each access review:

1. Go to Settings > Workspace.
2. Under Security contacts, add the client's security team mailbox and, where the client has one, their data protection officer.
3. Under Settings > Users, confirm that every Admin is a current employee with a monitored mailbox; Admins receive notices too.
4. On Enterprise workspaces, set up streaming under Settings > Audit log > Streaming so the client's SIEM holds its own copy of workspace activity for any investigation; see [Audit Log Streaming](nimbus-tier-audit-log-streaming.md).
5. Ask the mail team to make sure messages from security-notices@omnicorp.example are delivered and not quarantined.

The contacts can be checked with the Workspace API:

```bash
curl -s https://api.nimbus.omnicorp.example/workspace \
  -H "Authorization: Bearer <api-key>"
# {"id": "ws_8Hq2LmR4", "name": "Example Logistics",
#  "security_contacts": ["secops@examplelogistics.example", "dpo@examplelogistics.example"], ...}
```

### What the CSM does

When an incident notice is issued for one of their clients, the CSM:

1. Confirms within the same business day that the client's contacts received it, and resends it to any named contact who didn't.
2. Shares only what the notice and its updates say. Questions about cause, scope or regulatory impact go to the incident lead named in the notice, never answered from memory or guesswork.
3. Logs every client contact on the account record with the incident reference.
4. Helps the client with the actions in the notice, for example by pointing them to [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md) for their own investigation.
5. Books a follow-up call when the final report is issued.

## Shared responsibilities

| Stage | OmniCorp | Client |
|---|---|---|
| Detection | Monitors the platform and investigates | Reports anything suspicious in their workspace to OmniCorp support |
| Containment | Contains and fixes the platform side | Carries out the client actions in the notice |
| Notification | Notifies the client within 72 hours of confirming a personal-data breach | Notifies the supervisory authority and affected people where the law requires it |
| Contacts | Sends notices to Security contacts and Admins | Keeps those contacts current |
| Records | Issues updates and a final report | Keeps them with their own incident records |

## Evidence for auditors

A client can show their auditor the incident response commitments in their contract and DPA (see [GDPR and Data Processing](nimbus-security-gdpr.md)), the incident response controls in OmniCorp's SOC 2 Type II report, and a screenshot of Settings > Workspace showing current Security contacts. For any real incident, the notice, its updates and the final report, all carrying the same `SI-` reference, are the record the auditor will ask for.
