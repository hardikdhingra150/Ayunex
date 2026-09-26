from datetime import date
from sqlalchemy import select
from app.config import Settings
from app.module_d import create_session_token,verify_session_token
from app.models import Passage
from app.knowledge import KnowledgeGuidance
from test_module_d import client
from test_backend import env,create
from test_corpus_hardening import corpus
from test_knowledge import approve,query


def test_guest_cannot_choose_identity_or_role(client):
    c,app=client
    for body in ({'role':'administrator'},{'role':'curator'},{'subject':'victim'},{'tenant':'victim'}):
        assert c.post('/api/v1/auth/session',json=body).status_code==422
    assert c.get('/api/v1/auth/session').status_code in {404,405}
    app.state.settings.environment='production'
    assert c.post('/api/v1/auth/session').status_code==403


def test_guest_sessions_are_isolated(client):
    c,_=client
    a=c.post('/api/v1/auth/session').json();b=c.post('/api/v1/auth/session').json()
    assert a['principal']['tenant']!=b['principal']['tenant']
    assert a['principal']['subject']!=b['principal']['subject']
    headers={'Authorization':'Bearer '+a['token']}
    case=c.post('/api/v1/cases',headers=headers,json={'title':'Private case','jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat(),'consent':{'accepted':True,'notice_version':'case-notice-v1'}}).json()
    assert c.get('/api/v1/cases/'+case['id'],headers={'Authorization':'Bearer '+b['token']}).status_code==404


def test_local_sessions_never_authorize_production():
    dev=Settings(environment='test')
    token=create_session_token('a','b','user',dev)
    assert verify_session_token(token,dev)
    assert verify_session_token(token,Settings(environment='production',dev_token='')) is None
    assert verify_session_token(create_session_token('a','b','user',dev,-1),dev) is None
    assert verify_session_token(create_session_token('a','b','user',dev,7200),dev) is None


def test_introspection_requires_service_credential(client):
    c,_=client
    assert c.post('/api/v1/auth/introspect',json={'token':'anything'}).status_code==401


def test_hosted_consent_is_scoped_and_withdrawable(env):
    c,_,user,fake=env
    body={'question':'Synthetic question','jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat(),'allow_hosted_processing':True}
    assert c.post('/api/v1/guidance',json=body).status_code==403
    assert fake.calls==0
    assert c.post('/api/v1/consent/record',json={'purpose':'hosted_ai_processing'}).status_code==200
    assert c.post('/api/v1/guidance',json=body).status_code==200
    user.subject='other'
    assert c.post('/api/v1/guidance',json=body).status_code==403
    user.subject='alice'
    c.post('/api/v1/consent/withdraw',json={'purpose':'hosted_ai_processing'})
    assert c.post('/api/v1/guidance',json=body).status_code==403


def test_source_text_pilot_is_not_production_evidence(corpus):
    app,_,_,_=corpus;approve(app)
    with app.state.sessions() as db:
        p=db.scalar(select(Passage));p.review={**p.review,'review_status':'SOURCE_TEXT_CHECKED','expert_reviewed':False};db.commit()
    assert KnowledgeGuidance(app.state.sessions).generate(query())['citations'][0]['review_status']=='SOURCE_TEXT_CHECKED'
    assert not KnowledgeGuidance(app.state.sessions,allow_source_checked=False).generate(query())['citations']


def test_spa_does_not_serve_parent_files(client):
    c,_=client
    response=c.get('/%2e%2e%2fpackage.json')
    assert response.status_code==404


def test_default_dev_token_does_not_load_in_production(monkeypatch):
    from app.config import _default_dev_token
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('DEV_API_TOKEN','should-not-be-loaded')
    assert _default_dev_token()==''
