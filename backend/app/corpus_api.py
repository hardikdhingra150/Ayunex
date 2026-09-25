from datetime import date
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from pydantic import Field,model_validator
from sqlalchemy import select,func,update
from .schemas import Strict,Principal,GuidanceAnswer
from .retrieval import verify_answer
from .integrations import identity
from .models import SourceDocument,Passage,CorpusReviewEvent,now
from .corpus import sources,search


class ReviewPassage(Strict):
    approved:bool
    expected_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    provision:str=Field(min_length=2,max_length=300)
    effective_from:date
    effective_to:date|None=None
    review_valid_until:date
    notes:str=Field(min_length=20,max_length=4000)
    conflict:bool=False
    expected_review_revision:int=Field(default=0,ge=0)

    @model_validator(mode='after')
    def intervals(self):
        if self.effective_to and self.effective_to<=self.effective_from:raise ValueError('Invalid effective interval')
        if self.review_valid_until<date.today():raise ValueError('Review freshness cannot already be expired')
        return self


def router(database):
    api=APIRouter(prefix='/api/v1/corpus',tags=['Official corpus'])
    User=Annotated[Principal,Depends(identity)]

    @api.get('/catalog')
    def catalog(user:User):return {'sources':sources(),'restricted_access':'NOT_GRANTED'}

    @api.get('/status')
    def status(request:Request,user:User,db=Depends(database)):
        from .hybrid import eligible_rows
        settings=request.app.state.settings
        return {'documents':db.scalar(select(func.count()).select_from(SourceDocument)),
                'passages':db.scalar(select(func.count()).select_from(Passage)),
                'active_passages':db.scalar(select(func.count()).select_from(Passage).where(Passage.active.is_(True))),
                'currently_eligible_passages':db.scalar(select(func.count()).select_from(eligible_rows('IN',date.today().isoformat()).subquery())),
                'approved_reviews':db.scalar(select(func.count()).select_from(Passage).where(Passage.review['approved'].as_boolean().is_(True))),
                'coverage':'SEED_CORPUS_INCOMPLETE','approval_is_not_legal_certification':True,
                'guidance':settings.guidance_mode,'dense_retrieval_configured':settings.guidance_mode=='hosted' and bool(settings.embedding_model) and settings.ai_provider!='groq',
                'translation':False,'hosted_request_permission_required':True}

    @api.post('/verify')
    def verify(body:GuidanceAnswer,user:User,db=Depends(database)):
        errors=verify_answer(db,body.model_dump(mode='json'))
        return {'valid':not errors,'errors':errors,'scope':'LOCAL_CORPUS_EXACT_QUOTES_ONLY','semantic_entailment_tested':False}

    @api.get('/documents')
    def documents(user:User,db=Depends(database),offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
        return [{'id':d.id,'title':d.title,'authority':d.authority,'url':d.url,'sha256':d.sha256,'active':d.active,'retrieved_at':d.retrieved_at,'metadata':d.metadata_json} for d in db.scalars(select(SourceDocument).order_by(SourceDocument.retrieved_at.desc()).offset(offset).limit(limit))]

    @api.get('/documents/{document_id}/passages')
    def passages(document_id:str,user:User,db=Depends(database),offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
        if user.role not in {'curator','administrator'}:raise HTTPException(403,'Curator role required')
        if not db.get(SourceDocument,document_id):raise HTTPException(404,'Document not found')
        return [{'id':p.id,'text':p.text,'page':p.page,'sha256':p.sha256,'active':p.active,
                 'extraction':p.extraction,'review':p.review,'review_revision':p.review_revision}
                for p in db.scalars(select(Passage).where(Passage.document_id==document_id).order_by(Passage.page,Passage.id).offset(offset).limit(limit))]

    @api.get('/passages/{passage_id}/reviews')
    def reviews(passage_id:str,user:User,db=Depends(database)):
        if user.role not in {'curator','administrator','auditor'}:raise HTTPException(403,'Review audit role required')
        return [{'id':e.id,'actor':e.actor,'at':e.created_at,'review':e.payload} for e in db.scalars(select(CorpusReviewEvent).where(CorpusReviewEvent.passage_id==passage_id).order_by(CorpusReviewEvent.created_at.desc()).limit(100))]

    @api.get('/search')
    def find(user:User,q:str=Query(min_length=3,max_length=1000),country:str=Query('IN',pattern=r'^[A-Z]{2}$'),as_of:date=Query(...),reviewed_only:bool=True,db=Depends(database)):
        return {'results':search(db,q,country,as_of.isoformat(),reviewed_only),'purpose':'SOURCE_DISCOVERY_NOT_LEGAL_ADVICE','unreviewed_material_must_not_support_answers':True}

    @api.patch('/passages/{passage_id}/review')
    def review(passage_id:str,body:ReviewPassage,user:User,db=Depends(database)):
        if user.role not in {'curator','administrator'}:raise HTTPException(403,'Verified curator role required')
        passage=db.get(Passage,passage_id)
        if not passage:raise HTTPException(404,'Passage not found')
        if passage.sha256!=body.expected_sha256:raise HTTPException(409,'Passage hash changed')
        if body.approved and (not passage.active or passage.extraction.get('quarantined')):raise HTTPException(409,'Inactive or quarantined parse must be corrected before approval')
        doc=db.get(SourceDocument,passage.document_id)
        if not doc.active:raise HTTPException(409,'Cannot approve superseded source')
        value={**body.model_dump(mode='json',exclude={'expected_review_revision'}),'reviewer':user.subject,'reviewed_at':now().isoformat()}
        changed=db.execute(update(Passage).where(Passage.id==passage_id,Passage.review_revision==body.expected_review_revision).values(review=value,review_revision=Passage.review_revision+1))
        if changed.rowcount!=1:raise HTTPException(409,'Another curator changed the review; reload before retrying')
        db.add(CorpusReviewEvent(passage_id=passage.id,actor=user.subject,payload=value));db.flush()
        return {'passage_id':passage.id,'review':value,'review_revision':body.expected_review_revision+1}
    return api


from .knowledge import KnowledgeGuidance

# Compatibility for the existing local adapter and clients.
ExtractiveGuidance = KnowledgeGuidance
