"""Typed, local Module C orchestration with mechanically verified quotations."""
from .retrieval import search, verify_answer, VERSION, RetrievalCapacityError
from .schemas import GuidanceAnswer
import re


class KnowledgeGuidance:
    def __init__(self, sessions,retriever=None,allow_source_checked=True):
        self.sessions = sessions
        self.retriever = retriever or search
        self.allow_source_checked=allow_source_checked

    def generate(self, payload):
        jurisdiction = payload['jurisdiction']
        reason = 'No currently approved evidence matched. This does not establish absence of law or prior art.'
        support = 'MISSING_EVIDENCE'
        hits = []
        trace = {'engine':VERSION,'mode':'LOCAL_EXTRACTIVE','steps':['VALIDATE_CONTEXT','PLAN'],
                 'repair_count':0,'translation':'NOT_PERFORMED','source_versions':[],
                 'evidence_ids':[],'verification':'NO_CLAIMS'}
        if jurisdiction['layer'] != 'NATIONAL' or jurisdiction.get('country') != 'IN':
            support = 'OUT_OF_SCOPE'
            reason = 'The local corpus supports India only; treaty and export regimes need separately curated evidence.'
        elif payload.get('original_language','en') != 'en':
            support = 'OUT_OF_SCOPE'
            reason = 'Reviewed Hindi retrieval and translation are not configured. Please use an English query; original citations are never silently translated.'
        elif 'PUBLIC' not in payload.get('allowed_access_classes', ['PUBLIC']):
            support = 'OUT_OF_SCOPE'
            reason = 'No permitted public evidence access for this request.'
        else:
            with self.sessions() as db:
                try:
                    trace['steps'].append('RETRIEVE_APPROVED')
                    # General information should not be incorrectly restricted by product-route defaults.
                    domains = payload.get('domains') if payload.get('query_kind') == 'PRODUCT_SPECIFIC' else None
                    hits = self.retriever(db,payload['question'],'IN',payload['as_of_date'],domains=domains)
                except RetrievalCapacityError:
                    reason = 'Too many eligible lexical candidates. Narrow the question; no truncated answer was produced.'
        # Diversify by immutable source version; keep at most two excerpts per document.
        # Prefer an explicitly requested statutory locator over overlapping broad
        # chunks; matching generic words must not pull in unrelated statutes.
        question=payload['question'].lower()
        if 'patent' in question:
            hits=[h for h in hits if h['domain']=='PATENT']
        locator=re.search(r'\bsection\s+(\d+)\s*\(\s*([a-z])\s*\)',question)
        if locator:
            target='section'+locator.group(1)+'('+locator.group(2)+')'
            exact=[h for h in hits if target in re.sub(r'\s+','',h['review'].get('provision','').lower())]
            if exact:hits=exact
        selected = []
        counts = {}
        for hit in hits:
            if not self.allow_source_checked and hit['review'].get('review_status','VERIFIED')!='VERIFIED':continue
            if counts.get(hit['document_id'],0) >= 2: continue
            selected.append(hit); counts[hit['document_id']] = counts.get(hit['document_id'],0)+1
            if len(selected) == 3: break
        citations = []
        claims = []
        for hit in selected:
            review = hit['review']; cid = hit['passage_id']
            citations.append({'id':cid,'authority':hit['authority'],'title':hit['title'],
                'url':hit['url'],'provision':review['provision']+'; PDF page '+str(hit['page']),
                'excerpt':hit['text'],'version':hit['version'],'jurisdiction':jurisdiction,
                'effective_from':review['effective_from'],'effective_to':review.get('effective_to'),
                'retrieved_at':hit['retrieved_at'],'review_status':review.get('review_status','VERIFIED'),'access_class':'PUBLIC'})
            claims.append({'id':'quote-'+cid,'text':hit['text'],'jurisdiction':jurisdiction,'citation_ids':[cid]})
        if selected:
            support = 'REVIEW_REQUIRED'
            reason = 'Original reviewed excerpts only. Conditions, exceptions and applicability require human judgment; no product-specific legal conclusion is made.'
            if any(c['review_status']=='SOURCE_TEXT_CHECKED' for c in citations):
                reason += ' PILOT: source text checked by an AI assistant against the official publication, not approved by a legal expert. Coverage is limited to the cited provision; current-law completeness is not certified.'
        trace['steps'] += ['BUILD_EVIDENCE_MATRIX','VERIFY_QUOTES']
        trace['source_versions'] = sorted({h['version'] for h in selected})
        trace['evidence_ids'] = [h['passage_id'] for h in selected]
        answer = {'request_id':payload['request_id'],'context_hash':payload['context_hash'],
                  'jurisdiction':jurisdiction,'as_of_date':payload['as_of_date'],'support':support,
                  'sections':[{'id':'source-extracts','title':'Original source excerpts — not legal advice',
                               'support':'SUPPORTED_IN_SCOPE' if selected else support,'claims':claims,'reason':reason}],
                  'citations':citations,'retrieval_trace':trace}
        # Re-read reviews after retrieval to detect revocation during this run.
        with self.sessions() as db:
            errors = verify_answer(db,answer)
        if errors:
            answer['support'] = 'MISSING_EVIDENCE'; answer['citations'] = []
            answer['sections'] = [{'id':'verification','title':'Evidence verification failed',
                                   'support':'MISSING_EVIDENCE','claims':[],
                                   'reason':'Evidence changed or failed verification; request fresh retrieval.'}]
            trace['verification'] = 'REJECTED'
        elif selected:
            trace['verification'] = 'EXACT_QUOTES_VERIFIED'
        trace['steps'].append('PUBLISH')
        return GuidanceAnswer.model_validate(answer).model_dump(mode='json')
