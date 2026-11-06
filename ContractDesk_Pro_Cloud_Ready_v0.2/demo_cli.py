"""Run without Streamlit/API to prove the extraction engine works on fictional data.
Usage: python demo_cli.py
"""
from pathlib import Path
from engine import parse_document, local_extract, review_against_playbook
import json
ROOT=Path(__file__).resolve().parent
playbook=json.loads((ROOT/"sample_playbook.json").read_text())
file=ROOT/"sample_contracts"/"FICTIONAL_Northstar_MSA.pdf"
if not file.exists(): file=ROOT/"sample_contracts"/"FICTIONAL_Northstar_MSA.txt"
doc=parse_document(file.name,file.read_bytes())
findings=local_extract(doc)
print("Contract:",doc["name"])
print("Pages / sections:",len(doc["pages"]))
print("\nExtracted source-backed field examples:")
for row in findings:
    if row["field"] in ("Parties","Payment Terms","Renewal Notice","Limitation of Liability","Breach Notice"):
        print("\n",row["field"],"[",row["source_id"],"]")
        print(" ",row["value"][:250])
print("\nHuman review flags against a FICTIONAL sample playbook:")
for flag in review_against_playbook(findings,playbook):
    print("-",flag["route_to"],":",flag["review_question"])
