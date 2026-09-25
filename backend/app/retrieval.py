"""Module C lexical baseline. No model calls, translation, or legal inference.

Eligibility is applied in SQL before candidate limits. BM25 scores rank text,
not legal correctness. Oversized candidate sets fail closed rather than silently
searching a truncated subset. Dense retrieval is a later benchmarked adapter.
"""
from collections import Counter
from datetime import date
import math
import re
from sqlalchemy import select, or_
from .models import Passage, SourceDocument

VERSION = 'lexical-bm25-1.0'
MAX_CANDIDATES = 5000
STOP = set('a an the and or of to for in on is are was be can how what which my does do with this that about please'.split())


class RetrievalCapacityError(ValueError):
    pass


def tokens(text):
    return [t for t in re.findall(r'[\w\u0900-\u097f]+', text.casefold()) if t not in STOP and (len(t) > 1 or t.isdigit())]


def eligible(passage, doc, as_of):
    review = passage.review
    return bool(passage.active and not passage.extraction.get('quarantined') and doc.active and doc.metadata_json.get('access') == 'PUBLIC'
                and review.get('approved') and not review.get('conflict')
                and review.get('effective_from') and review['effective_from'] <= as_of
                and (not review.get('effective_to') or as_of < review['effective_to'])
                and review.get('review_valid_until', '') >= max(as_of, date.today().isoformat()))


def search(db, question, country, as_of, reviewed_only=True, limit=8, domains=None):
    date.fromisoformat(as_of)
    terms = list(dict.fromkeys(tokens(question)))[:32]
    if not terms:
        return []
    statement = select(Passage, SourceDocument).join(SourceDocument).where(
        SourceDocument.active.is_(True), Passage.active.is_(True),SourceDocument.country == country,
        SourceDocument.metadata_json['access'].as_string() == 'PUBLIC')
    if domains is not None:
        if not domains: return []
        statement = statement.where(SourceDocument.domain.in_(domains))
    if reviewed_only:
        review = Passage.review
        statement = statement.where(
            or_(Passage.extraction['quarantined'].as_boolean().is_(None),Passage.extraction['quarantined'].as_boolean().is_(False)),
            review['approved'].as_boolean().is_(True),
            or_(review['conflict'].as_boolean().is_(None), review['conflict'].as_boolean().is_(False)),
            review['effective_from'].as_string() <= as_of,
            or_(review['effective_to'].as_string().is_(None), review['effective_to'].as_string() > as_of),
            review['review_valid_until'].as_string() >= max(as_of, date.today().isoformat()))
    matches = [Passage.text.ilike('%'+t.replace('_', '\\_')+'%', escape='\\') for t in terms]
    matches += [Passage.review['provision'].as_string().ilike('%'+t.replace('_', '\\_')+'%', escape='\\') for t in terms]
    rows = list(db.execute(statement.where(or_(*matches)).order_by(Passage.id).limit(MAX_CANDIDATES+1)))
    if len(rows) > MAX_CANDIDATES:
        raise RetrievalCapacityError('Query exceeds lexical candidate budget; narrow the question or domain')
    bags = [Counter(tokens(p.text+' '+p.review.get('provision',''))) for p, _ in rows]
    average = sum(sum(b.values()) for b in bags) / max(1, len(bags))
    frequency = {t: sum(t in b for b in bags) for t in terms}
    results = []
    for (passage, doc), bag in zip(rows, bags):
        score = 0.0
        for term in terms:
            tf = bag[term]
            if not tf: continue
            idf = math.log(1+(len(rows)-frequency[term]+0.5)/(frequency[term]+0.5))
            score += idf * tf * 2.2 / (tf+1.2*(0.25+0.75*sum(bag.values())/max(average,1)))
        if score <= 0: continue
        results.append({'passage_id':passage.id,'passage_sha256':passage.sha256,
                        'document_id':doc.id,'title':doc.title,'authority':doc.authority,
                        'url':doc.url,'page':passage.page,'text':passage.text,
                        'version':doc.sha256,'reviewed':eligible(passage,doc,as_of),
                        'review':passage.review,'score':round(score,6),
                        'retrieved_at':doc.retrieved_at.isoformat(),'country':country,'domain':doc.domain,
                        'extraction':passage.extraction,'review_revision':passage.review_revision})
    return sorted(results,key=lambda r:(-r['score'],r['passage_id']))[:limit]


def verify_answer(db, answer,exact_quotes=True):
    """Exact quote verifier for LOCAL corpus answers; never an entailment model."""
    errors = []
    jurisdiction = answer['jurisdiction']
    citations = {c['id']: c for c in answer.get('citations', [])}
    for citation in citations.values():
        passage = db.get(Passage, citation['id'])
        doc = db.get(SourceDocument, passage.document_id) if passage else None
        if not passage or not doc:
            errors.append('UNKNOWN_PASSAGE'); continue
        if not eligible(passage, doc, answer['as_of_date']): errors.append('EVIDENCE_NOT_CURRENTLY_APPROVED')
        if jurisdiction.get('layer') != 'NATIONAL' or doc.country != jurisdiction.get('country'):
            errors.append('JURISDICTION_MISMATCH')
        expected = {'excerpt':passage.text,'version':doc.sha256,'url':doc.url,
                    'review_status':passage.review.get('review_status','VERIFIED'),
                    'title':doc.title,'authority':doc.authority,
                    'provision':passage.review.get('provision','')+'; PDF page '+str(passage.page),
                    'effective_from':passage.review.get('effective_from'),
                    'effective_to':passage.review.get('effective_to'), 'jurisdiction':jurisdiction}
        if any(citation.get(k) != v for k,v in expected.items()): errors.append('CITATION_CHANGED_OR_TAMPERED')
    for section in answer.get('sections', []) if exact_quotes else []:
        for claim in section['claims']:
            if not any(cid in citations and claim['text'] == citations[cid]['excerpt'] for cid in claim['citation_ids']):
                errors.append('NOT_AN_EXACT_REVIEWED_EXCERPT')
    return sorted(set(errors))
