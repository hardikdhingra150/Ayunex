from datetime import date
import os
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import pytest
import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, func
from app.main import create_app
from app.config import Settings
from app.models import Base, Case, Snapshot, Artifact, Event
from app.integrations import identity, GuidanceClient
from app.schemas import Principal, Jurisdiction, Passport, GuidanceAnswer
from app.domain import classify, clarify, services, RULESET

IN={'layer':'NATIONAL','country':'IN','framework':None}


class FakeC:
    calls=0
    def generate(self,p):
        self.calls+=1
        return {'request_id':p['request_id'],'context_hash':p['context_hash'],'jurisdiction':p['jurisdiction'],'as_of_date':p['as_of_date'],'support':'SUPPORTED_IN_SCOPE','sections':[{'id':'one','title':'Test fixture','support':'SUPPORTED_IN_SCOPE','reason':'Test only','claims':[{'id':'c1','text':'Synthetic testing passage','jurisdiction':p['jurisdiction'],'citation_ids':['s1']}]}],'citations':[{'id':'s1','authority':'TEST ONLY','title':'Synthetic authority','url':'https://example.org/test','provision':'TEST-1','excerpt':'Synthetic testing passage','version':'test-v1','jurisdiction':p['jurisdiction'],'effective_from':'2020-01-01','effective_to':None,'retrieved_at':'2026-09-23T00:00:00Z','review_status':'VERIFIED','access_class':'PUBLIC'}]}


@pytest.fixture
def env(tmp_path):
    fake=FakeC()
    url='sqlite:///'+str(tmp_path/'test.db')
    pg_url=os.getenv('TEST_POSTGRES_URL')
    admin_engine=None
    if pg_url:
        schema='test_'+uuid4().hex
        admin_engine=create_engine(pg_url)
        with admin_engine.begin() as connection:connection.execute(text('CREATE SCHEMA '+schema))
        url=make_url(pg_url).update_query_dict({'options':'-csearch_path='+schema}).render_as_string(hide_password=False)
    app=create_app(Settings(database_url=url,environment='test',dev_token='a'*40),fake)
    Base.metadata.create_all(app.state.engine)
    user=Principal(subject='alice',tenant='tenant-a',role='user')
    app.dependency_overrides[identity]=lambda:user
    with TestClient(app) as client:
        yield client,app,user,fake
    if admin_engine:
        with admin_engine.begin() as connection:connection.execute(text('DROP SCHEMA '+schema+' CASCADE'))
        admin_engine.dispose()


def create(client,**kw):
    body={'title':'Synthetic QA case','jurisdiction':IN,'as_of_date':'2026-09-23','consent':{'accepted':True,'notice_version':'case-notice-v1'},**kw}
    r=client.post('/api/v1/cases',json=body)
    assert r.status_code==201,r.text
    return r.json()


def current(c,case):return c.get('/api/v1/cases/'+case['id']).json()
def path(case,suffix=''):return '/api/v1/cases/'+case['id']+suffix
def fact(value=None,**kw):return {'value':value,'provenance':'user-entered','confirmed':False,'unknown':False,**kw}
def passport(c,case,facts):return c.post(path(case,'/passport/answers'),json={'expected_revision':current(c,case)['revision'],'passport':{'facts':facts,'ingredients':[]}})
def guided(c,case,key='request-0001',question='Test question'):
    return c.post(path(case,'/guidance'),json={'question':question},headers={'Idempotency-Key':key})


def test_openapi(env):
    c,_,_,_=env
    s=c.get('/openapi.json').json()
    assert len(s['paths'])>=27
    assert 'GuidanceAnswer' in str(s) or '/api/v1/guidance' in s['paths']


def test_create_consent_required(env):
    c,_,_,_=env
    assert c.post('/api/v1/cases',json={'title':'QA'}).status_code==422
    case=create(c)
    assert len(c.get('/api/v1/cases').json())==1
    assert c.get(path(case)).headers['cache-control']=='no-store'


