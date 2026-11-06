"""ContractDesk Pro — evidence-first contract operations portfolio workbench.

Local session prototype. NOT legal advice, a certified service, or an authenticated multiuser product.
Start: python -m streamlit run app.py
"""
from __future__ import annotations
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engine import (parse_document, local_extract, review_against_playbook,
                    registry_row, rank_chunks, document_index, source_lookup)
from ai_backend import ai_extract, ai_answer, ai_issue_spot
from evaluation import run_fixture_evaluation
from deal_intelligence import classify_document, policy_flags, term_highlights, package_summary
from review_workbench import (build_review_matrix, operational_score,
                              create_review_packet, compare_versions, new_event, event_csv,
                              metrics_snapshot)

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title="ContractDesk Pro | Review Workbench",page_icon="⚖️",layout="wide",initial_sidebar_state="expanded")
st.markdown('''<style>
html,body,[class*="css"]{font-family:"DM Sans",system-ui,sans-serif}
.block-container{padding:1.65rem 2.2rem 4rem;max-width:1510px}
h1,h2,h3{letter-spacing:-.035em}
h1{font-size:2.15rem!important;font-weight:700!important}
h2{font-size:1.28rem!important}
[data-testid="stMetric"]{border:1px solid rgba(100,116,139,.22);border-radius:14px;padding:13px 15px;background:rgba(100,116,139,.045)}
[data-testid="stMetricValue"]{font-size:1.6rem}
div[data-testid="stButton"] button[kind="primary"]{background:#1457b7;border-radius:9px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:15px}
.product-kicker{color:#3b82f6;font-size:.77rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.product-sub{color:#64748b;font-size:.94rem;margin-top:-.5rem}
.product-banner{border:1px solid rgba(37,99,235,.22);border-left:4px solid #2563eb;border-radius:10px;padding:12px 16px;margin:10px 0 17px;background:rgba(37,99,235,.045)}
.small-label{color:#64748b;font-size:.83rem}
</style>''',unsafe_allow_html=True)

for key,default in [('docs',{}),('findings',{}),('review_notes',{}),('review_meta',{}),('review_decisions',{}),('chat',[]),('issue_spots',{}),('events',[]),('demo_step',0)]:
    if key not in st.session_state: st.session_state[key]=default
if 'playbook' not in st.session_state:
    st.session_state.playbook=json.loads((ROOT/'sample_playbook.json').read_text('utf-8'))
if 'playbook_editor' not in st.session_state:
    st.session_state.playbook_editor=json.dumps(st.session_state.playbook,indent=2)


def record(action,doc_id='',detail=''):
    st.session_state.events.append(new_event(action,doc_id,detail))


def labels():
    return {f"{doc['name']}  ·  {i}":i for i,doc in st.session_state.docs.items()}


def add_doc(name,raw,sample=False):
    doc=parse_document(name,raw)
    if doc['doc_id'] in st.session_state.docs: return False
    st.session_state.docs[doc['doc_id']]=doc
    st.session_state.review_meta[doc['doc_id']]={'deal':name.rsplit('.',1)[0], 'owner':'', 'status':'New',
                                               'counterparty':'', 'next_action':'', 'updated_at':datetime.now(timezone.utc).isoformat()}
    doc['type_assessment']=classify_document(doc)
    record('Sample loaded' if sample else 'Document uploaded',doc['doc_id'],name)
    return True


def provider_config():
    with st.sidebar:
        st.markdown('<div class="product-kicker">CONTRACTDESK / PRO</div>',unsafe_allow_html=True)
        st.caption('Independent portfolio build · v0.3')
        st.divider()
        nav=st.radio('WORKSPACE',["Guided demo", "Overview", "Agreements", "Review workbench", "Compare drafts", "Contract copilot", "Operations & playbook"],
                     label_visibility='collapsed')
        st.divider()
        st.subheader('AI processing')
        provider=st.selectbox('Mode',['Evidence search · offline','Ollama · local model','OpenAI API · external'],index=0)
        if provider.startswith('OpenAI'):
            model=st.text_input('Model',value='gpt-4.1-mini')
            key=st.text_input('API key · session only',type='password')
            authorization=st.checkbox('I am authorized to send selected excerpts to this API',value=False)
            st.caption('Excerpts are transmitted only when an AI action is requested. Do not use third-party confidential agreements without permission.')
            api_provider='OpenAI API'
        elif provider.startswith('Ollama'):
            model=st.text_input('Local model',value='llama3.1:8b')
            key='';authorization=True;api_provider='Ollama (local)'
            st.caption('Requires a running local Ollama service and installed model.')
        else:
            model='';key='';authorization=True;api_provider='Local search (no AI)'
            st.caption('No model or network required. Text matching is not complete legal review.')
        st.divider()
        st.caption('**Privacy:** Session memory only. No authentication, database, or cross-user controls. Publicly host fictional demonstrations only.')
        st.caption('**Scope:** First-pass contract operations. Human counsel and authorized approvers decide.')
        return nav,api_provider,model,key,authorization

