---
id: nimbus-security-gdpr
title: GDPR and Data Processing
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-06-15
owner: Security & Compliance
---

Clients in the EU and UK, and many outside them, ask how Nimbus fits their GDPR obligations. The short answer is that the client is the controller of the personal data their workflows process, OmniCorp is the processor, and the terms are set out in the data processing agreement (DPA) that is part of every Nimbus contract. This note explains what OmniCorp does as processor, how a client finds and removes one person's data when a data subject request arrives, and what to send an auditor or a data protection officer.

## Scope

The note covers personal data that a Nimbus workspace holds: the workspace's own users (names, email addresses, roles, sign-in history), the data that passes through workflow runs (trigger payloads, step inputs and outputs), and the audit log. It applies to every Plan Tier and every data region.

Out of scope are the client's connected applications. A Salesforce org or a BambooHR account connected to Nimbus remains a separate system with its own processor terms between the client and that vendor; Nimbus reads and writes it on the client's instructions but doesn't become its record keeper. Where data is stored is covered in [Data Residency](nimbus-security-data-residency.md), and how long each kind of record is kept in [Data Retention and Deletion](nimbus-security-data-deletion.md).

## Controls in place

A DPA is part of every contract, and OmniCorp is the processor. The DPA commits OmniCorp to process personal data only on the client's documented instructions, which in practice means the workflows the client builds and the users the client invites.

The main commitments in the DPA, and how Nimbus meets them:

| Commitment | How it is met |
|---|---|
| Processing only on instructions | Nimbus runs only the workflows the client publishes; OmniCorp staff don't access workspace data except to resolve a support ticket the client raised |
| Confidentiality of staff | OmniCorp staff with production access are bound by confidentiality terms and need an approved, time-limited access grant |
| Security of processing | TLS 1.2 or later in transit, AES-256 at rest, and the controls tested in the SOC 2 Type II report |
| Sub-processors | A published list; clients are told of a new sub-processor 30 days before it starts processing and may object |
| International transfers | Data stays in the region chosen when the workspace was created; Standard Contractual Clauses are annexed to the DPA for any support access from outside the EEA |
| Assistance with data subject requests | Search and deletion tools in the console and API, described below |
| Breach notification | Clients are notified without undue delay, and within 72 hours, of a confirmed personal-data breach |
| Deletion at the end of the contract | Workspace deletion removes every workflow, run, connection and user once the restore window has passed |

The breach process, including who receives the notice, is described in [Security Incident Notification](nimbus-security-incident-notification.md).

## Admin settings

When a data subject asks to see or erase their data, the client's Admin collects it from three places: the user list, run history and the audit log. To handle a request:

1. Find the person as a user. In Settings > Users, search by email address, or call `GET /users?email=<address>`. Note the `usr_` id; a person who was never a workspace user won't appear here and may still appear in run data.
2. Find their data in runs. Open Runs, choose the workflows that handle personal data (for example an HR onboarding workflow), set the date range and search for the person's email address or employee number. Each matching run shows the trigger payload and step inputs and outputs. Run history is kept for 90 days on every Plan Tier, so older runs no longer hold the data.
3. Find what they did in the workspace. In Settings > Audit log, filter on the actor, or call `GET /audit-log/events?actor=<usr_id>`. Export CSV gives the client a copy to hand over.
4. Erase where asked. Delete the user under Settings > Users or with `DELETE /users/{id}`. Run history can't be edited from the console; if specific runs must go before they age out, the CSM raises a support request with the `run_` ids and OmniCorp deletes them. Then remove the person's records in the connected applications, which Nimbus doesn't do on the client's behalf.

The API calls for steps 1 and 3 look like this:

```bash
curl -s "https://api.nimbus.omnicorp.example/users?email=maria.keller@example.com" \
  -H "Authorization: Bearer <api-key>"

curl -s "https://api.nimbus.omnicorp.example/audit-log/events?actor=usr_5TzW91kD&from=2026-01-01T00:00:00Z&limit=100" \
  -H "Authorization: Bearer <api-key>"
```

Audit-log entries can't be edited or deleted, because they are the client's own evidence of who did what. When a user is deleted, their events keep the `usr_` id but the email address on each event is replaced with "deleted user", which is the pseudonymisation the DPA describes. More on export filters is in [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## Shared responsibilities

| Task | OmniCorp (processor) | Client (controller) |
|---|---|---|
| Lawful basis for processing | None | Decides it and records it |
| Record of processing activities | Keeps its processor record under Article 30(2) | Keeps its controller record, listing Nimbus as a processor |
| Data subject requests | Provides search, export and deletion tools; helps through support if asked | Receives the request, verifies identity and answers within the legal deadline |
| Minimising data in workflows | Keeps run data only for the run-history period | Maps only the fields a workflow needs and avoids special-category data where it can |
| Breach handling | Notifies the client within 72 hours of confirming a personal-data breach | Assesses it and notifies the supervisory authority and data subjects where required |
| Sub-processor changes | Gives notice of new sub-processors | Reviews the notice and objects if needed |

## Evidence for auditors

A client's data protection officer or auditor can ask the CSM for:

- the signed DPA with its annexes (security measures, sub-processor list, Standard Contractual Clauses);
- the current sub-processor list with each sub-processor's location and purpose;
- OmniCorp's SOC 2 Type II report and ISO/IEC 27001 certificate, released under NDA as described in [Compliance Reports and Certifications](nimbus-security-compliance-reports.md);
- a written description of the deletion process for a workspace at the end of a contract.

From their own workspace, the client can show audit-log exports for each data subject request they handled, with the `user.deleted` event that closes an erasure request, and the Runs search they used to locate the person's data.
