import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from engine import parse_document, local_extract, review_against_playbook
from review_workbench import build_review_matrix, operational_score, compare_versions, create_review_packet, new_event, event_csv, metrics_snapshot
from ai_backend import validate_issue_spots

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'sample_playbook.json').read_text())

def doc(name):
    p=ROOT/'sample_contracts'/name
    return parse_document(p.name,p.read_bytes())

def test_example_policy_routes_correct_clauses():
    d=doc('FICTIONAL_Northstar_MSA.txt')
    fs=local_extract(d)
    flags=review_against_playbook(fs,POLICY)
    names={f['field'] for f in flags}
    assert {'Payment Terms','Renewal Notice','Breach Notice','Data Processing / DPA'} <= names
    assert all(f['decision']=='Needs human review' for f in flags)
    matrix=build_review_matrix(d,fs,POLICY)
    mp={r['Clause']:r for r in matrix}
    assert mp['Payment Terms']['Attention']=='Review needed'
    assert mp['Breach Notice']['Attention']=='High attention'
    assert mp['Governing Law']['Attention']=='Evidence located'
    assert mp['Indemnification']['Attention']=='Evidence located'
    assert operational_score(matrix)['high']>=1

def test_revision_compares_real_changes_and_no_risk_clearance():
    orig=doc('FICTIONAL_Northstar_MSA.txt')
    latest=doc('FICTIONAL_Northstar_MSA_Revised.txt')
    delta=compare_versions(orig,latest)
    assert not delta['same_content']
    assert '+3. FEES AND PAYMENT.' in delta['diff']
    assert '-3. FEES AND PAYMENT.' in delta['diff']
    assert 'Payment Terms' in delta['potentially_affected_fields']
    newterms=local_extract(latest)
    flags=review_against_playbook(newterms,POLICY)
    assert not any(f['field']=='Payment Terms' for f in flags)
    assert not any(f['decision']=='Approved' for f in flags)

def test_review_packet_has_source_ids():
    d=doc('FICTIONAL_Northstar_MSA.txt');fs=local_extract(d)
    packet=create_review_packet(d,fs,POLICY,{'deal':'Fictional training','owner':'Reviewer'})
    assert 'Net 75' in packet
    assert d['doc_id'] in packet
    assert 'Pending authorized human reviewer' in packet

def test_unverified_ai_memoranda_are_excluded():
    d=doc('FICTIONAL_Northstar_MSA.txt')
    c=d['chunks'][0]
    fake={'clause':'Payment Terms','concern':'AI invented a clause', 'business_impact':'', 'reviewer':'Legal',
          'draft_negotiation_position':'','source_id':c['source_id'],'evidence':'THIS IS NOT IN THE AGREEMENT'}
    assert validate_issue_spots([fake],[c])==[]
    true={**fake,'evidence':'Invoices are due Net 75 from receipt.'}
    assert len(validate_issue_spots([true],[c]))==1

def test_event_metrics_from_observed_events_only():
    event=new_event('Sample loaded','abc','fake contract')
    met=metrics_snapshot([event],{'abc':{'name':'fake'}},{},{})
    assert met['intake_events']==1 and met['review_runs']==0 and met['review_coverage_pct']==0
    assert 'Sample loaded' in event_csv([event])

def test_fictional_fixture_suite_is_reproducible_and_labels_scope():
    from evaluation import run_fixture_evaluation
    result=run_fixture_evaluation()
    assert result['fixture_count']==3
    assert result['evidence_fixture_pass_pct']==100.0
    assert result['policy_fixture_recall_pct']==100.0
    assert result['unexpected_policy_flag_count']==0
    assert 'NOT performance on real contracts' in result['caution']