nav,provider,model,api_key,remote_allowed=provider_config()
metrics=metrics_snapshot(st.session_state.events,st.session_state.docs,st.session_state.findings,st.session_state.review_meta)

st.markdown('<div class="product-kicker">CONTRACT INTELLIGENCE / DEAL OPERATIONS</div>',unsafe_allow_html=True)
st.title('ContractDesk Pro')
st.markdown('<p class="product-sub">Agreement packages  /  source-backed review  /  policy exceptions  /  documented human decisions</p>',unsafe_allow_html=True)
st.markdown('<div class="product-banner"><strong>First-pass analysis, not automated legal approval.</strong> Findings are review suggestions supported by document excerpts. Example policy thresholds are fictional. Use only documents you are authorized to process.</div>',unsafe_allow_html=True)

DEMO_DEAL='Northstar Analytics / Lakewood Community College — FICTIONAL'


def load_fictional_deal():
    for path in sorted((ROOT/'sample_contracts').glob('*.txt')):
        add_doc(path.name,path.read_bytes(),sample=True)
    for did,doc in st.session_state.docs.items():
        if doc['name'].startswith('FICTIONAL_Northstar_'):
            st.session_state.review_meta[did]['deal']=DEMO_DEAL
            st.session_state.review_meta[did]['counterparty']='Lakewood Community College (fictional)'
    st.session_state.demo_step=max(1,st.session_state.demo_step)


def demo_documents():
    return {doc['name']: (did,doc) for did,doc in st.session_state.docs.items()
            if doc['name'].startswith('FICTIONAL_Northstar_')}