@pytest.mark.parametrize('role',['curator','auditor','facilitator'])
def test_roles_cannot_create(env,role):
    c,app,user,_=env;user.role=role
    r=c.post('/api/v1/cases',json={'title':'Synthetic QA','jurisdiction':IN,'as_of_date':'2026-09-23','consent':{'accepted':True,'notice_version':'case-notice-v1'}})
    assert r.status_code==403


def test_tenant_and_owner_isolation(env):
    c,_,user,_=env;case=create(c)
    user.tenant='other'
    assert c.get(path(case)).status_code==404
    assert c.get('/api/v1/cases').json()==[]
    user.tenant='tenant-a';user.subject='bob'
    assert c.get(path(case)).status_code==403
    assert c.get('/api/v1/cases').json()==[]


def test_optimistic_updates_and_archive(env):
    c,_,_,_=env;case=create(c)
    body={'expected_revision':case['revision'],'title':'Updated QA'}
    assert c.patch(path(case),json=body).status_code==200
    assert c.patch(path(case),json=body).status_code==409
    r=c.patch(path(case),json={'expected_revision':current(c,case)['revision'],'archived':True})
    assert r.json()['status']=='Archived'
    assert c.get('/api/v1/cases').json()==[]
    assert len(c.get('/api/v1/cases?archived=true').json())==1


def test_passport_versions_and_unknowns(env):
    c,_,_,_=env;case=create(c)
    f={'intended_use':fact('FOOD'),'origin':fact('secret',unknown=True)}
    r=passport(c,case,f)
    assert r.json()['passport']['facts']['origin']['value'] is None
    assert r.json()['version']==1
    assert passport(c,case,f).json()['version']==1
    f['claims']=fact('No medical claim')
    assert passport(c,case,f).json()['version']==2
    assert len(c.get(path(case,'/passport/versions')).json())==2


def test_provenance_and_extracted_confirmation(env):
    c,_,_,_=env;case=create(c)
    assert passport(c,case,{'intended_use':fact('FOOD',provenance='facilitator-confirmed')}).status_code==403
    assert passport(c,case,{'intended_use':fact('FOOD',provenance='extracted')}).status_code==200
    assert guided(c,case).status_code==409
    assert passport(c,case,{'intended_use':fact('FOOD',provenance='extracted',confirmed=True)}).status_code==200
    assert guided(c,case).status_code==200


def test_general_bypass(env):
    c,_,_,_=env;case=create(c,query_kind='GENERAL_INFORMATION')
    assert passport(c,case,{}).status_code==409
    r=c.post(path(case,'/classify')).json()
    assert r['payload']['route']=='NOT_REQUIRED'
    assert c.post(path(case,'/clarifications')).json()['payload']['questions']==[]
    assert guided(c,case).status_code==200
    assert c.post('/api/v1/guidance',json={'question':'General test','jurisdiction':IN,'as_of_date':'2026-09-23'}).status_code==200


@pytest.mark.parametrize('rule',RULESET['rules'])
def test_all_rule_branches_stay_unvalidated(rule):
    passport={'facts':{k:fact(v) for k,v in rule['conditions'].items()},'ingredients':[]}
    a=classify(passport,IN,'2026-09-23')
    assert a==classify(passport,IN,'2026-09-23')
    assert a['route']=='UNRESOLVED'
    assert any(r['route']==rule['route'] and r['all_conditions_met'] for r in a['alternatives'])
    assert a['review_required']


def test_unknown_does_not_default_to_proprietary():
    a=classify({'facts':{}},IN,'2026-09-23')
    assert a['route']=='UNRESOLVED' and a['missing_facts']
    b=classify({'facts':{'intended_use':fact('COSMETIC'),'administration_route':fact('ORAL')}},IN,'2026-09-23')
    assert b['conflicts']
    assert not any(r['route']=='PROPRIETARY_AYURVEDA' for r in b['alternatives'])


