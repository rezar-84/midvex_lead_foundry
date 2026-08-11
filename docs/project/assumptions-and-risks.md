---
status: draft
owner: product-manager
last-reviewed: 2026-08-11
---

# Assumptions, unknowns & risks — Midvex Lead Foundry

## Open assumptions

| # | Assumption | Why needed | What breaks if wrong | Who can confirm | Asked? | Since |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | The pilot uses one personal Gmail account containing company mail imported over approximately nine years. | Defines the first source connector. | OAuth, volume and date-reconciliation design changes. | requester | yes; reported | 2026-08-11 |
| A2 | Dokploy can inject secrets and run the declared containers. | Defines deployment shape. | Deployment and secret controls must change. | infrastructure owner | partially | 2026-08-11 |
| A3 | Turkish and English cover the material pilot archive. | Defines evaluation/localisation scope. | Extraction and review quality are incomplete. | archive owner | yes; reported | 2026-08-11 |

## Unknowns

| # | Question | Blocks | How we would find out | Owner |
| --- | --- | --- | --- | --- |
| U1 | Who is the accountable human and who are the two Tier 1 approvers? | merge/release | Record names in charter. | product-manager |
| U2 | Which laws, notices, contracts and retention rules apply to current/former staff and correspondents? | real mailbox connection | Qualified review of ownership, locations and purposes. | privacy-legal |
| U3 | What are the archive size, baseline candidate quality and acceptable review cost? | production budgets | Synthetic run, then authorised labelled pilot. | product-manager |
| U4 | Which AI and search processors are approved? | external AI/web processing | Processor, retention and agreement review. | privacy-legal |
| U5 | Which public domains, crawl purposes and source terms are approved per project? | real enrichment execution | Record an allowlist and qualified source-policy review. | privacy-legal |

## Unverified claims

| # | Claim | Where it appears | Evidence needed | From whom | Status |
| --- | --- | --- | --- | --- | --- |
| C1 | There are no legal limitations on processing the archive. | requester statement | Written qualified determination covering employees and third parties. | accountable human and qualified counsel | open |

## Risks

| # | Risk | Impact | Likelihood | Mitigation / early warning | Owner |
| --- | --- | --- | --- | --- | --- |
| R1 | Unauthorised or excessive processing of personal correspondence | Severe legal and personal harm | unknown | Block real data until purpose, authority, scope and retention are recorded. | privacy-legal |
| R2 | OAuth/AI credentials or message content leak through logs | Security breach | possible | Envelope encryption, secret injection, redaction tests, restricted logs. | security |
| R3 | AI-generated facts are mistaken for evidence | Misleading leads and damaged relationships | likely without controls | Evidence citations, confidence, prompt/model versions and human review. | product-manager |
| R4 | Imported/forwarded dates and identities are resolved incorrectly | False opportunity history | possible | Preserve all headers and expose ambiguity rather than overwriting source facts. | architect |
| R5 | Spam or malicious attachments reach parsers/models | Resource abuse or compromise | possible | Gmail/header/Rspamd quarantine, MIME limits, ClamAV and non-execution. | security |
| R6 | Future SaaS work assumes pilot isolation is externally verified | Cross-tenant exposure | possible | Separate MVX-014 gate and adversarial isolation review. | security |
| R7 | Message-derived URLs cause SSRF or uncontrolled crawling | Infrastructure compromise, excessive collection or cost | possible | Deny non-public addresses, require allowlists/budgets, cap redirects/bytes/depth and disable network execution by default. | security |

## Accepted risks

| # | Risk | Why accepted | Accepted by | Review on |
| --- | --- | --- | --- | --- |

## Resolved

| # | Was | Resolution | Date | What changed as a result |
| --- | --- | --- | --- | --- |
