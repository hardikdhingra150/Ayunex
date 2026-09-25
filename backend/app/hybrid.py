"""Bounded exact-vector baseline with RRF; no approximate/vector extension required.

Metadata filtering occurs in SQL before vectors are loaded. Suitable for the
small pilot corpus; fail closed above 5000 eligible vectors. Move to pgvector
after scale/recall benchmarking rather than pretending this is an ANN index.
"""
from datetime import date
from sqlalchemy import select,or_
from .models import Passage,SourceDocument,PassageEmbedding
from .retrieval import search,eligible,RetrievalCapacityError
from .ai_provider import vector,ProviderError


def eligible_rows(country,as_of,domains=None):
    r=Passage.review
    stmt=select(Passage,SourceDocument).join(SourceDocument).where(
        Passage.active.is_(True),SourceDocument.active.is_(True),SourceDocument.country==country,
        SourceDocument.metadata_json['access'].as_string()=='PUBLIC',r['approved'].as_boolean().is_(True),
        or_(r['conflict'].as_boolean().is_(None),r['conflict'].as_boolean().is_(False)),
        or_(Passage.extraction['quarantined'].as_boolean().is_(None),Passage.extraction['quarantined'].as_boolean().is_(False)),
        r['effective_from'].as_string()<=as_of,
        or_(r['effective_to'].as_string().is_(None),r['effective_to'].as_string()>as_of),
        r['review_valid_until'].as_string()>=max(as_of,date.today().isoformat()))
    if domains is not None:stmt=stmt.where(SourceDocument.domain.in_(domains))
    return stmt


def result(p,d,as_of,score):
    return {'passage_id':p.id,'passage_sha256':p.sha256,'document_id':d.id,'title':d.title,
            'authority':d.authority,'url':d.url,'page':p.page,'text':p.text,'version':d.sha256,
            'reviewed':eligible(p,d,as_of),'review':p.review,'score':score,
            'retrieved_at':d.retrieved_at.isoformat(),'country':d.country,'domain':d.domain,
            'extraction':p.extraction,'review_revision':p.review_revision}


def retrieve(db,question,country,as_of,provider,domains=None,limit=8):
    lexical=search(db,question,country,as_of,domains=domains,limit=24)
    statement=eligible_rows(country,as_of,domains).add_columns(PassageEmbedding).join(PassageEmbedding,PassageEmbedding.passage_id==Passage.id).where(
        PassageEmbedding.model==provider.embedding_model,PassageEmbedding.text_sha256==Passage.sha256)
    rows=list(db.execute(statement.order_by(Passage.id).limit(5001)))
    if len(rows)>5000:raise RetrievalCapacityError('Eligible vector budget exceeded')
    if not rows:return lexical[:limit]
    q=vector(provider.embed([question])[0]);dense=[]
    for p,d,e in rows:
        v=vector(e.vector)
        if len(q)!=len(v):raise ProviderError('Index and query embedding dimensions differ; rebuild index')
        similarity=sum(a*b for a,b in zip(q,v))
        if similarity>0:dense.append(result(p,d,as_of,similarity))
    dense=sorted(dense,key=lambda h:(-h['score'],h['passage_id']))[:24]
    scores={};hits={}
    for ranking in (lexical,dense):
        for rank,hit in enumerate(ranking,1):
            pid=hit['passage_id'];hits[pid]=hit;scores[pid]=scores.get(pid,0)+1/(60+rank)
    return [{**hits[pid],'score':scores[pid]} for pid in sorted(scores,key=lambda x:(-scores[x],x))[:limit]]


def index_batch(db,provider,limit=16):
    today=date.today().isoformat()
    stmt=eligible_rows('IN',today).outerjoin(PassageEmbedding,
        (PassageEmbedding.passage_id==Passage.id)&(PassageEmbedding.model==provider.embedding_model)&(PassageEmbedding.text_sha256==Passage.sha256)).where(PassageEmbedding.passage_id.is_(None)).order_by(Passage.id).limit(limit)
    rows=list(db.execute(stmt))
    if not rows:return 0
    vectors=provider.embed([p.text for p,_ in rows])
    if len(vectors)!=len(rows):raise ProviderError('Missing embedding output')
    for (p,_),v in zip(rows,vectors):
        db.merge(PassageEmbedding(passage_id=p.id,model=provider.embedding_model,text_sha256=p.sha256,vector=vector(v)))
    return len(rows)