def test_clarifications_max_three_no_repeated_unknown():
    p={'facts':{'intended_use':fact(unknown=True)}}
    q=clarify(p,classify(p,IN,'2026-09-23'))
    assert len(q['questions'])<=3 and q['escalate']
    assert all(x['fact_id']!='intended_use' for x in q['questions'])


def test_abs_never_defaults_to_exempt():
    s=services({'facts':{}},IN,'2026-09-23')
    assert s['abs']['clearance'] is False and s['abs']['missing_facts']
    assert s['traditional_knowledge']['restricted_access_granted'] is False
    assert len(s['ip'])==7


@pytest.mark.parametrize('j',[{'layer':'NATIONAL'}, {'layer':'TREATY_FRAMEWORK','country':'IN','framework':'PCT'}, {'layer':'EXPORT_MARKET','country':'US','framework':'PCT'}])
def test_invalid_contexts(j):
    with pytest.raises(ValidationError):Jurisdiction.model_validate(j)


def test_unsupported_country():
    a=classify({'facts':{}},{'layer':'EXPORT_MARKET','country':'ZZ','framework':None},'2026-09-23')
    assert a['route']=='OUTSIDE_SUPPORTED_SCOPE'


def test_guidance_idempotency_and_invalidations(env):
    c,_,_,fake=env;case=create(c)
    a=guided(c,case);assert a.status_code==200,a.text
    b=guided(c,case);assert a.json()['id']==b.json()['id'] and fake.calls==1
    assert guided(c,case,question='Different question').status_code==409
    c.patch(path(case),json={'expected_revision':current(c,case)['revision'],'as_of_date':'2026-09-24'})
    assert guided(c,case).status_code==409
    assert c.get('/api/v1/answers/'+a.json()['id']).json()['stale']
    assert c.get('/api/v1/answers/'+a.json()['id']+'/events').status_code==409


def test_stream_exposes_only_verified_sections(env):
    c,_,_,_=env;case=create(c);a=guided(c,case).json()
    r=c.get('/api/v1/answers/'+a['id']+'/events')
    assert 'section_verified' in r.text and 'answer_complete' in r.text and 'draft' not in r.text


@pytest.mark.parametrize('mutation',['jurisdiction','date','citation','restricted','empty','duplicate'])
def test_evidence_firewall(mutation):
    p={'request_id':'test','context_hash':'test','jurisdiction':IN,'as_of_date':'2026-09-23'}
    a=FakeC().generate(p)
    if mutation=='jurisdiction':a['citations'][0]['jurisdiction']={'layer':'EXPORT_MARKET','country':'US','framework':None}
    if mutation=='date':a['citations'][0]['effective_from']='2027-01-01'
    if mutation=='citation':a['sections'][0]['claims'][0]['citation_ids']=['nonexistent']
    if mutation=='restricted':a['citations'][0]['access_class']='PAID'
    if mutation=='empty':a['sections'][0]['claims']=[]
    if mutation=='duplicate':a['citations'].append(a['citations'][0])
    with pytest.raises(ValidationError):GuidanceAnswer.model_validate(a)


def test_missing_module_c_is_503(env):
    c,app,_,_=env;case=create(c)
    app.state.guidance=GuidanceClient(app.state.settings)
    assert guided(c,case).status_code==503


def test_module_c_timeout(env,monkeypatch):
    c,app,_,_=env;case=create(c)
    app.state.settings.guidance_url='https://service.example/guidance'
    app.state.guidance=GuidanceClient(app.state.settings)
    def timeout(*a,**k):raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(httpx,'stream',timeout)
    assert guided(c,case).status_code==504


