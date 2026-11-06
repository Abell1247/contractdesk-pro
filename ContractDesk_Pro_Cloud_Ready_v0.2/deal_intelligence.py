"""Document-type-aware, evidence-first deal intelligence for fictional portfolio use.

Pure deterministic helpers. Classifications and warnings are triage aids, not legal advice.
"""
from __future__ import annotations
from collections import Counter
import re
from engine import TERMS, normalized, parse_number_days, review_against_playbook

# The scope describes WHERE to look, not a legal requirement to include every clause.
ALL = frozenset(TERMS)
REVIEW_FIELDS = {
    "MSA": frozenset({"Agreement Type", "Parties", "Effective Date", "Contract Term", "Auto-Renewal",
        "Renewal Notice", "Fees / Pricing", "Payment Terms", "Limitation of Liability",
        "Indemnification", "Confidentiality", "Data Processing / DPA", "Data Security",
        "Breach Notice", "Termination", "Governing Law", "Intellectual Property", "SLA / Uptime", "Assignment"}),
    "DPA": frozenset({"Agreement Type", "Parties", "Confidentiality", "Data Processing / DPA",
        "Data Security", "Breach Notice", "Subprocessors", "Data Residency", "Termination"}),
    "Order Form": frozenset({"Agreement Type", "Parties", "Effective Date", "Contract Term",
        "Fees / Pricing", "Payment Terms", "Auto-Renewal", "Renewal Notice", "SLA / Uptime"}),
    "NDA": frozenset({"Agreement Type", "Parties", "Effective Date", "Contract Term",
        "Confidentiality", "Termination", "Governing Law"}),
    "SOW": frozenset({"Agreement Type", "Parties", "Effective Date", "Contract Term",
        "Fees / Pricing", "Payment Terms", "Termination", "Intellectual Property", "SLA / Uptime"}),
    "Unknown": ALL,
}
# These are *verification prompts*, never a claim that a clause is legally mandatory.
VERIFY_IF_UNLOCATED = {
    "MSA": frozenset({"Limitation of Liability", "Indemnification", "Termination", "Data Processing / DPA"}),
    "DPA": frozenset({"Data Processing / DPA", "Data Security", "Breach Notice", "Subprocessors"}),
    "Order Form": frozenset({"Fees / Pricing", "Contract Term"}),
    "NDA": frozenset({"Confidentiality"}),
    "SOW": frozenset({"Fees / Pricing", "Contract Term"}),
    "Unknown": frozenset({"Limitation of Liability", "Indemnification", "Termination", "Data Processing / DPA"}),
}
HEADINGS = [
    ("DPA", r"^\s*(?:\d+[.)]\s*)?(?:DATA PROCESSING ADDENDUM|DATA PROCESSING AGREEMENT)\b"),
    ("MSA", r"^\s*(?:\d+[.)]\s*)?MASTER (?:SERVICES|SUBSCRIPTION|SERVICE) AGREEMENT\b"),
    ("Order Form", r"^\s*(?:\d+[.)]\s*)?(?:ORDER FORM|SUBSCRIPTION ORDER)\b"),
    ("NDA", r"^\s*(?:\d+[.)]\s*)?(?:MUTUAL )?(?:NON[- ]DISCLOSURE|CONFIDENTIALITY) AGREEMENT\b"),
    ("SOW", r"^\s*(?:\d+[.)]\s*)?STATEMENT OF WORK\b"),
]
NAME_HINTS = [("DPA",r"(?:^|[_ .-])dpa(?:[_ .-]|$)"),("MSA",r"(?:^|[_ .-])msa(?:[_ .-]|$)"),
              ("Order Form",r"order[_ .-]?form"),("NDA",r"(?:^|[_ .-])nda(?:[_ .-]|$)"),
              ("SOW",r"(?:^|[_ .-])sow(?:[_ .-]|$)")]


def classify_document(doc:dict)->dict:
    """Heading takes precedence over references to other agreements in the body."""
    beginning = "\n".join(p.get("text", "") for p in doc.get("pages", []))[:5500]
    for label, pattern in HEADINGS:
        if re.search(pattern, beginning[:1400], re.I | re.M):
            return {"type": label, "basis": "Document heading", "confidence": "heading match"}
    name = doc.get("name", "")
    for label, pattern in NAME_HINTS:
        if re.search(pattern, name, re.I):
            return {"type": label, "basis": "Filename hint only", "confidence": "unverified"}
    return {"type": "Unknown", "basis": "No supported document heading located", "confidence": "unverified"}


def applicable_fields(doc_type:str)->frozenset:
    return REVIEW_FIELDS.get(doc_type, ALL)


def required_checks(doc_type:str)->frozenset:
    return VERIFY_IF_UNLOCATED.get(doc_type, VERIFY_IF_UNLOCATED["Unknown"])


def policy_flags(findings:list[dict], playbook:dict, doc_type:str)->list[dict]:
    """Apply baseline thresholds only to fields relevant for the classified document."""
    permitted=applicable_fields(doc_type)
    return [f for f in review_against_playbook(findings,playbook) if f.get("field") in permitted]


def term_highlights(findings:list[dict], doc_type:str)->list[dict]:
    """Show conservative numeric indicators linked to exact extracted evidence.

    No date or legal-meaning inference, and no claims about what a clause permits.
    """
    by_field={f.get("field"):f for f in findings}
    results=[]
    for field,label,unit in (("Payment Terms","Payment window","days"),
                            ("Renewal Notice","Nonrenewal notice","days"),
                            ("Breach Notice","Incident notice","hours")):
        if field not in applicable_fields(doc_type):continue
        f=by_field.get(field,{})
        if not f.get('source_id') or not f.get('evidence'): continue
        passage=normalized(f.get('evidence',''))
        if field=="Payment Terms":
            match=re.search(r"\bnet\s*(\d{1,3})\b",passage)
            value=int(match.group(1)) if match else None
        elif field=="Breach Notice":
            match=re.search(r"\b(\d{1,3})(?:\s*\))?\s*hours?\b",passage)
            value=int(match.group(1)) if match else None
        else:
            # Prefer a number adjacent to a notice/renewal expression, not unrelated durations.
            match=re.search(r"(?:non[- ]renewal|notice)[^.;]{0,130}?(\d{1,3})(?:\s*\))?\s*days?\b",passage)
            value=int(match.group(1)) if match else None
        if value is not None:
            results.append({"label":label,"value":value,"unit":unit,
                            "source_id":f['source_id'],"quote":f['evidence']})
    return results


def package_summary(documents:dict, metadata:dict, deal_name:str)->dict:
    """Group only by human-entered deal label; never infer parties as a verified match."""
    selected=[(did,d) for did,d in documents.items() if metadata.get(did,{}).get('deal','').strip()==deal_name.strip()]
    types={did: classify_document(d)['type'] for did,d in selected}
    counts=Counter(types.values())
    notes=[]
    if counts.get('MSA') and not counts.get('DPA'):
        notes.append('No DPA registered under this deal label; determine whether one is required or incorporated elsewhere.')
    if counts.get('DPA') and counts.get('MSA'):
        notes.append('Both an MSA and DPA are registered. Verify their signatures, incorporation, precedence, and consistent definitions; upload alone proves none of these.')
    if counts.get('MSA',0)>1:
        notes.append('Multiple MSAs present. Confirm which version controls; these may be drafts, not executed documents.')
    return {"deal":deal_name,"documents":len(selected),"types":dict(counts),
            "document_ids":[did for did,_ in selected],"notes":notes}
