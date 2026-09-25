from contextlib import contextmanager
from datetime import date,timedelta
import json
import httpx
import pytest
from sqlalchemy import select
from test_corpus_hardening import corpus,CONTENT
from test_knowledge import approve,query
from app.config import Settings
from app.models import Passage,PassageEmbedding
from app.ai_provider import HostedProvider,ProviderError,vector
from app.hybrid import index_batch,retrieve
from app.hosted_guidance import HostedGuidance
from app.legal_parser import chunks
from app.environment import load_local_env
from scripts.extract_pdf import ocr_page


class FakeProvider:
    model='synthetic-model'
    embedding_model='synthetic:embedding'
    def __init__(self,reject=False,wrong=False):self.calls=0;self.reject=reject;self.wrong=wrong
    def embed(self,texts):return [[1.0,0.0] for _ in texts]
    def structured(self,instruction,payload,schema):
        self.calls+=1
        if 'draft' in payload:
            return {'supported':not self.reject,'preserves_conditions':True,'no_legal_determination':True}
        return {'claims':[{'text':'Synthetic paraphrase for engineering tests only.',
                           'evidence_ids':['invented' if self.wrong else payload['evidence'][0]['id']]}]}


def test_hosted_no_permission_no_calls(corpus):
    app,_,_,_=corpus;approve(app);provider=FakeProvider()
    answer=HostedGuidance(app.state.sessions,Settings(),provider).generate(query())
    assert provider.calls==0 and answer['retrieval_trace']['mode']=='LOCAL_EXTRACTIVE'


def test_hosted_no_evidence_no_calls(corpus):
    app,_,_,_=corpus;provider=FakeProvider()
    answer=HostedGuidance(app.state.sessions,Settings(),provider).generate(query(allow_hosted_processing=True))
    assert provider.calls==0 and not answer['citations']


def test_hosted_success_is_still_review_required(corpus):
    app,_,_,_=corpus;approve(app);provider=FakeProvider()
    answer=HostedGuidance(app.state.sessions,Settings(),provider).generate(query(allow_hosted_processing=True))
    assert provider.calls==2
    assert answer['support']=='REVIEW_REQUIRED'
    assert answer['retrieval_trace']['mode']=='HOSTED_RAG'
    assert answer['citations'][0]['excerpt']==CONTENT.strip()


@pytest.mark.parametrize('wrong',[False,True])
def test_model_failures_get_at_most_one_repair(corpus,wrong):
    app,_,_,_=corpus;approve(app);provider=FakeProvider(reject=True,wrong=wrong)
    answer=HostedGuidance(app.state.sessions,Settings(),provider).generate(query(allow_hosted_processing=True))
    assert provider.calls<=4 and answer['retrieval_trace']['repair_count']==1
    assert answer['retrieval_trace']['mode']=='LOCAL_EXTRACTIVE'
    assert answer['sections'][0]['claims'][0]['text']==CONTENT.strip()


def test_dense_search_recovers_nonlexical_match_and_respects_revocation(corpus):
    app,_,_,_=corpus;approve(app);provider=FakeProvider()
    with app.state.sessions() as db:
        assert index_batch(db,provider)==1;db.commit()
        assert index_batch(db,provider)==0
        assert retrieve(db,'paraphrase unseen vocabulary','IN',date.today().isoformat(),provider)
        assert not retrieve(db,'paraphrase unseen vocabulary','US',date.today().isoformat(),provider)
        p=db.scalar(select(Passage));p.review={**p.review,'approved':False};db.commit()
        assert not retrieve(db,'paraphrase unseen vocabulary','IN',date.today().isoformat(),provider)


@pytest.mark.parametrize('value',[[0,0],[float('nan')],[float('inf')],[True],[],['x']])
def test_invalid_vectors_rejected(value):
    with pytest.raises(ProviderError):vector(value)


@pytest.mark.parametrize('provider_name',['openai','gemini'])
def test_provider_structured_transport(monkeypatch,provider_name):
    calls=[]
    data={'claims':[]}
    response=({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
        if provider_name=='openai' else {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(data)}]}}]})
    @contextmanager
    def stream(method,url,**kwargs):
        calls.append((url,kwargs));yield httpx.Response(200,json=response,request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'stream',stream)
    settings=Settings(ai_provider=provider_name,ai_key='synthetic-key',ai_model='synthetic-model',cloud_processing_allowed=True)
    assert HostedProvider(settings).structured('test',{}, {'type':'object'})==data
    assert 'synthetic-key' not in calls[0][0]
    assert calls[0][1]['follow_redirects'] is False
    if provider_name=='openai':assert calls[0][1]['json']['store'] is False


def test_hosted_configuration_requires_explicit_permission():
    with pytest.raises(ValueError):Settings(guidance_mode='hosted',ai_provider='openai',ai_key='x',ai_model='x',embedding_model='x').validate()


def test_provision_continuation_preserves_exceptions():
    pages=[{'page':1,'text':'Section 3. Synthetic heading\n'+'Condition. '*15},
           {'page':2,'text':'Provided that this synthetic exception remains attached.\nSection 4. Next provision\n'+'Other condition. '*8}]
    parsed=chunks(pages)
    assert len(parsed)==2
    assert 'Provided that' in parsed[0]['text'] and parsed[0]['page_end']==2
    for item in parsed:
        restored='\n'.join(pages[s['page']-1]['text'][s['start']:s['end']] for s in item['segments'])
        assert restored==item['text']


def test_long_provision_is_quarantined_not_cut():
    parsed=chunks([{'page':1,'text':'Section 3. Heading\n'+'condition '*1500}])
    assert len(parsed)==1 and parsed[0]['quarantined'] and len(parsed[0]['text'])>10000


def test_curator_review_compare_and_swap(corpus):
    app,c,user,doc=corpus;user.role='curator'
    p=c.get('/api/v1/corpus/documents/'+doc['document_id']+'/passages').json()[0]
    body={'approved':True,'expected_sha256':p['sha256'],'expected_review_revision':0,
          'provision':'Synthetic section 1','effective_from':'2020-01-01',
          'review_valid_until':(date.today()+timedelta(days=1)).isoformat(),'notes':'Synthetic fixture approval; not a real review.'}
    endpoint='/api/v1/corpus/passages/'+p['id']+'/review'
    assert c.patch(endpoint,json=body).status_code==200
    assert c.patch(endpoint,json=body).status_code==409
    assert c.patch(endpoint,json={**body,'approved':False,'expected_review_revision':1}).status_code==200
    assert len(c.get('/api/v1/corpus/passages/'+p['id']+'/reviews').json())==2


def test_missing_ocr_binaries_fails_closed(monkeypatch):
    monkeypatch.setattr('shutil.which',lambda name:None)
    with pytest.raises(ValueError,match='requires Tesseract'):ocr_page('unused.pdf',1)


def test_environment_loader_does_not_execute_or_override(tmp_path,monkeypatch):
    p=tmp_path/'settings';p.write_text('AYUNEX_TEST_SETTING="$(do-not-run)"\n')
    monkeypatch.delenv('AYUNEX_TEST_SETTING',raising=False)
    load_local_env(p)
    import os
    assert os.environ['AYUNEX_TEST_SETTING']=='$(do-not-run)'
    monkeypatch.setenv('AYUNEX_TEST_SETTING','explicit');load_local_env(p)
    assert os.environ['AYUNEX_TEST_SETTING']=='explicit'