def test_checklist_and_exports_delete_cascade(env):
    c,app,_,_=env;case=create(c);passport(c,case,{'intended_use':fact('FOOD')})
    r=c.post(path(case,'/checklists')).json()
    changed=c.patch('/api/v1/checklists/'+r['id']+'/items/1',json={'expected_revision':r['case_revision'],'status':'DONE'})
    assert changed.status_code==200,changed.text
    e=c.post(path(case,'/exports')).json()
    assert c.get('/api/v1/exports/'+e['id']).status_code==200
    assert c.delete('/api/v1/exports/'+e['id']).status_code==204
    c.post(path(case,'/exports'))
    assert c.delete(path(case),params={'expected_revision':current(c,case)['revision']}).status_code==204
    with app.state.sessions() as db:
        for model in [Case,Snapshot,Artifact,Event]:assert db.scalar(select(func.count()).select_from(model))==0


def test_review_consent_roles_and_withdrawal(env):
    c,app,user,_=env;case=create(c)
    user.role='facilitator'
    assert c.get(path(case)).status_code==403
    user.role='user'
    body={'expected_revision':current(c,case)['revision'],'question':'Review origin','consent':True,'sharing_scope':'CURRENT_CASE_FACTS_AND_EVIDENCE','consent_version':'facilitator-sharing-v1'}
    e=c.post(path(case,'/escalations'),json=body).json()
    assert e['payload']['external_delivery']=='NOT_SENT'
    assert c.patch('/api/v1/escalations/'+e['id'],json={'expected_revision':e['case_revision'],'comment':'Test review','status':'Reviewed'}).status_code==403
    user.role='facilitator'
    assert c.get(path(case)).status_code==200
    assert len(c.get('/api/v1/facilitator/queue').json())==1
    r=c.patch('/api/v1/escalations/'+e['id'],json={'expected_revision':e['case_revision'],'comment':'Test review','status':'Reviewed'})
    assert r.status_code==200,r.text
    user.role='user'
    assert c.delete('/api/v1/escalations/'+e['id'],params={'expected_revision':current(c,case)['revision']}).status_code==200
    user.role='facilitator'
    assert c.get(path(case)).status_code==403
    assert c.get('/api/v1/facilitator/queue').json()==[]


def test_auth_no_header_trust(env):
    c,app,_,_=env;app.dependency_overrides.clear()
    assert c.get('/api/v1/cases',headers={'X-Tenant':'arbitrary','X-Role':'administrator'}).status_code==401
    assert c.get('/api/v1/me',headers={'Authorization':'Bearer '+'a'*40}).json()['role']=='user'
    assert c.get('/api/v1/me',headers={'Authorization':'Bearer wrong'}).status_code==401


def test_production_rejects_dev_auth():
    with pytest.raises(ValueError):Settings(environment='production',dev_token='a'*40).validate()


def test_audit_role_read_only(env):
    c,_,user,_=env;case=create(c);user.role='auditor'
    assert c.get(path(case,'/activity')).status_code==200
    assert c.get(path(case,'/passport')).status_code==403


def test_invalid_options_and_unknown_fields(env):
    c,_,_,_=env;case=create(c)
    assert passport(c,case,{'intended_use':fact('Anything')}).status_code==422
    assert passport(c,case,{'modified':fact('true')}).status_code==422
    assert passport(c,case,{'secret_ratio':fact('50%')}).status_code==422


def test_invalid_c_response_is_safe_502(env):
    c,app,_,_=env;case=create(c)
    class Broken:
        def generate(self,p):return {'claims':['unverified draft']}
    app.state.guidance=Broken()
    r=guided(c,case)
    assert r.status_code==502
    assert 'unverified draft' not in r.text
    assert c.get(path(case,'/artifacts')).json()==[]


def test_cannot_request_paid_access(env):
    c,_,_,_=env;case=create(c)
    r=c.post(path(case,'/guidance'),headers={'Idempotency-Key':'test-paid'},json={'question':'Test','allowed_access_classes':['PAID']})
    assert r.status_code==422


def test_fact_change_stales_answers_and_checklists(env):
    c,_,_,_=env;case=create(c)
    answer=guided(c,case).json()
    check=c.post(path(case,'/checklists')).json()
    passport(c,case,{'intended_use':fact('FOOD')})
    assert c.get('/api/v1/answers/'+answer['id']).json()['stale']
    assert c.patch('/api/v1/checklists/'+check['id']+'/items/1',json={'expected_revision':current(c,case)['revision'],'status':'DONE'}).status_code==409


