# ContractDesk Pro v0.3 — Guided deal review

## Shipped in this update

- **Document-aware classification:** MSA, DPA, NDA, SOW and order-form heading recognition, with explicit fallback to a low-confidence filename hint or unknown.
- **Document-appropriate review:** The DPA review queue no longer treats every MSA-only commercial clause as a missing DPA clause. Optional, unlocated provisions are differentiated from first-pass verification prompts.
- **Explicit agreement packages:** Group files by the human-entered deal label and report whether MSA/DPA records coexist. Presence alone never establishes execution, incorporation or legal consistency.
- **Source-linked numeric indicators:** Payment windows, nonrenewal notice and incident notice periods are extracted conservatively from cited passages when patterns match.
- **Four-stage fictional deal walkthrough:** Intake, offline policy triage, draft comparison and downloadable human-review handoff—no API key required.
- **Review workbench redesign:** Priority finding cards, review owners, evidence expanders, scoped clause matrix and structured indicators.
- **Metrics wording correction:** “Documents with extraction” replaces a potentially misleading broad “review coverage” label.

## Verify before considering a release

Run `python -m pytest -q` in the application folder (install `requirements-dev.txt` if needed), then `python -m streamlit run app.py`. Test the 4-stage guided demo, documents table, DPA review, source expanders, compare drafts and JSON export. Streamlit is unavailable in the automated build environment, so GUI testing must still be done on a machine with Streamlit installed.

## Explicitly not included

Legal advice/approval, actual lawyer-grade reasoning, generative negotiation without a configured model, authenticated access, durable storage, OCR, native tracked-changes redlining, multi-tenant controls, private commercial use, or validation on real contracts. Fictional playbook thresholds are illustrative and **not** a legal standard or a policy approved by any outside organization.

Deploy through a reviewed pull request. Do not merge into `main` until local UI validation is complete; the existing Streamlit URL will update automatically after merging.
