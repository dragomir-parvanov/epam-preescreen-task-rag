---
id: nimbus-security-compliance-reports
title: Compliance Reports and Certifications
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-09-14
owner: Security & Compliance
---

A client's security or procurement team usually asks for the same three things before signing or renewing: OmniCorp's SOC 2 Type II report, its ISO/IEC 27001 certificate and answers to a security questionnaire. This note explains what each document covers, how a CSM obtains them for a client under NDA, and which Nimbus settings and records the client can put in front of their own auditors alongside them.

The reports are confidential. They are never attached to a ticket, posted in a shared channel or sent to anyone who isn't covered by an NDA with OmniCorp.

## Scope

This note covers OmniCorp's third-party attestations for Nimbus and the process for releasing them to clients:

- the SOC 2 Type II report and the bridge letter that extends it;
- the ISO/IEC 27001 certificate and its Statement of Applicability;
- the penetration test executive summary;
- the standard security questionnaire answer pack and how custom questionnaires are handled.

It doesn't cover the data processing agreement, which is part of every contract and is described in [GDPR and Data Processing](nimbus-security-gdpr.md), or the technical detail of encryption, which is in [Encryption in Transit and at Rest](nimbus-security-encryption.md). Both are frequent follow-up questions once the reports have been read.

## Controls in place

OmniCorp holds a SOC 2 Type II report and an ISO/IEC 27001 certificate covering the Nimbus platform, the engineering and operations teams that run it, and OmniCorp support. Clients get them through their CSM under NDA. The documents differ in what they prove, so it helps to know which one answers which question:

| Document | Issued by | What it shows | Refreshed |
|---|---|---|---|
| SOC 2 Type II report | Independent audit firm | Design and operating effectiveness of controls over a 12-month observation period, against the Security and Confidentiality trust services criteria | Annually, covering October to September |
| Bridge letter | OmniCorp Security & Compliance | That no material change to the control environment has happened since the end of the last SOC 2 period | On request |
| ISO/IEC 27001 certificate | Accredited certification body | That OmniCorp runs a certified information security management system with Nimbus in scope | Three-year cycle with yearly surveillance audits |
| Statement of Applicability | OmniCorp Security & Compliance | Which Annex A controls apply and how each is implemented | With each certificate or surveillance audit |
| Penetration test summary | Independent testing firm | Scope, method and findings by severity of the yearly test of the console, API and SSO sign-in | Annually |

The controls tested in the SOC 2 report include role-based access for OmniCorp staff, peer-reviewed change management, encryption with TLS 1.2 or later in transit and AES-256 at rest, vulnerability management, backup and restore testing, and incident response. Exceptions noted by the auditor, if any, appear in section IV of the report together with management's response; a CSM should never summarise them for a client, but point the client's reviewer to that section.

## Admin settings

Nothing in the admin console publishes or unlocks the reports; the CSM requests them. To release a report to a client:

1. Open the client's account record in the CRM and confirm that an NDA is in force. The confidentiality clause of the master agreement counts; a lapsed evaluation NDA doesn't.
2. Raise a Security documentation request in the Security & Compliance queue, naming the documents, the recipient and the reason (new deal, renewal, client audit).
3. Security & Compliance watermarks each PDF with the client's name and the recipient's email address and sends it through a secure share link that expires after 14 days.
4. Record the delivery on the account record, so the next request from the same client can reuse the approval.

A request carries these fields:

```yaml
request_type: security_documentation
client: Example Logistics Ltd
workspace_id: ws_8Hq2LmR4
nda_reference: MSA-2025-0418, clause 12
recipient: ciso@examplelogistics.example
documents:
  - soc2_type2_report
  - bridge_letter
  - iso27001_certificate
reason: renewal security review
```

Auditors on the client side often ask to see how the client has configured their own workspace. The settings they look at most are under Settings > Security > Two-factor authentication, Settings > Security > Sessions and Settings > Security > Single sign-on, plus an export from Settings > Audit log; see [Requiring Two-Factor Authentication](nimbus-admin-requiring-two-factor.md) and [Searching and Exporting the Audit Log](nimbus-admin-exporting-the-audit-log.md).

## Shared responsibilities

The reports describe OmniCorp's side only. A client's auditor will also expect evidence of the controls the client operates in their own workspace.

| Area | OmniCorp | Client |
|---|---|---|
| Platform infrastructure and hosting | Operates, patches and monitors it; covered by the SOC 2 report | Nothing to operate |
| Encryption | TLS in transit and AES-256 at rest by default | Chooses customer-managed keys where the tier allows it |
| User access to the workspace | Provides roles, SSO, two-factor and session controls | Decides who gets which role and reviews access regularly |
| Connection credentials | Encrypts them and never shows them again after saving | Grants each connection only the third-party permissions it needs |
| Report confidentiality | Watermarks and releases reports under NDA | Keeps the reports within the people named on the request |

## Evidence for auditors

A client can show their auditor the watermarked SOC 2 Type II report with a bridge letter for any gap, the ISO/IEC 27001 certificate and Statement of Applicability, and the penetration test summary. For the client-operated controls, the usual evidence is an audit-log CSV export, a list of users and roles, and screenshots of the security settings listed above. A record of the client's own access reviews is described in [Running User Access Reviews](nimbus-security-access-reviews.md).

### Security questionnaires

Security & Compliance keeps a standard answer pack with completed CAIQ and SIG Lite questionnaires, refreshed after each SOC 2 report. A CSM can send the answer pack under the same NDA check as the reports, and should offer it before the client sends their own form. When a client insists on their own questionnaire, the CSM fills in what the knowledge base answers directly, marks the rest for Security & Compliance and attaches it to a Security documentation request; the team returns custom questionnaires within 10 business days. Questions about future certifications or roadmap commitments are always passed to Security & Compliance rather than answered by the CSM.
