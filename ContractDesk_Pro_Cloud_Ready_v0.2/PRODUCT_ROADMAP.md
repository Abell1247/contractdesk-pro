# ContractDesk Pro — product and commercialization blueprint

## Product thesis

Do not try to be a generic lawyer replacement. Compete on **document-grounded deal operations**: intake-to-signature visibility, agreement package completeness, clear negotiation positions, and reliable routing for small-to-midmarket software companies—potentially focusing first on **education technology procurement**, where contracts may involve institutional privacy/security terms, DPAs, accessibility documentation, procurement forms, and pricing approvals.

**Proposed position:** "The deal-desk operating system that helps a small commercial team move from agreement intake to accountable human sign-off with AI-assisted analysis and auditable evidence."

## Product maturity and scope

| Level | What it requires | State |
|---|---|---|
| 0: Evidence-first prototype | Document parsing, structured extraction, sample rules, evidence, editable state and comparisons | Partial implementation in v0.2 |
| 1: Credible portfolio | Workbench UX, tested fixture cases, realistic handoffs, comprehensive safe demo | Partial implementation in v0.2 |
| 2: Team pilot | User auth, permissions, secure storage, collaboration, legally approved playbooks, practical evals, reviewer training | Not implemented |
| 3: Production SaaS | Tenant isolation, security assessment, logging, queue, uptime, incident response, backup, legal terms, DPA, support | Not implemented |
| 4: Competitive product | Clause library, precedent memory, native tracked-change redlining, exception routing, CRM/e-sign, document obligations, domain specialization | Not implemented |
| 5: Advanced agentic suite | Policy-scoped agents, approvals gateway, MCP tool service, autonomous queue operations with limits and rollback | Not implemented |

## Agent design (future concept, not current functionality)

`Inbound email / CRM / upload → intake agent → parser/OCR → clause extractor → grounded retrieval → playbook evaluator → negotiation drafting assistant → approver gateway → counterparty/e-sign workflow → signed obligations → monitoring & retrospectives`

- **Intake agent**: classifies agreement; creates deal; links MSA/DPA/order form/exhibits; checks missing attachments. Allowed to read/write drafts, not send external messages.
- **Review agent**: extracts exact source quotes, cross-references policies and relevant precedents, marks uncertainty and conflict. No legal judgments outside approved boundaries.
- **Negotiation agent**: prepares alternative clause language using **approved legal wording**, not improvised legal standards. Word tracked changes; draft for counsel.
- **Approval router**: deterministically checks authority, value, liability/indemnity thresholds, privacy/security positions; routes to Legal/Finance/Security/leadership. The model **never** grants approval.
- **Comms agent**: drafts clarifying questions, deal handoffs and status notes. Human approves any external send.
- **Repository/obligations agent**: after human-confirmed execution, extracts and verifies renewal notices, fees, dates, data retention/return and obligations.
- **Audit & evaluation service**: logs tool calls, model version, prompt template, policy version, user identity, human decision, and reversal. Evaluate hallucinations, omissions and prompt-injection resilience.

## Engineering architecture to graduate beyond prototype

1. **Frontend:** Streamlit for an internal dashboard or proof of concept. For wide external deployment, consider a dedicated web interface with stable API boundaries.
2. **API:** FastAPI or an equivalent service with authenticated request validation and account/org boundaries.
3. **Storage:** encrypted object storage for original/derived documents; PostgreSQL for contracts, versions, playbooks, approval decisions, users/tenants and obligations; optionally pgvector for embeddings.
4. **Document processing:** isolated workers for parsing, OCR, antivirus checks, tracked changes, tables, exhibits, and source map construction.
5. **Background jobs:** durable queue, retry/idempotency, dead letter queues, latency monitoring and cost budgets. Never run long external jobs in the UI server request path.
6. **AI orchestration:** small, explicit tool set; schema-constrained extraction; retrieval with excerpt/page IDs; model-free deterministic policies where possible; prompt-injection filters, no arbitrary network actions.
7. **Human decision gateway:** role/authority policies; two-person review for high-risk exceptions; tenant-specific legal playbooks; immutable-equivalent audit retention where appropriate.
8. **Integrations:** Outlook/Gmail, Salesforce/HubSpot, Word tracked changes, Docusign/Adobe Sign, Slack/Teams, MCP read-only query tools with auth.
9. **Security:** SSO/SAML/OIDC, RBAC and least privilege, tenant isolation and authorization tests, KMS-managed encryption, key rotation, secrets, retention/deletion controls, backup restore exercises, vulnerability scans, incident response, approved data-processing terms and independent security assessment.
10. **Operations:** per-tenant cost budgets, request tracing, queue lag, latency, error alerts, model/version rollback, human override mechanisms.

## What to measure (not fabricated claims)

**Quality**: clause-level precision/recall by agreement type; source-citation validity; misses on liability, privacy, fees and renewals; false-positive escalations; human corrections per 100 clauses; redline approval rate *after legal review*; regression on different formats.

**Workflow**: intake→first-pass median minutes; open exceptions; stage aging by owner; signed deal cycle time; percentage of deals missing required exhibits; renewals missed; rework; close-rate under approved rules; actual dollars in model + reviewer costs.

**Security**: blocked unauthorized access, prompt-injection test success, activity audit completeness, deletion verification, restore success, dependency vulnerabilities and incident recovery.

## Competitive reality (November 2026)

Established products already provide AI playbooks, redlining, precedent retrieval, contract repositories, and approval routing. See vendor descriptions: Ironclad https://support.ironcladapp.com/hc/en-us/articles/12275685560215-Ironclad-AI-Playbooks-Overview , Juro https://juro.com/ai-contract-review , LegalOn https://www.legalontech.com/ai-contract-review-software , Luminance https://www.luminance.com/platform/product/negotiation . **The prototype does not currently match these tools in security, legal expertise, integrations or model evaluation.** A realistic wedge is smaller teams and a targeted workflow, not generic automated lawyering.

## Non-negotiable product principles

- An LLM can suggest a concern; only licensed counsel/authorized company reviewers can make legal or company-policy decisions.
- "No flag" never means "compliant". Review coverage and incompleteness must be visible.
- Any final external email, approval, redline, or signature requires a scoped human authorization step unless a specific, legally approved low-risk policy expressly permits otherwise.
- Public demos use synthetic data. Real client data requires written authorization and a threat-reviewed environment.
- Benchmarks and customer evidence must be measured and presented honestly; never imply actual user adoption based on a synthetic portfolio demo.
