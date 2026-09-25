from datetime import date,timedelta
import os
from uuid import uuid4
from unittest.mock import patch
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,create_engine,text
from sqlalchemy.engine import make_url
from app.config import Settings
from app.main import create_app
from app.models import Base,Passage,SourceDocument,CorpusReviewEvent
from app.schemas import Principal,GuidanceAnswer
from app.integrations import identity
from app.corpus import persist,search,sha,validate_url,ingest
from app.corpus_api import ExtractiveGuidance

SOURCE={'id':'test-statute','title':'Synthetic test statute','authority':'Test only','url':'https://ipindia.gov.in/test.pdf','domain':'PATENT','kind':'PDF','access':'PUBLIC'}
CONTENT='Traditional knowledge and patent examination. Synthetic fixture only. '*15

@pytest.fixture
def corpus(tmp_path):
    url='sqlite:///'+str(tmp_path/'corpus.db')
    admin=None
    if os.getenv('TEST_POSTGRES_URL'):
        admin=create_engine(os.environ['TEST_POSTGRES_URL'])
        schema='test_'+uuid4().hex
        with admin.begin() as conn:conn.execute(text('CREATE SCHEMA '+schema))
        url=make_url(os.environ['TEST_POSTGRES_URL']).update_query_dict({'options':'-csearch_path='+schema}).render_as_string(hide_password=False)
    app=create_app(Settings(environment='test',database_url=url,guidance_mode='corpus'))
    Base.metadata.create_all(app.state.engine)
    principal=Principal(subject='tester',tenant='test',role='user')
    app.dependency_overrides[identity]=lambda:principal
    with app.state.sessions() as db:
        doc=persist(db,SOURCE,b'%PDF-fixture',SOURCE['url'],[{'page':1,'text':CONTENT}]);db.commit()
    try:
        with TestClient(app) as client:yield app,client,principal,doc
    finally:
        if admin:
            with admin.begin() as conn:conn.execute(text('DROP SCHEMA '+schema+' CASCADE'))
            admin.dispose()

def test_new_corpus_cannot_support_answers(corpus):
    app,c,_,doc=corpus
    with app.state.sessions() as db:
        assert search(db,'traditional knowledge','IN',date.today().isoformat())==[]
        assert search(db,'traditional knowledge','IN',date.today().isoformat(),False)
    result=c.post('/api/v1/guidance',json={'question':'traditional knowledge','jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat()})
    assert result.status_code==200
    assert result.json()['support']=='MISSING_EVIDENCE' and result.json()['citations']==[]

def test_public_search_labels_unreviewed(corpus):
    _,c,_,_=corpus
    r=c.get('/api/v1/corpus/search',params={'q':'traditional knowledge','as_of':date.today().isoformat(),'reviewed_only':False}).json()
    assert not r['results'][0]['reviewed']
    assert r['purpose']=='SOURCE_DISCOVERY_NOT_LEGAL_ADVICE'

def test_review_roles_and_extractive_result(corpus):
    app,c,user,_=corpus
    with app.state.sessions() as db:p=db.scalar(select(Passage));pid=p.id;checksum=p.sha256
    body={'approved':True,'expected_sha256':checksum,'provision':'TEST ONLY section 1','effective_from':'2020-01-01','review_valid_until':(date.today()+timedelta(days=30)).isoformat(),'notes':'Synthetic test review, not a real legal approval.'}
    endpoint='/api/v1/corpus/passages/'+pid+'/review'
    assert c.patch(endpoint,json=body).status_code==403
    user.role='curator'
    assert c.patch(endpoint,json={**body,'expected_sha256':'0'*64}).status_code==409
    assert c.patch(endpoint,json=body).status_code==200
    user.role='user'
    r=c.post('/api/v1/guidance',json={'question':'traditional knowledge','jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat()})
    assert r.status_code==200,r.text
    answer=GuidanceAnswer.model_validate(r.json())
    assert answer.support=='REVIEW_REQUIRED'
    assert answer.citations[0].excerpt==CONTENT.strip()
    with app.state.sessions() as db:assert db.scalar(select(func.count()).select_from(CorpusReviewEvent))==1

def test_versioning_is_idempotent_and_supersedes(corpus):
    app,_,_,doc=corpus
    with app.state.sessions() as db:
        assert persist(db,SOURCE,b'%PDF-fixture',SOURCE['url'],[{'page':1,'text':CONTENT}])['status']=='UNCHANGED'
        fresh=persist(db,SOURCE,b'%PDF-fixture-v2',SOURCE['url'],[{'page':1,'text':CONTENT+'Updated'}]);db.commit()
        assert fresh['document_id']!=doc['document_id']
        assert not db.get(SourceDocument,doc['document_id']).active
        assert db.scalar(select(func.count()).select_from(SourceDocument))==2

def test_restricted_and_registry_are_pointer_only():
    assert ingest(None,{**SOURCE,'access':'RESTRICTED'})['status']=='POINTER_ONLY'
    assert ingest(None,{**SOURCE,'kind':'POINTER'})['status']=='POINTER_ONLY'

@pytest.mark.parametrize('url',['http://ipindia.gov.in/test','https://127.0.0.1/a','https://evil.example/a','https://user:password@ipindia.gov.in/a','https://ipindia.gov.in:444/a','file:///etc/passwd'])
def test_ssrf_allowlist(url):
    with pytest.raises(ValueError):validate_url(url)

def test_private_dns_rejected():
    with patch('socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):
        with pytest.raises(ValueError):validate_url('https://ipindia.gov.in/test')

def test_request_limits_and_request_id(corpus):
    app,c,_,_=corpus
    r=c.post('/api/v1/cases',content=b'x'*(1024*1024+1))
    assert r.status_code==413 and r.headers['x-request-id']
    assert c.post('/api/v1/cases',content='test',headers={'Content-Encoding':'gzip'}).status_code==415
    assert c.get('/health',headers={'host':'evil.example'}).status_code==400
    assert c.get('/health').headers['x-request-id']

def test_rate_limiting(tmp_path):
    app=create_app(Settings(environment='test',database_url='sqlite:///'+str(tmp_path/'rate.db'),rate_limit=1))
    with TestClient(app) as c:
        assert c.get('/api/v1/me').status_code==401
        assert c.get('/api/v1/me').status_code==429
        assert c.get('/health').status_code==200

def test_invalid_review_dates(corpus):
    app,c,user,_=corpus;user.role='curator'
    with app.state.sessions() as db:p=db.scalar(select(Passage));pid=p.id;checksum=p.sha256
    body={'approved':True,'expected_sha256':checksum,'provision':'TEST','effective_from':'2025-01-01','effective_to':'2020-01-01','review_valid_until':date.today().isoformat(),'notes':'Synthetic test review, not a real legal approval.'}
    assert c.patch('/api/v1/corpus/passages/'+pid+'/review',json=body).status_code==422

def test_country_and_date_filter(corpus):
    app,_,_,_=corpus
    with app.state.sessions() as db:
        p=db.scalar(select(Passage));p.review={'approved':True,'effective_from':'2025-01-01','effective_to':None,'review_valid_until':(date.today()+timedelta(days=30)).isoformat()};db.commit()
        assert search(db,'knowledge','US',date.today().isoformat())==[]
        assert search(db,'knowledge','IN','2024-01-01')==[]
        p.review={**p.review,'review_valid_until':'2020-01-01'};db.commit()
        assert search(db,'knowledge','IN',date.today().isoformat())==[]
