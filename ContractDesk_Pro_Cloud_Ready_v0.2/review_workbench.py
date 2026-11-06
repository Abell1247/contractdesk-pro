"""Pure deterministic workflows for ContractDesk Pro.

No legal opinions, no network calls, no persistence; only first-pass triage.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher, unified_diff
import csv
import io
import json
import re
from typing import Any
from engine import TERMS, review_against_playbook, local_extract, normalized
from deal_intelligence import classify_document, applicable_fields, required_checks, policy_flags

PROVISION_OWNERS = {
    "Agreement Type": "Deal Desk", "Parties": "Deal Desk", "Effective Date": "Deal Desk", "Contract Term": "Deal Desk",
    "Auto-Renewal": "Legal / Deal Desk", "Renewal Notice": "Deal Desk / Legal", "Fees / Pricing": "Finance / Sales",
    "Payment Terms": "Finance", "Limitation of Liability": "Legal", "Indemnification": "Legal",
    "Confidentiality": "Legal", "Data Processing / DPA": "Privacy / Legal", "Data Security": "Security",
    "Breach Notice": "Security / Privacy / Legal", "Subprocessors": "Privacy / Security", "Data Residency": "Privacy / Security",
    "Termination": "Legal", "Governing Law": "Legal", "Intellectual Property": "Legal",
    "SLA / Uptime": "Product / Legal", "Assignment": "Legal"
}
PROVISION_PURPOSE = {
    "Payment Terms": "Compare cash-collection timing against approved payment policy.",
    "Renewal Notice": "Confirm cancellation / non-renewal deadline and any notice mechanism.",
    "Auto-Renewal": "Check whether renewal is automatic, optional, or contingent.",
    "Breach Notice": "Determine whose incident reporting clock applies, its trigger, and exceptions.",
    "Data Processing / DPA": "Check data roles, processing details, exhibit availability, and privacy approvals.",
    "Limitation of Liability": "Check cap basis, excluded claims, and any supercaps with counsel.",
    "Indemnification": "Identify indemnified claims, duties to defend, and control of defense with counsel.",
    "Termination": "Check cause, convenience, cure periods, and consequences of exit.",
    "Intellectual Property": "Determine ownership, license scope, and residual rights with counsel.",
    "Fees / Pricing": "Confirm all commercial details match the order form and approvals.",
}
SEVERITY_SORT={"High attention":0,"Review needed":1,"Evidence located":2,"Not located — optional check":3,"Not reviewed":4}


def build_review_matrix(doc:dict, findings:list[dict]|None, playbook:dict)->list[dict]:
    """Categorize issues for *review*, never auto-approve anything."""
    findings = findings or []
    by_field={r['field']:r for r in findings}
    doc_type=classify_document(doc)["type"]
    exceptions=policy_flags(findings,playbook,doc_type) if findings else []
    scope=applicable_fields(doc_type)
    must_verify=required_checks(doc_type)
    evidence_by_id={c['source_id']: c for c in doc.get('chunks',[])}
    rows=[]
    for field in TERMS:
        if field not in scope: continue
        finding=by_field.get(field,{})
        sid=finding.get('source_id','')
        related=[flag for flag in exceptions if flag.get('field')==field]
        if not findings: attention="Not reviewed"
        elif related:
            attention=("High attention" if any("privacy" in f['priority'].lower() or "security" in f['priority'].lower() for f in related)
                       else "Review needed")
        elif not sid:
            attention="Review needed" if field in must_verify else "Not located — optional check"
        else:
            attention="Evidence located"
        rows.append({
            'Clause':field,'Attention':attention,'Evidence':"Found" if sid in evidence_by_id else "Not located",
            'Document type':doc_type,'Source excerpt':str(finding.get('evidence',''))[:600],
            'Source':sid, 'Review owner':related[0]['route_to'] if related else PROVISION_OWNERS.get(field,'Deal Desk'),
            'What to verify':related[0]['review_question'] if related else PROVISION_PURPOSE.get(field,'Verify meaning, context, and any related exhibits.'),
            'Extracted detail':str(finding.get('value','Not yet extracted'))[:340],
            'Review status':finding.get('status','Not reviewed'),
        })
    rows.sort(key=lambda r:(SEVERITY_SORT[r['Attention']],r['Clause']))
    return rows


def operational_score(matrix:list[dict])->dict:
    """Deterministic queue prioritization only. Not a legal risk, compliance or probability score."""
    counts=Counter(r['Attention'] for r in matrix)
    num=sum(counts.get(k,0)*weight for k,weight in [('High attention',5),('Review needed',2)])
    return {'points':num,'high':counts.get('High attention',0),'review':counts.get('Review needed',0),
            'located':counts.get('Evidence located',0),'unreviewed':counts.get('Not reviewed',0)}


def create_review_packet(doc, findings, playbook, meta=None, notes=None)->str:
    meta=meta or {}; notes=notes or []
    matrix=build_review_matrix(doc,findings,playbook)
    doc_type=classify_document(doc)["type"]
    flags=policy_flags(findings or [],playbook,doc_type) if findings else []
    scored=operational_score(matrix)
    lines=["CONTRACTDESK — FIRST-PASS REVIEW PACK",f"Agreement: {doc['name']}",f"Document fingerprint: {doc['doc_id']}",
           f"Deal: {meta.get('deal','Unassigned')}",f"Owner: {meta.get('owner','Unassigned')}",
           f"Status: {meta.get('status','New')}",f"Classified document: {doc_type} (heuristic; verify)",
           f"Triage (not legal risk): {scored['high']} high attention / {scored['review']} review needed / {scored['located']} evidence located",
           "", "AUTOMATED LIMITATIONS",
           "No legal approval or compliance finding. 'Not located' does not establish absence. Quotations and exhibits require human verification.",
           "", "PRIORITIZED HUMAN REVIEW"]
    for r in matrix:
        if r['Attention'] in ('High attention','Review needed'):
            lines.extend([f"[{r['Attention']}] {r['Clause']} | Owner: {r['Review owner']}",
                          f"Question: {r['What to verify']}",f"Source: {r['Source'] or 'Not located'}",""])
    lines.extend(["SOURCE-BACKED FINDINGS"])
    for f in (findings or []):
        if f.get('source_id'):
            lines.extend([f"{f['field']}: {f.get('value','')}",f"Source: {f['source_id']}",
                          f"Quote: {f.get('evidence','')}",""])
    if notes:
        lines.extend(["AI NOTES — CHECK ALL CLAIMS", *[str(n) for n in notes],""])
    lines.extend(["HANDOFF","Decision: Pending authorized human reviewer", "Required: confirm applicable policy, complete agreement package and source references."])
    return "\n".join(lines)


def compare_versions(old_doc:dict,new_doc:dict, max_diff_lines=1800)->dict:
    """Text-level diff; cannot interpret Word tracked changes or reliably establish legal meaning."""
    old='\n'.join(p['text'] for p in old_doc.get('pages',[]))
    new='\n'.join(p['text'] for p in new_doc.get('pages',[]))
    old_lines=old.splitlines(); new_lines=new.splitlines()
    if len(old_lines)>7000 or len(new_lines)>7000:
        raise ValueError('Draft comparison exceeds the 7,000-line safety limit. Compare smaller parts of the agreement.')
    opcodes=SequenceMatcher(None,old_lines,new_lines,autojunk=False).get_opcodes()
    add=sum(b2-b1 for tag,a1,a2,b1,b2 in opcodes if tag in ('insert','replace'))
    rem=sum(a2-a1 for tag,a1,a2,b1,b2 in opcodes if tag in ('delete','replace'))
    ud=list(unified_diff(old_lines,new_lines,fromfile=old_doc['name'],tofile=new_doc['name'],lineterm='',n=2))
    touched=[]
    for field,patterns in TERMS.items():
        hits=[]
        for tag,a1,a2,b1,b2 in opcodes:
            if tag=='equal': continue
            snippet='\n'.join(old_lines[a1:a2]+new_lines[b1:b2])
            if any(re.search(p,snippet,re.I) for p in patterns):
                hits.append(tag)
        if hits: touched.append(field)
    return {'old':old_doc['name'],'new':new_doc['name'],'same_content':old==new,
            'lines_added_or_changed':add,'lines_removed_or_changed':rem,
            'potentially_affected_fields':touched,
            'diff':'\n'.join(ud[:max_diff_lines]),'diff_truncated':len(ud)>max_diff_lines,
            'notice':'Text-level comparisons are aids only. DOCX tracked changes, legal meaning, embedded schedules, and clause cross-references are not resolved.'}


def new_event(action:str, doc_id:str='', detail:str='', actor:str='Local operator')->dict:
    return {'timestamp_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'), 'actor':actor[:100],
            'action':action[:120], 'doc_id':doc_id[:80], 'detail':detail[:500]}


def event_csv(events:list[dict])->str:
    out=io.StringIO()
    fields=['timestamp_utc','actor','action','doc_id','detail']
    writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore')
    writer.writeheader();writer.writerows(events)
    return out.getvalue()


def metrics_snapshot(events:list[dict],docs:dict,findings:dict,meta:dict)->dict:
    """Observed session events only, not invented gains or benchmark claims."""
    c=Counter(e['action'] for e in events)
    reviewed=len(findings)
    stages=Counter(m.get('status','New') for m in meta.values())
    return {'intake_events':c.get('Document uploaded',0)+c.get('Sample loaded',0),
            'review_runs':c.get('Extraction completed',0),
            'documents':len(docs),'reviewed_documents':reviewed,
            'review_coverage_pct':round(100*reviewed/len(docs),1) if docs else 0,
            'tracked_events':len(events),'active_handoffs':sum(1 for s,n in stages.items() if 'Awaiting' in s for _ in range(n))}