def test_context_change_revokes_review_access(env):
    c,_,user,_=env;case=create(c)
    body={'expected_revision':current(c,case)['revision'],'question':'Review origin','consent':True,'sharing_scope':'CURRENT_CASE_FACTS_AND_EVIDENCE','consent_version':'facilitator-sharing-v1'}
    e=c.post(path(case,'/escalations'),json=body)
    assert e.status_code==200
    user.role='facilitator'
    assert c.get(path(case,'/passport/versions')).status_code==403
    assert c.get(path(case,'/activity')).status_code==403
    user.role='user'
    c.patch(path(case),json={'expected_revision':current(c,case)['revision'],'jurisdiction':{'layer':'EXPORT_MARKET','country':'US'}})
    user.role='facilitator'
    assert c.get('/api/v1/facilitator/queue').json()==[]
    assert c.get(path(case)).status_code==403


def test_persistence_across_app_restart(env):
    c,app,_,_=env;case=create(c)
    other=create_app(app.state.settings)
    other.dependency_overrides[identity]=lambda:Principal(subject='alice',tenant='tenant-a',role='user')
    with TestClient(other) as restarted:
        assert restarted.get(path(case)).json()['title']==case['title']


def test_auditor_cannot_cross_tenant(env):
    c,_,user,_=env;case=create(c);user.role='auditor';user.tenant='other'
    assert c.get(path(case,'/activity')).status_code==404


def test_context_changed_during_c_request_discards_response(env):
    c,app,_,_=env;case=create(c)
    class Changing(FakeC):
        def generate(self,p):
            with app.state.sessions() as db:
                row=db.get(Case,case['id']);row.as_of='2026-09-24';db.commit()
            return super().generate(p)
    app.state.guidance=Changing()
    assert guided(c,case).status_code==409
    assert c.get(path(case,'/artifacts')).json()==[]


def test_unresolved_section_cannot_expose_claims():
    a=FakeC().generate({'request_id':'test','context_hash':'test','jurisdiction':IN,'as_of_date':'2026-09-23'})
    a['support']='MISSING_EVIDENCE';a['sections'][0]['support']='MISSING_EVIDENCE'
    with pytest.raises(ValidationError):GuidanceAnswer.model_validate(a)


def test_identity_service_failure_fails_closed(env,monkeypatch):
    c,app,_,_=env;app.dependency_overrides.clear()
    app.state.settings.identity_url='https://identity.example/introspect'
    def fail(*a,**kw):raise httpx.ConnectError('unavailable')
    monkeypatch.setattr(httpx,'stream',fail)
    assert c.get('/api/v1/cases',headers={'Authorization':'Bearer unknown'}).status_code==503


def test_openapi_exposes_bearer_and_core_models(env):
    c,_,_,_=env;s=c.get('/openapi.json').json()
    assert s['components']['securitySchemes']['HTTPBearer']['scheme']=='bearer'
    assert {'CaseResponse','PassportResponse','GuidanceAnswer'} <= set(s['components']['schemas'])


def test_dev_role_tokens_support_roles(env):
    c,app,_,_=env;app.dependency_overrides.clear()
    token = app.state.settings.dev_token
    # default dev token -> role user
    r_user = c.get('/api/v1/me', headers={'Authorization': f'Bearer {token}'})
    assert r_user.status_code == 200
    assert r_user.json()['role'] == 'user'
    # facilitator dev token -> role facilitator
    r_fac = c.get('/api/v1/me', headers={'Authorization': f'Bearer {token}:facilitator'})
    assert r_fac.status_code == 200
    assert r_fac.json()['role'] == 'facilitator'
    # admin dev token -> role administrator
    r_admin = c.get('/api/v1/me', headers={'Authorization': f'Bearer {token}:administrator'})
    assert r_admin.status_code == 200
    assert r_admin.json()['role'] == 'administrator'

