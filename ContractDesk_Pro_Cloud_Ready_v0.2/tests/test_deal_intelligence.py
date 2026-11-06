"""Focused regression tests for document-aware contract review and package context."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import parse_document, local_extract
from deal_intelligence import (classify_document, applicable_fields, policy_flags,
                               package_summary, term_highlights)
from review_workbench import build_review_matrix
import json

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'sample_playbook.json').read_text())


def sample(name):
    path=ROOT/'sample_contracts'/name
    return parse_document(path.name,path.read_bytes())


def test_dpa_classification_prioritizes_heading_over_msa_reference():
    doc=sample('FICTIONAL_Northstar_DPA.txt')
    result=classify_document(doc)
    assert result['type']=='DPA'
    assert result['basis']=='Document heading'
    assert 'Limitation of Liability' not in applicable_fields('DPA')
    assert 'Data Security' in applicable_fields('DPA')


def test_dpa_queue_does_not_ask_for_msa_only_commercial_clauses():
    doc=sample('FICTIONAL_Northstar_DPA.txt')
    findings=local_extract(doc)
    matrix=build_review_matrix(doc,findings,POLICY)
    fields={row['Clause'] for row in matrix}
    assert 'Indemnification' not in fields
    assert 'Limitation of Liability' not in fields
    assert 'Payment Terms' not in fields
    assert 'Subprocessors' in fields
    assert not any(f['field'] in {'Indemnification','Limitation of Liability','Payment Terms'}
                   for f in policy_flags(findings,POLICY,'DPA'))


def test_msa_still_flags_real_example_commercial_exceptions():
    doc=sample('FICTIONAL_Northstar_MSA.txt')
    flags=policy_flags(local_extract(doc),POLICY,classify_document(doc)['type'])
    fields={f['field'] for f in flags}
    assert {'Payment Terms','Renewal Notice','Breach Notice'} <= fields
    assert all(f['decision']=='Needs human review' for f in flags)


def test_package_is_explicit_and_not_an_execution_claim():
    msa=sample('FICTIONAL_Northstar_MSA.txt')
    dpa=sample('FICTIONAL_Northstar_DPA.txt')
    docs={msa['doc_id']:msa,dpa['doc_id']:dpa}
    meta={msa['doc_id']:{'deal':'Fictional deal'},dpa['doc_id']:{'deal':'Fictional deal'}}
    summary=package_summary(docs,meta,'Fictional deal')
    assert summary['documents']==2
    assert summary['types']=={'MSA':1,'DPA':1}
    assert any('Verify their signatures' in note for note in summary['notes'])
    meta[dpa['doc_id']]['deal']='Other deal'
    assert 'No DPA registered' in package_summary(docs,meta,'Fictional deal')['notes'][0]


def test_unknown_classification_is_honest():
    doc=parse_document('notes.txt',b'This memo contains a payment policy for internal discussion only.')
    assert classify_document(doc)['type']=='Unknown'
    assert classify_document(doc)['confidence']=='unverified'


def test_structured_indicators_retain_a_source_reference():
    msa=sample('FICTIONAL_Northstar_MSA.txt')
    indicators=term_highlights(local_extract(msa),'MSA')
    assert any(x['label']=='Payment window' and x['value']==75 and x['source_id'] for x in indicators)
    assert all(x['quote'] for x in indicators)
