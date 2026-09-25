"""Synthetic engineering fixtures only — not expert-approved legal benchmarks."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date,timedelta
import httpx
import pytest
from sqlalchemy import select
from test_corpus_hardening import corpus, SOURCE, CONTENT
from app.models import Passage,SourceDocument
from app.corpus import persist,sha
from app.retrieval import search,verify_answer,RetrievalCapacityError
from app.knowledge import KnowledgeGuidance
from app.integrations import bounded_post


def approve(app, **changes):
    with app.state.sessions() as db:
        p=db.scalar(select(Passage))
        p.review={'approved':True,'provision':'TEST section 3(p)','effective_from':'2020-01-01',
                  'effective_to':None,'review_valid_until':(date.today()+timedelta(days=30)).isoformat(),**changes}
        db.commit();return p.id


def query(**changes):
    return {'question':'traditional knowledge','request_id':'test','context_hash':'test',
            'jurisdiction':{'layer':'NATIONAL','country':'IN','framework':None},
            'as_of_date':date.today().isoformat(),'query_kind':'GENERAL_INFORMATION',
            'original_language':'en','allowed_access_classes':['PUBLIC'],**changes}


def test_local_trace_and_exact_verifier(corpus):
    app,_,_,_=corpus;approve(app)
    a=KnowledgeGuidance(app.state.sessions).generate(query())
    assert a['retrieval_trace']['verification']=='EXACT_QUOTES_VERIFIED'
    assert a['retrieval_trace']['repair_count']==0
    assert a['support']=='REVIEW_REQUIRED'
    with app.state.sessions() as db:
        assert verify_answer(db,a)==[]
        bad=deepcopy(a);bad['citations'][0]['excerpt']='Invented text'
        assert 'CITATION_CHANGED_OR_TAMPERED' in verify_answer(db,bad)
        bad=deepcopy(a);bad['sections'][0]['claims'][0]['text']='You will receive a patent.'
        assert 'NOT_AN_EXACT_REVIEWED_EXCERPT' in verify_answer(db,bad)


@pytest.mark.parametrize('changes',[
    {'original_language':'hi'},
    {'jurisdiction':{'layer':'EXPORT_MARKET','country':'US','framework':None}},
    {'allowed_access_classes':['RESTRICTED']},
])
def test_unsupported_context_abstains(corpus,changes):
    app,_,_,_=corpus;approve(app)
    a=KnowledgeGuidance(app.state.sessions).generate(query(**changes))
    assert a['support']=='OUT_OF_SCOPE' and not a['citations']


def test_domain_filter_does_not_leak_other_law(corpus):
    app,_,_,_=corpus;approve(app)
    a=KnowledgeGuidance(app.state.sessions).generate(query(query_kind='PRODUCT_SPECIFIC',domains=['COSMETIC']))
    assert a['support']=='MISSING_EVIDENCE'


def test_conflict_and_restricted_metadata_block(corpus):
    app,_,_,doc=corpus;approve(app,conflict=True)
    engine=KnowledgeGuidance(app.state.sessions)
    assert not engine.generate(query())['citations']
    approve(app,conflict=False)
    with app.state.sessions() as db:
        d=db.get(SourceDocument,doc['document_id']);d.metadata_json={**d.metadata_json,'access':'RESTRICTED'};db.commit()
    assert not engine.generate(query())['citations']


def test_eligibility_before_candidate_budget(corpus,monkeypatch):
    app,_,_,doc=corpus;approved=approve(app)
    # More unapproved matches than the candidate cap must not hide approved evidence.
    with app.state.sessions() as db:
        for i in range(5):db.add(Passage(document_id=doc['document_id'],page=2,text=CONTENT,sha256=sha(CONTENT.encode()),review={}))
        db.commit()
        monkeypatch.setattr('app.retrieval.MAX_CANDIDATES',2)
        assert search(db,'knowledge','IN',date.today().isoformat())[0]['passage_id']==approved
        with pytest.raises(RetrievalCapacityError):search(db,'knowledge','IN',date.today().isoformat(),False)


def test_stopwords_do_not_create_spurious_answer(corpus):
    app,_,_,_=corpus;approve(app)
    assert not KnowledgeGuidance(app.state.sessions).generate(query(question='what is the'))['citations']


def test_unknown_query_does_not_invent_authority(corpus):
    app,_,_,_=corpus;approve(app)
    assert not KnowledgeGuidance(app.state.sessions).generate(query(question='xylophonic extraterrestrials'))['citations']


def test_revoked_evidence_invalidates_saved_answer_and_exports(corpus):
    app,c,_,_=corpus;approve(app)
    case=c.post('/api/v1/cases',json={'title':'Synthetic retrieval case','query_kind':'GENERAL_INFORMATION',
        'jurisdiction':query()['jurisdiction'],'as_of_date':date.today().isoformat(),
        'consent':{'accepted':True,'notice_version':'case-notice-v1'}}).json()
    base='/api/v1/cases/'+case['id']
    headers={'Idempotency-Key':'knowledge-test-1'}
    body={'question':'traditional knowledge'}
    r=c.post(base+'/guidance',json=body,headers=headers)
    assert r.status_code==200,r.text
    answer=r.json();assert not answer['stale']
    export=c.post(base+'/exports').json()
    approve(app,approved=False)
    assert c.get('/api/v1/answers/'+answer['id']).json()['stale']
    assert c.get('/api/v1/answers/'+answer['id']+'/citations').json()['stale']
    assert c.get('/api/v1/answers/'+answer['id']+'/events').status_code==409
    assert c.post(base+'/guidance',json=body,headers=headers).status_code==409
    assert c.get('/api/v1/exports/'+export['id']).status_code==409
    fresh=c.post(base+'/exports').json()
    assert c.get('/api/v1/exports/'+fresh['id']).status_code==200


def test_supersession_invalidates_prior_quotes(corpus):
    app,_,_,_=corpus;approve(app)
    a=KnowledgeGuidance(app.state.sessions).generate(query())
    with app.state.sessions() as db:
        persist(db,SOURCE,b'%PDF-new',SOURCE['url'],[{'page':1,'text':CONTENT+' Later edition.'}]);db.commit()
        assert 'EVIDENCE_NOT_CURRENTLY_APPROVED' in verify_answer(db,a)


def test_upstream_response_is_bounded(monkeypatch):
    @contextmanager
    def stream(*args,**kwargs):
        yield httpx.Response(200,content=b'x'*100,request=httpx.Request('POST','https://service.example'))
    monkeypatch.setattr(httpx,'stream',stream)
    with pytest.raises(ValueError,match='byte limit'):bounded_post('https://service.example',{},'secret',5,10)


def test_verification_and_coverage_endpoints(corpus):
    app,c,_,_=corpus;approve(app)
    a=KnowledgeGuidance(app.state.sessions).generate(query())
    assert c.post('/api/v1/corpus/verify',json=a).json()['valid']
    assert c.get('/api/v1/corpus/status').json()['coverage']=='SEED_CORPUS_INCOMPLETE'


def test_partial_scanned_pdf_is_not_silently_indexed(corpus):
    app,_,_,_=corpus
    with app.state.sessions() as db:
        with pytest.raises(ValueError,match='OCR/manual review'):
            persist(db,{**SOURCE,'id':'scanned'},b'%PDF-scanned',SOURCE['url'],
                    [{'page':1,'text':CONTENT},{'page':2,'text':''}])
