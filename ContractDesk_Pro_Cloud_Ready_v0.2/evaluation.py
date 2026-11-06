"""Small transparent fictional-fixture evaluation, not a real-world legal accuracy benchmark."""
from __future__ import annotations
from pathlib import Path
from time import perf_counter
import json
from engine import parse_document, local_extract, review_against_playbook

ROOT=Path(__file__).resolve().parent
FIXTURES={
 'FICTIONAL_Northstar_MSA.txt':{
     'must_find':{'Payment Terms':'Net 75','Breach Notice':'96) hours','Renewal Notice':'15) days'},
     'expected_policy_deviations':{'Payment Terms','Breach Notice','Renewal Notice','Data Processing / DPA'}},
 'FICTIONAL_Northstar_MSA_Revised.txt':{
     'must_find':{'Payment Terms':'Net 45','Breach Notice':'48) hours','Renewal Notice':'45) days'},
     'expected_policy_deviations':{'Data Processing / DPA'}},
 'FICTIONAL_Northstar_DPA.txt':{
     'must_find':{'Breach Notice':'72) hours','Data Processing / DPA':'DATA PROCESSING ADDENDUM','Subprocessors':'SUBPROCESSORS'},
     'expected_policy_deviations':set()},
}
# DPA fixture intentionally omits liability/indemnity/termination; the baseline engine
# conservatively raises 'check missing' prompts, excluded from the deviation precision sample.

def run_fixture_evaluation():
    policy=json.loads((ROOT/'sample_playbook.json').read_text('utf-8'))
    rows=[];start=perf_counter()
    for name,expected in FIXTURES.items():
        p=ROOT/'sample_contracts'/name
        t0=perf_counter();doc=parse_document(name,p.read_bytes())
        findings=local_extract(doc)
        field={r['field']:r for r in findings}
        checks=0;correct=0
        for k,needle in expected['must_find'].items():
            checks+=1
            v=field.get(k,{})
            if needle.lower() in (v.get('evidence') or '').lower() and v.get('source_id'):correct+=1
        flags=review_against_playbook(findings,policy)
        got={f['field'] for f in flags if f.get('priority')!='Check missing / unverified'}
        want=expected['expected_policy_deviations']
        rows.append({'Fictional fixture':name,'Evidence checks passed':correct,'Evidence checks':checks,
                     'Expected policy flags':len(want),'Flags found as expected':len(got & want),
                     'Unexpected policy flags':len(got-want),'Missed expected flags':len(want-got),
                     'Runtime (ms)':round(1000*(perf_counter()-t0),1)})
    total_checks=sum(x['Evidence checks'] for x in rows)
    total_correct=sum(x['Evidence checks passed'] for x in rows)
    expected_flags=sum(x['Expected policy flags'] for x in rows)
    hits=sum(x['Flags found as expected'] for x in rows)
    return {'evidence_fixture_pass_pct':round(total_correct/total_checks*100,1),
            'policy_fixture_recall_pct':round(hits/expected_flags*100,1) if expected_flags else None,
            'unexpected_policy_flag_count':sum(x['Unexpected policy flags'] for x in rows),
            'fixture_count':len(rows),'evaluated_evidence_checks':total_checks,
            'total_runtime_ms':round(1000*(perf_counter()-start),1), 'cases':rows,
            'caution':'Fictional text samples only. Numbers are NOT performance on real contracts, not legal risk accuracy, and not a claim of time savings. Results vary with hardware. Scans, DOCX redlines, and external models are not evaluated.'}

if __name__=='__main__':
    print(json.dumps(run_fixture_evaluation(),indent=2))