if nav=='Guided demo':
    st.header('Three-minute contract review / guided experience')
    st.caption('A fictional SaaS procurement case. Runs without a model or API key. Each stage shows real deterministic analysis; no legal decisions are automated.')
    step=int(st.session_state.demo_step)
    st.progress(min(step,4)/4)
    a,b,c,d=st.columns(4)
    a.metric('01 · Intake','Ready' if step>=1 else 'Start')
    b.metric('02 · Triage','Complete' if step>=2 else 'Pending')
    c.metric('03 · Compare','Complete' if step>=3 else 'Pending')
    d.metric('04 · Handoff','Prepared' if step>=4 else 'Pending')
    if st.button('1 · Load fictional contract package',type='primary'):
        load_fictional_deal()
        st.rerun()
    if step>=1:
        docs=demo_documents()
        bundle=package_summary(st.session_state.docs,st.session_state.review_meta,DEMO_DEAL)
        st.subheader('Stage 1 · Intake and agreement package')
        st.dataframe(pd.DataFrame([{'Document':name,'Type':classify_document(doc)['type'],
                                   'Source pages':len(doc['pages'])} for name,(did,doc) in docs.items()]),
                     hide_index=True,use_container_width=True)
        for note in bundle['notes']: st.info(note)
        st.caption('A matching deal label groups files; association does not establish execution, incorporation, or precedence.')
        if st.button('2 · Run evidence-based contract triage'):
            for name,(did,doc) in docs.items():
                st.session_state.findings[did]=local_extract(doc)
                record('Extraction completed',did,'Offline fictional demo')
            st.session_state.demo_step=max(2,st.session_state.demo_step)
            st.rerun()
    if step>=2:
        docs=demo_documents()
        st.subheader('Stage 2 · Playbook exceptions and supporting evidence')
        msa=docs.get('FICTIONAL_Northstar_MSA.txt')
        dpa=docs.get('FICTIONAL_Northstar_DPA.txt')
        if msa:
            did,doc=msa; findings=st.session_state.findings.get(did,[])
            matrix=build_review_matrix(doc,findings,st.session_state.playbook)
            flags=policy_flags(findings,st.session_state.playbook,'MSA')
            k1,k2,k3=st.columns(3)
            k1.metric('MSA policy prompts',len(flags))
            k2.metric('MSA source passages',len(doc['chunks']))
            k3.metric('MSA scoped clauses',len(matrix))
            for flag in flags[:5]:
                with st.container(border=True):
                    st.markdown(f"**{flag['field']} · {flag['route_to']}**")
                    st.write(flag['review_question'])
                    if flag['source_id']:
                        st.caption(f"Source: {doc['name']} / {flag['source_id']}")
                        st.code(flag['evidence'],language=None)
                    else:
                        st.caption('Clause not confidently located — review the source manually.')
            for item in term_highlights(findings,'MSA'):
                st.caption(f"Extracted indicator: {item['label']} — {item['value']} {item['unit']} · {item['source_id']}")
        if dpa:
            did,doc=dpa; findings=st.session_state.findings.get(did,[])
            matrix=build_review_matrix(doc,findings,st.session_state.playbook)
            st.info(f"Separate DPA analysis: {len(matrix)} relevant fields checked; MSA-only commercial clauses excluded from its queue.")
        if st.button('3 · Compare original and revised MSA'):
            st.session_state.demo_step=max(3,st.session_state.demo_step)
            record('Guided demo comparison viewed')
            st.rerun()
    if step>=3:
        docs=demo_documents(); old=docs.get('FICTIONAL_Northstar_MSA.txt');new=docs.get('FICTIONAL_Northstar_MSA_Revised.txt')
        if old and new:
            result=compare_versions(old[1],new[1])
            st.subheader('Stage 3 · Negotiation change detection')
            st.markdown('**Potentially affected subjects:** '+(', '.join(result['potentially_affected_fields']) or 'No defined topic detected'))
            st.caption('Text-level differences only; no legal conclusion or Word track-changes support.')
            with st.expander('Inspect actual text-level diff',expanded=False): st.code(result['diff'],language='diff')
        if st.button('4 · Generate human-review handoff'):
            st.session_state.demo_step=max(4,st.session_state.demo_step)
            record('Guided demo reviewer packet prepared')
            st.rerun()
    if step>=4:
        docs=demo_documents(); msa=docs.get('FICTIONAL_Northstar_MSA.txt')
        if msa:
            did,doc=msa
            packet=create_review_packet(doc,st.session_state.findings.get(did,[]),st.session_state.playbook,
                                        st.session_state.review_meta.get(did,{}))
            st.subheader('Stage 4 · Reviewer handoff')
            st.success('First-pass packet prepared for authorized human review. No contract was approved or sent.')
            st.download_button('Download source-backed review packet',packet,
                               file_name='FICTIONAL_Northstar_Review_Packet.txt',mime='text/plain')
            st.caption('Next: use Review workbench to record a reviewer decision, or Agreements to edit deal ownership.')

elif nav=='Overview':
    a,b,c,d=st.columns(4)
    a.metric('Agreements in session',metrics['documents'])
    b.metric('Documents reviewed',metrics['reviewed_documents'])
    c.metric('Extraction runs',metrics['review_runs'])
    d.metric('Logged workflow actions',metrics['tracked_events'])
    left,right=st.columns([1.55,1],gap='large')
    with left:
        st.subheader('Deal pipeline')
        if st.session_state.docs:
            rows=[]
            for did,doc in st.session_state.docs.items():
                meta=st.session_state.review_meta.get(did,{})
                finding=st.session_state.findings.get(did)
                flags=policy_flags(finding,st.session_state.playbook,classify_document(doc)['type']) if finding else []
                rows.append({'Agreement':doc['name'], 'Type':classify_document(doc)['type'], 'Deal':meta.get('deal',''), 'Stage':meta.get('status','New'),
                             'Review owner':meta.get('owner','Unassigned'),
                             'Playbook review flags':len(flags) if finding else 'Not analyzed',
                             'Evidence coverage':'Extracted' if finding else 'Pending'})
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=min(380,80+len(rows)*42))
        else:
            st.info('No contracts yet. Start with the fictional test portfolio to see the full workflow.')
        if st.button('Load fictional demonstration portfolio',type='primary'):
            load_fictional_deal()
            st.success('Fictional contract package loaded; open Guided demo or Review workbench.')
    with right:
        st.subheader('Operating model')
        for step,desc in [
            ('01 · Intake','Register agreement, identify version, retain original source.'),
            ('02 · Extract','Locate key commercial, privacy, and legal provisions.'),
            ('03 · Review','Compare evidence with editable policy; flag missing or non-standard items.'),
            ('04 · Handoff','Assign accountable reviewer and capture the next action.'),
            ('05 · Improve','Track actual workflow actions and compare versions.')]:
            st.markdown(f'**{step}**  \n{desc}')
        st.caption('AI-powered issue spotting is optional. Human review remains mandatory.')
    if st.session_state.docs:
        st.subheader('Registered agreement packages')
        deals=sorted({m.get('deal','').strip() for m in st.session_state.review_meta.values() if m.get('deal','').strip()})
        for deal in deals:
            summary=package_summary(st.session_state.docs,st.session_state.review_meta,deal)
            with st.expander(f"{deal} · {summary['documents']} file(s)"):
                st.write('Document types: '+', '.join(f"{k}: {v}" for k,v in summary['types'].items()))
                for note in summary['notes']: st.info(note)
    st.divider()
    st.subheader('What this version is designed to prove')
    p,q,r=st.columns(3)
    p.info('**Evidence-based**  \nVerifiable source passages and traceable review questions.')
    q.info('**Workflow-aware**  \nOwners, statuses, escalation flags, and event trail.')
    r.info('**Negotiation-aware**  \nDraft-to-draft comparison and clauses that may need renewed attention.')

