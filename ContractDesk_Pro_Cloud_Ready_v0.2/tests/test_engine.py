import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import parse_document, local_extract, review_against_playbook, rank_chunks, validate_ai_findings, TERMS
import json

ROOT=Path(__file__).resolve().parents[1]
PLAYBOOK=json.loads((ROOT/"sample_playbook.json").read_text())

def sample():
 p=ROOT/"sample_contracts/FICTIONAL_Northstar_MSA.txt"
 return parse_document(p.name,p.read_bytes())

def test_sample_contract_parsing_and_local_extraction():
 doc=sample()
 assert doc["chars"]>1000
 assert len(doc["chunks"])>=1
 rows={r["field"]:r for r in local_extract(doc)}
 assert len(rows)==len(TERMS)
 assert "Net 75" in rows["Payment Terms"]["evidence"]
 assert rows["Auto-Renewal"]["source_id"]
 assert "Colorado" in rows["Governing Law"]["evidence"]

def test_review_thresholds_raise_three_real_issues():
 doc=sample();rows=local_extract(doc)
 flags=review_against_playbook(rows,PLAYBOOK)
 text=" ".join(x["review_question"] for x in flags)
 assert "Net 75" in text
 assert "15 days" in text
 assert "96 hours" in text
 assert not any(x["decision"]=="Approved" for x in flags)

def test_retrieval_and_quote_guard():
 doc=sample(); chunks=rank_chunks(doc["chunks"],"Net 75 payment",limit=3)
 assert any("Net 75" in c["text"] for c in chunks)
 s=chunks[0]["source_id"]
 verified=validate_ai_findings([{"field":"Payment Terms","value":"Net 75","evidence":"THIS QUOTE IS FABRICATED","source_id":s}],chunks)
 assert verified[0]["status"]=="Unverified — check source" or next(x for x in verified if x["field"]=="Payment Terms")["status"]=="Unverified — check source"

def test_pdf_and_docx_extraction():
 import io
 from docx import Document
 from reportlab.pdfgen import canvas
 d=Document();d.add_paragraph("Payment Terms: Net 45 days. Termination requires notice.")
 b=io.BytesIO();d.save(b)
 got=parse_document("contract.docx",b.getvalue())
 assert "Net 45" in got["chunks"][0]["text"]
 b2=io.BytesIO();p=canvas.Canvas(b2);p.drawString(40,760,"Payment Terms: Net 45 days.");p.save()
 got2=parse_document("contract.pdf",b2.getvalue())
 assert "Net 45" in got2["chunks"][0]["text"]
