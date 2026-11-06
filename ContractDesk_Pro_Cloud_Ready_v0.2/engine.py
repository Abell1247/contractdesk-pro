"""ContractDesk Assistant: text extraction, evidence-aware search and review logic.

No network calls and no file persistence in this module.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any

from docx import Document
from pypdf import PdfReader

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_EXTRACTED_CHARS = 700_000
MAX_PAGES = 250

# Each concept has its own plain-English label. Regular expressions are recall aids,
# not legal conclusions; they intentionally err on the side of human review.
TERMS = {
    "Agreement Type": [r"master services agreement", r"data processing addendum", r"statement of work", r"order form", r"non[- ]disclosure agreement", r"service level agreement"],
    "Parties": [r"\bbetween\b", r"\bby and between\b", r"\bcustomer\b.*\bprovider\b", r"\bvendor\b.*\bcustomer\b"],
    "Effective Date": [r"effective date", r"dated as of", r"commenc(?:es|ement) on"],
    "Contract Term": [r"initial term", r"contract term", r"term of this agreement", r"term will be"],
    "Auto-Renewal": [r"automatically renew", r"automatic renewal", r"auto[- ]renew", r"renew for successive"],
    "Renewal Notice": [r"notice of non[- ]renewal", r"before the end of the (?:then[- ]current|current)", r"prior to (?:the )?expiration"],
    "Fees / Pricing": [r"subscription fees", r"total fees", r"order form", r"annual fee", r"price per"],
    "Payment Terms": [r"net\s*\d{1,3}", r"within\s+\w+\s*\(?\d{1,3}\)?\s*days?\s+(?:of|after)", r"payment is due", r"invoices? (?:are )?due"],
    "Limitation of Liability": [r"limitation of liability", r"aggregate liability", r"liability (?:shall )?not exceed", r"liability cap"],
    "Indemnification": [r"indemnif", r"defend and hold harmless"],
    "Confidentiality": [r"confidential information", r"confidentiality"],
    "Data Processing / DPA": [r"data processing addendum", r"data processing agreement", r"personal data", r"controller and processor"],
    "Data Security": [r"information security", r"technical and organizational measures", r"encryption", r"security controls"],
    "Breach Notice": [r"security incident", r"data breach", r"breach notification", r"notify.*(?:hours|days).*breach"],
    "Subprocessors": [r"sub[- ]processor", r"subprocessor"],
    "Data Residency": [r"data residency", r"data location", r"stored in", r"cross[- ]border transfer"],
    "Termination": [r"termination for cause", r"terminate (?:this )?agreement", r"material breach", r"termination for convenience"],
    "Governing Law": [r"governing law", r"laws of the state", r"jurisdiction and venue"],
    "Intellectual Property": [r"intellectual property", r"ownership of", r"all right, title and interest", r"license grant"],
    "SLA / Uptime": [r"service level", r"uptime", r"availability commitment", r"service credits"],
    "Assignment": [r"assignment", r"may not assign", r"assign this agreement"],
}

KEYWORDS = {
    "term": "term duration month year start expiration",
    "renewal": "automatically renew nonrenewal cancel expiration notice",
    "payment": "payment invoice net fees price discount",
    "liability": "liability limitation cap damages exclusions",
    "privacy": "data personal breach incident dpa subprocessor security",
    "termination": "termination breach cure convenience notice",
}

@dataclass
class ExtractedDocument:
    name: str
    doc_id: str
    pages: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    chars: int
    warnings: List[str]

    def to_dict(self):
        return {"name": self.name, "doc_id": self.doc_id, "pages": self.pages,
                "chunks": self.chunks, "chars": self.chars, "warnings": self.warnings}


def parse_document(name: str, content: bytes) -> Dict[str, Any]:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("File is larger than the 15 MB app limit.")
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    pages = []
    warnings = []
    if ext == "pdf":
        if not content.startswith(b"%PDF"):
            raise ValueError("The selected file is not a valid PDF header.")
        try:
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported. Use an authorized unlocked copy.")
            if len(reader.pages) > MAX_PAGES:
                raise ValueError(f"PDF exceeds the {MAX_PAGES}-page limit.")
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text(extraction_mode="layout") or ""
                pages.append({"page": i, "text": clean_text(text)})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not read PDF: {str(exc)[:200]}") from exc
        if sum(len(p["text"]) for p in pages) < 60:
            warnings.append("Almost no selectable text was found. This may be a scan: OCR is not included in this version.")
    elif ext == "docx":
        try:
            d = Document(io.BytesIO(content))
            paragraphs = [p.text.strip() for p in d.paragraphs if p.text.strip()]
            for t in d.tables:
                for row in t.rows:
                    paragraphs.append(" | ".join(c.text.strip().replace("\n", " ") for c in row.cells))
            pages = [{"page": 1, "text": clean_text("\n".join(paragraphs))}]
            warnings.append("DOCX has no reliable page numbers here; source references use section 1 and excerpt IDs.")
        except Exception as exc:
            raise ValueError(f"Could not read DOCX: {str(exc)[:200]}") from exc
    elif ext == "txt":
        pages = [{"page": 1, "text": clean_text(content.decode("utf-8-sig", errors="replace"))}]
    else:
        raise ValueError("Accepted formats: .pdf, .docx, .txt")
    char_count = sum(len(p["text"]) for p in pages)
    if char_count > MAX_EXTRACTED_CHARS:
        warnings.append("Document text was truncated at the app's size limit; do not treat extraction as complete.")
        remaining = MAX_EXTRACTED_CHARS
        limited = []
        for p in pages:
            if remaining <= 0: break
            limited.append({"page": p["page"], "text": p["text"][:remaining]})
            remaining -= len(limited[-1]["text"])
        pages = limited
    doc_id = hashlib.sha256(content).hexdigest()[:12]
    chunks = make_chunks(pages, doc_id)
    if not chunks:
        warnings.append("No searchable contract text extracted.")
    return ExtractedDocument(name, doc_id, pages, chunks, char_count, warnings).to_dict()


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def make_chunks(pages, doc_id, size=1650, overlap=160):
    result=[]
    for page in pages:
        text=page["text"]
        if not text: continue
        start = 0
        idx = 1
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                split = text.rfind("\n", start+int(size*.7), end)
                if split != -1: end = split+1
            if end <= start: end = min(len(text),start+size)
            part = text[start:end].strip()
            if part:
                result.append({"source_id": f"{doc_id}:p{page['page']}:c{idx}","page": page["page"], "text": part})
                idx += 1
            if end == len(text): break
            start = max(start+1,end-overlap)
    return result


def excerpt_around(text: str, match: re.Match, width=460):
    """Keep wrapped PDF lines together; evidence must remain an exact source substring."""
    start=max(0, match.start()-70)
    before=text.rfind("\n\n", max(0, start-90), match.start())
    if before!=-1: start=before+2
    elif (line:=text.rfind("\n", max(0,start-70),match.start()))!=-1:
        start=line+1
    end=min(len(text), match.end()+width-70)
    # End at the next paragraph break, not a single PDF line wrap.
    para_end=text.find("\n\n",match.end(),min(len(text),end+130))
    if para_end!=-1: end=min(end,para_end)
    return text[start:end].strip()[:width]


def local_extract(doc):
    """Non-AI baseline: literal keyword match + source evidence (not normalized legal interpretation)."""
    rows=[]
    for field, patterns in TERMS.items():
        found=None
        for chunk in doc["chunks"]:
            for pattern in patterns:
                m=re.search(pattern,chunk["text"],re.I|re.S)
                if m:
                    ev=excerpt_around(chunk["text"],m)
                    found={"field":field,"value":ev,"evidence":ev,"source_id":chunk["source_id"],
                           "status":"Found — verify wording", "method":"literal search"}
                    break
            if found: break
        rows.append(found or {"field":field,"value":"Not found","evidence":"","source_id":"",
                               "status":"Not found (not proof of absence)","method":"literal search"})
    return rows


def word_tokens(text: str):
    return re.findall(r"[a-z0-9]{3,}",text.lower())


def rank_chunks(chunks, query, limit=7, max_chars=17000):
    """Local retrieval with lexical relevance and phrase matches. No index files or embeddings."""
    query = (query or "").strip()
    tokens = Counter(word_tokens(query))
    ranked=[]
    for c in chunks:
        ct = Counter(word_tokens(c["text"]))
        score = sum(min(3, ct[t])* (1.0+0.4*len(t)/8) for t in tokens)
        if query and query.lower() in c["text"].lower(): score+=10
        # Weight exact long terms over common words.
        score += sum(0.5 for t in tokens if len(t)>7 and t in ct)
        ranked.append((score,c))
    ranked.sort(key=lambda x:x[0],reverse=True)
    selected = [c for score,c in ranked if score>0][:limit]
    if not selected: selected=[c for _,c in ranked[:min(limit,3)]]
    out=[];total=0
    for c in selected:
        if total+len(c["text"])>max_chars: break
        out.append(c)
        total+=len(c["text"])
    return out


def make_extraction_context(doc, max_chars=29000):
    """Gather direct evidence by category + first-page context; incomplete coverage is shown in UI."""
    selected={}
    for c in doc["chunks"][:2]: selected[c["source_id"]]=c
    for field, patterns in TERMS.items():
        hits=[]
        for c in doc["chunks"]:
            if any(re.search(p,c["text"],re.I) for p in patterns):
                hits.append(c)
        for c in hits[:2]: selected[c["source_id"]]=c
    result=[]; n=0
    for c in selected.values():
        if n+len(c["text"])>max_chars: break
        result.append(c);n+=len(c["text"])
    return result


def normalized(s):
    return re.sub(r"\s+"," ",s or "").strip().lower()


def validate_ai_findings(raw_rows, context_chunks):
    context={c["source_id"]:c["text"] for c in context_chunks}
    allowed=set(TERMS)
    by_field={}
    for r in raw_rows or []:
        if not isinstance(r,dict) or r.get("field") not in allowed: continue
        sid=r.get("source_id") or ""
        quote=(r.get("evidence") or "").strip()
        value=(r.get("value") or "").strip()
        grounded=bool(sid in context and quote and normalized(quote) in normalized(context[sid]))
        by_field[r["field"]] = {
            "field":r["field"],
            "value":value if value else "Not found",
            "evidence":quote if grounded else "",
            "source_id":sid if grounded else "",
            "status":"Source quote verified" if grounded else ("Not found (not proof of absence)" if not value else "Unverified — check source"),
            "method":"AI (quoted evidence checked)"
        }
    return [by_field.get(field,{"field":field,"value":"Not found","evidence":"","source_id":"",
                                  "status":"Not found (not proof of absence)","method":"AI"}) for field in TERMS]


def parse_number_days(text):
    t=normalized(text)
    m=re.search(r"\bnet\s*(\d{1,3})\b",t)
    if m: return int(m.group(1))
    m=re.search(r"(?<!\d)(?:\(\s*)?(\d{1,3})(?:\s*\))?\s*days?\b",t)
    if m: return int(m.group(1))
    return None


def review_against_playbook(findings, playbook):
    """Conservative review prompts, not approvals or legal advice."""
    rows={r["field"]:r for r in findings}
    flags=[]
    def push(priority,owner,issue,evidence,sid,field=""):
        flags.append({"field":field,"priority":priority,"route_to":owner,"review_question":issue,
                      "evidence":evidence,"source_id":sid,"decision":"Needs human review"})
    pay=rows.get("Payment Terms",{})
    paydays=parse_number_days(pay.get("value",""))
    if paydays and paydays > playbook["max_net_payment_days"]:
        push("Commercial exception","Finance / Deal Desk",f"Payment term appears Net {paydays}; example guideline is Net {playbook['max_net_payment_days']}. Confirm commercial approval.", pay.get("evidence",""),pay.get("source_id",""),"Payment Terms")
    renew=rows.get("Auto-Renewal",{})
    if "automatically" in normalized(renew.get("value","")) or "auto-renew" in normalized(renew.get("value","")):
        notice=rows.get("Renewal Notice",{})
        days=parse_number_days(notice.get("value",""))
        if days is not None and days<playbook["min_nonrenewal_notice_days"]:
            push("Commercial exception","Deal Desk / Legal",f"Non-renewal notice appears {days} days; example guideline is at least {playbook['min_nonrenewal_notice_days']} days. Confirm position.",notice.get("evidence",""),notice.get("source_id",""),"Renewal Notice")
    breach=rows.get("Breach Notice",{})
    m=re.search(r"(?<!\d)(?:\(\s*)?(\d{1,3})(?:\s*\))?\s*hours?\b", normalized(breach.get("value","")))
    if m and int(m.group(1))>playbook["max_breach_notification_hours"]:
        push("Security / privacy exception","Security / Privacy / Legal",f"Breach notice appears {m.group(1)} hours; example guideline is ≤{playbook['max_breach_notification_hours']} hours. Verify applicability and definitions.",breach.get("evidence",""),breach.get("source_id",""),"Breach Notice")
    dpa=rows.get("Data Processing / DPA",{})
    dpa_context=normalized(dpa.get("value", "") + " " + dpa.get("evidence", ""))
    if any(x in dpa_context for x in ("no dpa is attached", "separate data processing addendum", "intend to execute a separate", "dpa is not attached")):
        push("Missing attachment / privacy review", "Privacy / Legal", "A DPA appears to be referenced as separate or not attached. Verify the executed addendum and applicable terms before moving forward.", dpa.get("evidence", ""), dpa.get("source_id", ""),"Data Processing / DPA")
    critical=[("Limitation of Liability","Legal"),("Indemnification","Legal"),("Data Processing / DPA","Privacy / Legal"),("Termination","Legal")]
    for field,owner in critical:
        f=rows.get(field,{})
        if not f.get("source_id"):
            push("Check missing / unverified",owner,f"{field} not reliably located in extracted passages. Confirm whether a separate addendum or clause exists.","","",field)
    # No 'approved' status is ever generated by this function.
    return flags


def registry_row(doc, findings=None):
    d={"Document":doc["name"],"ID":doc["doc_id"],"Pages":len(doc["pages"]),"Characters":doc["chars"]}
    by_field={r["field"]:r for r in (findings or [])}
    for field in ("Agreement Type","Parties","Effective Date","Contract Term","Auto-Renewal","Renewal Notice","Payment Terms","Limitation of Liability","Data Processing / DPA"):
        val=by_field.get(field,{}).get("value","")
        d[field]=val[:145] if val else "Not reviewed"
    return d


def document_index(docs):
    return [c for d in docs for c in d.get("chunks",[])]


def source_lookup(docs):
    return {c["source_id"]:(d["name"],c) for d in docs for c in d.get("chunks",[])}