elif nav=='Agreements':
    st.header('Agreement intake & registry')
    a,b=st.columns([1.6,1],gap='large')
    with a:
        upload=st.file_uploader('Upload PDF · DOCX · TXT (text-based)',type=['pdf','docx','txt'],accept_multiple_files=True)
        col1,col2=st.columns(2)
        with col1:
            if st.button('Add selected documents',type='primary',use_container_width=True):
                if not upload: st.warning('Select one or more files.')
                else:
                    ok=0
                    for item in upload:
                        try: ok+=int(add_doc(item.name,item.getvalue()))
                        except Exception as e: st.error(f'{item.name}: {e}')
                    st.success(f'Added {ok} new documents. Duplicate byte-identical files were skipped.')
        with col2:
            if st.button('Load fictional samples',use_container_width=True):
                load_fictional_deal()
                st.success('Fictional package loaded.')
    with b:
        st.metric('Registered documents',len(st.session_state.docs))
        st.caption('In this version, registry and files live only in your current session. Restart/reload may clear the work. Export before exiting.')
        st.caption('Text scans require OCR; Word tracked changes and legal cross-references are not resolved.')
    if st.session_state.docs:
        st.subheader('Registry')
        table=[]
        for did,doc in st.session_state.docs.items():
            m=st.session_state.review_meta.get(did,{})
            row=registry_row(doc,st.session_state.findings.get(did))
            row.update({'Type':classify_document(doc)['type'],'Deal':m.get('deal',''),'Counterparty':m.get('counterparty',''),'Stage':m.get('status','New'),'Owner':m.get('owner','')})
            table.append(row)
        st.dataframe(pd.DataFrame(table),use_container_width=True,hide_index=True,height=min(360,90+len(table)*39))
        with st.expander('Manage agreement metadata'):
            opts=labels();name=st.selectbox('Agreement',list(opts),key='meta_pick');did=opts[name]
            m=st.session_state.review_meta.get(did,{})
            co1,co2=st.columns(2)
            deal=co1.text_input('Deal / matter label',value=m.get('deal',''),key=f'deal_{did}')
            party=co2.text_input('Counterparty (human entered)',value=m.get('counterparty',''),key=f'party_{did}')
            stages=['New','In review','Awaiting legal','Awaiting finance','Awaiting security / privacy','Awaiting counterparty','Ready for signature (human confirmed)','Signed / closed (human confirmed)']
            status=co1.selectbox('Stage',stages,index=stages.index(m.get('status','New')) if m.get('status','New') in stages else 0,key=f'stage_meta_{did}')
            owner=co2.text_input('Human owner',value=m.get('owner',''),key=f'owner_meta_{did}')
            next_action=st.text_area('Next action / handoff',value=m.get('next_action',''),key=f'next_meta_{did}',height=75)
            if st.button('Save case details'):
                st.session_state.review_meta[did]={'deal':deal,'counterparty':party,'status':status,'owner':owner,'next_action':next_action,
                                                   'updated_at':datetime.now(timezone.utc).isoformat()}
                record('Handoff updated',did,f'{status} · {owner} · {next_action}')
                st.success('Saved for this local session.')
        with st.expander('Remove agreement from session'):
            opts=labels();pick=st.selectbox('Select agreement to remove',list(opts),key='rem_pick');did=opts[pick]
            if st.button('Remove selected agreement'):
                record('Document removed',did,st.session_state.docs[did]['name'])
                for k in ['docs','findings','review_notes','review_meta','review_decisions','issue_spots']:
                    st.session_state[k].pop(did,None)
                st.rerun()

