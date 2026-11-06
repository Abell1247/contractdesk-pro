# ContractDesk Pro v0.2 — evidence-first deal desk workbench

**Independent portfolio application. Not affiliated with BoodleBox. Not legal advice, a legal service, or a production-ready contract management platform.**

The design goal is to demonstrate **operational contract intelligence**, not merely a text-generation chatbot. The app takes text-based agreements, extracts key terms, compares a limited set of structured conditions to a **fictional sample policy**, asks for authorized human decisions, and exports source-backed review packets. Optional AI adds a source-grounded issue-spotting memo and Q&A.

## Quick start — Mac

1. Install Python 3.11 or newer. Unzip this source-only ZIP.
2. Open Terminal. Type `cd ` (with the space), drag the extracted `ContractDesk_Assistant_Pro_v0.2` directory into the Terminal window, press Return.
3. Run, one at a time:

   ```bash
   python3 -m pip install -r requirements.txt
   python3 -m streamlit run app.py
   ```

4. Visit <http://localhost:8501> if a browser doesn't automatically open.

## Windows

Open PowerShell in the extracted directory, then:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Python 3.11+ is required; install it from python.org if `py` is not found.

**No API key required** to try the offline extraction, review queue, clause evidence, comparison, or evaluation laboratory.

## 90-second scripted demonstration

1. **Overview** → **Load fictional demonstration portfolio**. Three entirely fictitious agreements appear (an original MSA, revised MSA, and separate DPA).
2. **Review workbench** → choose `FICTIONAL_Northstar_MSA.txt` → **Run first-pass extraction**. The fictional contract has *Net 75*, *15-day non-renewal*, *96-hour security incident notification*, and a *missing/elsewhere referenced DPA*. Observe routing suggestions to Finance / Legal / Privacy.
3. Expand an issue. View its exact source passage. Under **Reviewer decision log**, enter a fictional name and an explanatory next action. This action appears in the **Operations** activity trace.
4. **Compare drafts** → choose the original MSA, then `FICTIONAL_Northstar_MSA_Revised.txt` → **Compare versions**. The later fictional draft changes payment, renewal and breach notice windows. Inspect the diff.
5. **Contract copilot** → in offline mode ask about `Net 75`, renewal, or DPA. This performs passage search, **not** generative reasoning.
6. **Operations & playbook** → **Run fictional contract evaluation**. It measures extraction and rule triggers on three deliberately simple text fixtures. **These are not legal-accuracy or real-world recall results.**
7. Export a review packet, data JSON, policy JSON, activity CSV and registry CSV for inspection.

## Optional AI analysis

**Local Ollama:** Install and run Ollama with a suitable model, then choose `Ollama · local model`. AI model quality varies and may be poor on contract data. Treat all model output as draft material requiring review.

**OpenAI API:** Choose `OpenAI API · external`, supply a *personal authorized key* in the session-only password field, and explicitly confirm the content can be sent to the external service. Only then does clicking an AI action send **selected contract excerpts** for processing. API billing is separate. No key is included in this project.

You can now use **Generate AI issue-spotting memorandum** for source-cited draft concerns, business implications, and proposed discussion positions. These remain **unreviewed suggestions**. Source quotations are checked for exact presence within retrieved excerpts, which does **not** establish that the interpretation or advice is correct.

**Never upload real client, employee, privileged, or institutionally confidential agreements without authority and an approved security and data-processing process.** Even the on-device app has limited protections.

## Features that actually work

| Feature | Technical scope |
|---|---|
| Text contract import | PDF (selectable text), DOCX (flattened), TXT. Bounded size and page counts. |
| Registry & workflow | In-session cases, human-entered owner / counterparty / stage / next action. |
| Text extraction | 20+ domain concepts with literal evidence IDs. AI-assisted extraction optional. |
| Review matrix | Rules, configured thresholds, human routing, source citation; **not approval**. |
| AI review memo | Optional source-checked draft issue spots using selected excerpts; not exhaustive or authoritative. |
| Reviewer log | Human-entered per-clause decisions, owner, note, action timestamp. |
| Version comparison | Line-based, text-only unified diff and heuristic topics potentially touched. |
| Q&A | Offline source passage search or optional retrieval-grounded model response. |
| Operations | Observed session actions, queues, review coverage, reproducible fictional fixtures. |
| Exports | Review text packet, review data JSON, registry CSV, events CSV, playbook JSON, diff. |

## Known important limitations

- **No accounts or role-based permissions.** No persistent encrypted database or multi-tenant separation.
- No database durable audit; session events are editable/resettable, and page reload may clear data.
- No OCR for images or scanned PDF. No real tracked-change `.docx` redlining, Docusign, Outlook, Salesforce, MCP, or approvals API.
- AI review selects **some excerpts**, not all pages. Document parsing can omit headers, footers, image content, footnotes, and exhibit relationships. A missing finding does not establish absence.
- The literal extraction is prone to false positives and false negatives. The fictional-playbook thresholds are **not** legal standards or employer policies.
- No performance claims beyond reproducible results on three **fictional** sample files. No measured real customer productivity gain.
- No legal interpretation or legally binding advice; licensed counsel must verify legal risk, enforceability, regulatory compliance, and draft language.
- Source quotations are verified, but model interpretations can still be incorrect or overlook vital context. Documents are untrusted input; malicious text or prompt injection could affect AI output.
- Public Streamlit hosting is appropriate **only for sanitized fictional demonstrations** in this version, not for confidential multi-party work.

## Source files

- `app.py` — Streamlit interface and workflow orchestration
- `engine.py` — text extraction, pattern matching, retrieval, fictional threshold rules
- `review_workbench.py` — issue matrices, source-backed review packets, draft comparisons, session event metrics
- `ai_backend.py` — optional local/remote model calls, structured outputs, quote validation
- `evaluation.py` — reproducible tiny fictional benchmark
- `sample_contracts/` — fictional original MSA, revised MSA and DPA
- `sample_playbook.json` — fictional policy settings
- `tests/` — regression and workflow tests
- `PRODUCT_ROADMAP.md` — commercialization and agentic architecture plan

## Run code-level tests (optional)

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q tests
python3 evaluation.py
```

## Share a demo safely

For a public demo, publish these **source files** to a GitHub repository and deploy a Streamlit app, if the host permits use of this code. Do not add actual contracts, API keys, internal playbooks, real approvals, or confidential logs. This ZIP deliberately contains **no launcher scripts** because previous security scanners flagged an earlier easy-start package.

## Professional representation

This software is a **new, independently built prototype**. It is not evidence of real institutional adoption, production-level testing, or previous customer usage. Describe it as an implementation of the workflow methods you know from your work—unless and until it is actually deployed and adopted by real users.