elif nav=='Review workbench':
    st.header('Clause review & exception routing')
    if not st.session_state.docs: st.info('Upload agreements first or load the sample portfolio in Overview.')
    else:
        options=labels();selected=st.selectbox('Select agreement to review',list(options),key='review_doc');did=options[selected];doc=st.session_state.docs[did]
        a,b,c=st.columns(3)
        a.metric('Document type',classify_document(doc)['type'])
        b.metric('Source characters',f"{doc['chars']:,}")
        c.metric('Document pages / sections',len(doc['pages']))
        st.caption('Classification basis: '+classify_document(doc)['basis']+'. Check the document title and related exhibits before relying on scope.')
        for warning in doc['warnings']: st.warning(warning)
        col1,col2=st.columns([1,1.1])
        with col1:
            if st.button('Run first-pass extraction',type='primary',use_container_width=True):
                try:
                    if provider=='Local search (no AI)':
                        findings=local_extract(doc);notes=[]
                    else:
                        if not remote_allowed: raise ValueError('Authorize external processing in the sidebar, or choose a local mode.')
                        with st.spinner('Extracting terms and validating source quotations...'):
                            output=ai_extract(doc,provider,model,api_key)
                        findings=output['findings'];notes=output.get('review_notes',[])
                        if output['included_chunks']<output['all_chunks']:
                            st.warning(f"Selected passages analyzed: {output['included_chunks']}/{output['all_chunks']}. Not comprehensive.")
                    st.session_state.findings[did]=findings
                    st.session_state.review_notes[did]=notes
                    st.session_state.issue_spots.pop(did,None)
                    record('Extraction completed',did,provider)
                    st.success('First pass completed. Review sources and policy exceptions below.')
                except Exception as e: st.error(f'Extraction error: {e}')
        with col2:
            if st.button('Generate AI issue-spotting memorandum',use_container_width=True,disabled=provider=='Local search (no AI)'):
                try:
                    if not remote_allowed: raise ValueError('Authorize external processing in the sidebar first.')
                    with st.spinner('Reviewing selected excerpts against illustrative policy...'):
                        result=ai_issue_spot(doc,st.session_state.playbook,provider,model,api_key)
                    st.session_state.issue_spots[did]=result
                    record('AI memo drafted',did,f"{len(result['issues'])} verified issue citations")
                    st.success('Draft memo ready; every finding requires a human decision.')
                except Exception as e: st.error(f'Memo error: {e}')
        if provider=='Local search (no AI)':
            st.caption('To generate the deeper AI issue-spotting memo, configure an authorized OpenAI API key or local Ollama model.')
        if did in st.session_state.findings:
            findings=st.session_state.findings[did]
            matrix=build_review_matrix(doc,findings,st.session_state.playbook)
            triage=operational_score(matrix)
            st.subheader('Document-aware first-pass review queue')
            m1,m2,m3=st.columns(3)
            m1.metric('High attention',triage['high'])
            m2.metric('Other review prompts',triage['review'])
            m3.metric('Evidence located',triage['located'])
            st.caption('These are deterministic triage counts, **not** legal risk scores, accuracy guarantees, or approval decisions.')
            st.caption(f"Review scope: {classify_document(doc)['type']} · {len(matrix)} relevant clause topics. Optional missing clauses are not automatically classified as policy exceptions.")
            for row in matrix:
                if row['Attention'] not in ('High attention','Review needed'): continue
                with st.container(border=True):
                    col_a,col_b=st.columns([3,1])
                    col_a.markdown(f"**{row['Clause']}** · {row['Attention']}")
                    col_b.caption('Owner: '+row['Review owner'])
                    st.write(row['What to verify'])
                    if row.get('Source'):
                        with st.expander('Inspect original evidence · '+row['Source']):
                            st.code(row.get('Source excerpt',''),language=None)
                    else: st.caption('No verified source passage — inspect the complete agreement and any exhibits.')
            with st.expander('Complete scoped clause matrix'):
                st.dataframe(pd.DataFrame(matrix)[['Attention','Clause','Review owner','Evidence','What to verify','Source']],use_container_width=True,hide_index=True,height=430)
            indicators=term_highlights(findings,classify_document(doc)['type'])
            if indicators:
                st.subheader('Structured terms (verify wording)')
                st.dataframe(pd.DataFrame([{'Indicator':row['label'],'Value':f"{row['value']} {row['unit']}",'Source':row['source_id']} for row in indicators]),
                             use_container_width=True,hide_index=True)
            flags=policy_flags(findings,st.session_state.playbook,classify_document(doc)['type'])
            if flags:
                st.subheader('Policy deviation / escalation details')
                for idx,f in enumerate(flags,1):
                    with st.expander(f"{idx}. {f['route_to']} · {f['priority']}"):
                        st.markdown(f"**Human review question:** {f['review_question']}")
                        st.caption(f"Citation: {f['source_id'] or 'Not located — verify manually'}")
                        if f.get('evidence'):st.code(f['evidence'],language=None)
            if did in st.session_state.issue_spots:
                memo=st.session_state.issue_spots[did]
                st.subheader('AI issue-spotting memo · counsel review required')
                st.info(memo['overall_note'] or 'No overview supplied.')
                st.caption(f"Memo saw selected passages: {memo['read_chunks']}/{memo['all_chunks']}. Uncited issues were discarded; this is not a complete legal review.")
                if not memo['issues']: st.warning('No source-verified AI issues returned. This does not mean the agreement is acceptable.')
                for item in memo['issues']:
                    with st.expander(f"{item['clause']} · {item['reviewer']}"):
                        st.markdown(f"**Potential concern:** {item['concern']}")
                        st.markdown(f"**Business implication:** {item['business_impact']}")
                        st.markdown(f"**Proposed discussion position — do not send without approval:** {item['draft_negotiation_position']}")
                        st.caption(f"Source: {item['source_id']}")
                        st.code(item['evidence'],language=None)
            st.subheader('Reviewer decision log')
            st.caption('Decisions are entered by a person. Automated findings never change an agreement to approved or signed.')
            for item in matrix:
                if item['Attention'] in ('High attention','Review needed'):
                    field=item['Clause']; old=st.session_state.review_decisions.get(did,{}).get(field,{})
                    with st.expander(f"Decision · {field}"):
                        co1,co2=st.columns([1.1,1])
                        decisions=['Pending human review','Escalated to authorized reviewer','Clarification requested','Human-confirmed position (not automatic)']
                        choice=co1.selectbox('Human decision',decisions,index=decisions.index(old.get('decision','Pending human review')) if old.get('decision','Pending human review') in decisions else 0,key=f'dec_{did}_{field}')
                        who=co2.text_input('Decision owner',value=old.get('owner',''),key=f'dec_owner_{did}_{field}')
                        why=st.text_area('Reason and next action',value=old.get('note',''),key=f'dec_note_{did}_{field}',height=70)
                        st.caption('Supporting source: '+(item['Source'] or 'Not located — verify manually'))
                        if st.button('Record human decision',key=f'dec_save_{did}_{field}'):
                            st.session_state.review_decisions.setdefault(did,{})[field]={
                                'decision':choice,'owner':who,'note':why,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
                            record('Human issue decision recorded',did,f'{field}: {choice} · {who}')
                            st.success('Recorded for this session; not a legal sign-off.')
            st.subheader('Review packet & evidence')
            text=create_review_packet(doc,findings,st.session_state.playbook,st.session_state.review_meta.get(did),st.session_state.review_notes.get(did))
            st.download_button('Download human-review packet (.txt)',text,file_name=f"{did}_review_packet.txt",mime='text/plain')
            with st.expander('Inspect all extracted fields and source text'):
                by_source={c['source_id']:c for c in doc['chunks']}
                for r in findings:
                    if r.get('source_id') in by_source:
                        st.markdown(f"**{r['field']}** · {r['status']} · `{r['source_id']}`")
                        st.code(r.get('evidence',''),language=None)
                    else:st.caption(f"{r['field']}: not reliably located in the current pass")
            st.caption('When a source reference is missing or unverified, inspect the full agreement and all exhibits manually.')
        else: st.info('Run first-pass extraction to generate the review matrix, escalation queue and downloadable review packet.')

elif nav=='Compare drafts':
    st.header('Version comparison')
    if len(st.session_state.docs)<2:st.info('Add at least two document versions. The fictional sample portfolio includes an original and revised MSA.')
    else:
        items=labels();keys=list(items)
        c1,c2=st.columns(2)
        first=c1.selectbox('Earlier version',keys,index=0)
        second=c2.selectbox('Later version',keys,index=min(1,len(keys)-1))
        if items[first]==items[second]:st.warning('Choose different documents for a meaningful comparison.')
        elif st.button('Compare versions',type='primary'):
            result=compare_versions(st.session_state.docs[items[first]],st.session_state.docs[items[second]])
            record('Versions compared',items[second],f"{result['old']} → {result['new']}")
            st.session_state.latest_diff=result
        if 'latest_diff' in st.session_state:
            result=st.session_state.latest_diff
            a,b,c=st.columns(3)
            a.metric('Added / changed lines',result['lines_added_or_changed'])
            b.metric('Removed / changed lines',result['lines_removed_or_changed'])
            c.metric('Potentially affected topics',len(result['potentially_affected_fields']))
            st.markdown('**Provision topics touched (heuristic):** '+(', '.join(result['potentially_affected_fields']) or 'No defined topic detected'))
            st.warning(result['notice'])
            st.code(result['diff'] or 'No text differences detected.',language='diff')
            if result['diff_truncated']:st.caption('Diff truncated for preview. Compare smaller sections or files if needed.')
            st.download_button('Download comparison (.diff)',result['diff'],file_name='contract_version_comparison.diff',mime='text/plain')

elif nav=='Contract copilot':
    st.header('Ask the contract evidence')
    if not st.session_state.docs: st.info('Upload a contract or load fictional examples first.')
    else:
        choices=labels();s=st.selectbox('Contract scope',['Entire current portfolio']+list(choices))
        docs=list(st.session_state.docs.values()) if s=='Entire current portfolio' else [st.session_state.docs[choices[s]]]
        st.caption('Examples: "Which version changed the payment window?" · "Where is the limitation of liability?" · "What notice periods appear?"')
        st.caption('In offline mode this is evidence search; choose a configured AI mode for synthesized answers.')
        for msg in st.session_state.chat[-18:]:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
                if msg.get('sources'):st.caption('Source IDs: '+', '.join(msg['sources']))
        q=st.chat_input('Ask about terms, risk signals, obligations or negotiation changes...')
        if q:
            st.session_state.chat.append({'role':'user','content':q})
            with st.chat_message('user'):st.markdown(q)
            with st.chat_message('assistant'):
                try:
                    if provider=='Local search (no AI)':
                        matches=rank_chunks(document_index(docs),q,limit=5,max_chars=9000)
                        ans='**Matching document passages — not AI interpretation:**\n\n'+'\n\n'.join(
                            f"**{x['source_id']} · page/section {x['page']}**\n> {x['text'][:750].replace(chr(10),' ')}" for x in matches)
                        sources=[x['source_id'] for x in matches]
                    else:
                        if not remote_allowed:raise ValueError('Authorize external processing in the sidebar first.')
                        with st.spinner('Retrieving and checking sources...'):
                            out=ai_answer(q,docs,provider,model,api_key)
                        ans=out['answer']+("\n\n**Uncertainty:** "+out['uncertainty'] if out.get('uncertainty') else '')
                        sources=out['source_ids']
                        if not sources:ans+='\n\n**No source citation verified. Treat this response as unsubstantiated.**'
                    st.markdown(ans)
                    if sources:
                        st.caption('Source IDs: '+', '.join(sources))
                        lookup=source_lookup(docs)
                        with st.expander('See cited excerpts'):
                            for sid in sources:
                                if sid in lookup:
                                    nm,chunk=lookup[sid]
                                    st.markdown(f'**{nm} · {sid}**')
                                    st.code(chunk['text'],language=None)
                    st.session_state.chat.append({'role':'assistant','content':ans,'sources':sources})
                    record('Contract question answered','',f'{provider} · {q[:100]}')
                except Exception as e:st.error(f'Unable to complete the question: {e}')
        if st.button('Clear conversation'):
            st.session_state.chat=[];st.rerun()

elif nav=='Operations & playbook':
    st.header('Operations analytics & policy')
    st.caption('All metrics below are derived from observed actions in this local session—no fabricated time savings or model accuracy claims.')
    a,b,c,d=st.columns(4)
    a.metric('Observed intake actions',metrics['intake_events'])
    b.metric('Extraction runs',metrics['review_runs'])
    c.metric('Documents with extraction',f"{metrics['review_coverage_pct']}%")
    d.metric('Handoffs awaiting input',metrics['active_handoffs'])
    if st.session_state.docs:
        statuses=[{'Agreement':d['name'],'Stage':st.session_state.review_meta.get(i,{}).get('status','New'),
                   'Owner':st.session_state.review_meta.get(i,{}).get('owner',''),
                   'Next action':st.session_state.review_meta.get(i,{}).get('next_action','')} for i,d in st.session_state.docs.items()]
        st.subheader('Handoff pipeline')
        st.dataframe(pd.DataFrame(statuses),use_container_width=True,hide_index=True)
    st.subheader('Illustrative playbook')
    st.warning('These are **fictional example thresholds**, not legal standards or any employer\'s actual approved policy. The software does not auto-approve agreements.')
    st.text_area('Editable policy JSON · requires human review',key='playbook_editor',height=240)
    if st.button('Validate & apply session playbook'):
        try:
            cfg=json.loads(st.session_state.playbook_editor)
            for field in ('max_net_payment_days','min_nonrenewal_notice_days','max_breach_notification_hours'):
                if not isinstance(cfg.get(field),int) or isinstance(cfg.get(field),bool) or cfg[field] < 1 or cfg[field]>3650:
                    raise ValueError(f'{field} must be a positive integer ≤ 3650')
            st.session_state.playbook=cfg
            record('Playbook edited','',cfg.get('version','session change'))
            st.success('Playbook updated for this local session. Existing findings can be re-triaged using the new thresholds.')
        except Exception as e:st.error(f'Invalid policy: {e}')
    st.download_button('Export policy JSON',json.dumps(st.session_state.playbook,indent=2),file_name='illustrative_policy.json',mime='application/json')
    st.subheader('Session activity record')
    st.caption('This is an activity trace for demo and debugging, not a tamper-proof, persistent audit log.')
    if st.session_state.events:
        st.dataframe(pd.DataFrame(st.session_state.events[::-1]),use_container_width=True,hide_index=True,height=260)
        st.download_button('Export activity CSV',event_csv(st.session_state.events),file_name='activity_export.csv',mime='text/csv')
    else:st.info('No activity recorded yet.')
    if st.session_state.docs:
        rows=[]
        for did,doc in st.session_state.docs.items():
            row=registry_row(doc,st.session_state.findings.get(did))
            row.update(st.session_state.review_meta.get(did,{}))
            rows.append(row)
        out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(dict.fromkeys(k for row in rows for k in row)),extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)
        st.download_button('Export deal registry CSV',out.getvalue().encode('utf-8-sig'),file_name='deal_registry.csv',mime='text/csv')
        structured={'schema_version':'0.3','demo_limitations': 'Not legal advice; review necessary; session only',
                    'playbook':st.session_state.playbook,'agreements':[
                        {'name':doc['name'],'fingerprint':did,'metadata':st.session_state.review_meta.get(did,{}),
                         'findings':st.session_state.findings.get(did,[]),
                         'memo':st.session_state.issue_spots.get(did),'human_issue_decisions':st.session_state.review_decisions.get(did,{}),
                         'policy_flags':policy_flags(st.session_state.findings[did],st.session_state.playbook,classify_document(doc)['type']) if did in st.session_state.findings else []}
                        for did,doc in st.session_state.docs.items()]}
        st.download_button('Export findings & verified sources JSON',json.dumps(structured,indent=2),file_name='review_data_export.json',mime='application/json')
    st.subheader('Evaluation laboratory · fictional contracts')
    st.caption('Run repeatable fixture tests for source extraction, expected policy flags, and runtime. This is NOT a real-world legal-accuracy benchmark.')
    if st.button('Run fictional contract evaluation'):
        with st.spinner('Evaluating provided synthetic fixtures...'):
            st.session_state.latest_evaluation=run_fixture_evaluation()
        record('Fixture evaluation completed','',f"{st.session_state.latest_evaluation['fixture_count']} fixtures")
    if 'latest_evaluation' in st.session_state:
        ev=st.session_state.latest_evaluation
        e1,e2,e3=st.columns(3)
        e1.metric('Synthetic evidence checks passed',f"{ev['evidence_fixture_pass_pct']}%")
        e2.metric('Expected policy triggers found',f"{ev['policy_fixture_recall_pct']}%")
        e3.metric('Local fixture runtime',f"{ev['total_runtime_ms']} ms")
        st.dataframe(pd.DataFrame(ev['cases']),hide_index=True,use_container_width=True)
        st.warning(ev['caution'])
    st.subheader('Production readiness gates')
    st.markdown('**Not implemented:** authenticated roles and SSO; multi-tenant data separation; encrypted persistence and retention; secure job queue; audit integrity; OCR/visual document review; real DOCX tracked-change redlining; e-signature and CRM integrations; legal review by qualified counsel; evaluation on a representative contract test set; monitoring and incident response.')

st.divider()
st.caption('ContractDesk Pro 0.3 · Independent portfolio prototype · Fictional demo data only · Not legal advice. Review prompts require qualified human judgment.')
