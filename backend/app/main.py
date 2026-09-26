import json
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import create_engine, event, select, delete, text
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .hardening import RequestGuard
from .corpus_api import router as corpus_router, ExtractiveGuidance
from .retrieval import verify_answer, RetrievalCapacityError
from .hosted_guidance import HostedGuidance
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from pydantic import ValidationError
from .config import Settings
from .models import Base, Case, Snapshot, Artifact, Event, now
from .schemas import (Principal, CreateCase, PatchCase, Answers, Guidance, GeneralGuidance,
                      Escalate, Review, ActionUpdate, SearchRecord, GuidanceAnswer,
                      CaseResponse, ArtifactResponse, PassportResponse)
from .integrations import identity, GuidanceClient
from .domain import (RULESET, PORTALS, DISCLAIMER, classify, clarify, services, checklist,
                     context, digest, route_domains, contradictions)


def create_app(settings=None, guidance_client=None):
    settings=settings or Settings()
    settings.validate()
    engine=create_engine(settings.database_url, connect_args={'check_same_thread':False} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
    if settings.database_url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_constraints(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=5000')
    sessions=sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_):
        # Migrations are explicit; startup never silently mutates production schema.
        yield
        engine.dispose()

    app=FastAPI(title='AYUNEX Backend',version='1.1.0',description=DISCLAIMER, lifespan=lifespan,docs_url=None if settings.environment=='production' else '/docs',redoc_url=None if settings.environment=='production' else '/redoc',openapi_url=None if settings.environment=='production' else '/openapi.json')
    app.state.settings=settings
    app.state.engine=engine
    app.state.sessions=sessions
    app.state.guidance=guidance_client or (HostedGuidance(sessions,settings) if settings.guidance_mode=='hosted' else ExtractiveGuidance(sessions,allow_source_checked=settings.environment!='production') if settings.guidance_mode=='corpus' else GuidanceClient(settings))
    app.add_middleware(RequestGuard,settings=settings)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=settings.allowed_hosts)
    app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Authorization','Content-Type','Idempotency-Key','X-CSRF-Protection'],allow_credentials=True)

    @app.middleware('http')
    async def security_headers(request, call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']='camera=(), microphone=(self), geolocation=()'
        if settings.environment=='production':
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
            response.headers['Referrer-Policy']='no-referrer'
        return response

    @app.exception_handler(StaleDataError)
    @app.exception_handler(IntegrityError)
    async def conflict_handler(_, __):
        return JSONResponse(status_code=409, content={'detail':'Concurrent change or duplicate request. Reload and retry.'})

    @app.exception_handler(Exception)
    async def server_error(request, error):
        return JSONResponse(status_code=500,content={'detail':'Internal service error','request_id':request.scope.get('request_id')},headers={'Cache-Control':'no-store'})

    @app.exception_handler(RetrievalCapacityError)
    async def retrieval_capacity(_, error):
        return JSONResponse(status_code=422,content={'detail':str(error)})

    def database():
        with sessions() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    DB=Annotated[Session,Depends(database)]
    User=Annotated[Principal,Depends(identity)]
    app.include_router(corpus_router(database))
    from .module_d import module_d_router, init_module_d_tables
    if settings.environment!='production':init_module_d_tables(engine)
    app.include_router(module_d_router(sessions, settings, identity))
    from .accounts import accounts_router
    app.include_router(accounts_router(sessions,settings))

    @app.get('/health/readiness')
    def readiness():
        try:
            with sessions() as db:
                version=db.execute(text('SELECT version_num FROM alembic_version')).scalar()
                if version!='0006':raise ValueError('Migrations pending')
            if settings.redis_url:
                from redis import Redis
                with Redis.from_url(settings.redis_url,socket_timeout=2,socket_connect_timeout=2) as cache:
                    cache.ping()
            return {'ready':True,'schema':version,'guidance_mode':settings.guidance_mode}
        except Exception:
            return JSONResponse(status_code=503,content={'ready':False,'reason':'Database, migrations or shared limiter unavailable'})
    app.state.readiness=readiness

    def scoped(db, principal, case_id, write=False):
        case=db.get(Case,case_id)
        if not case or case.tenant!=principal.tenant:
            raise HTTPException(404,'Case not found')
        allowed=principal.role=='administrator' or (case.owner==principal.subject and principal.role=='user')
        if not write and principal.role=='facilitator':
            allowed=any(a.payload.get('active') and a.context_hash==context(case) for a in db.scalars(select(Artifact).where(Artifact.case_id==case.id,Artifact.kind=='escalation')))
        if not allowed:
            raise HTTPException(403,'Case permission denied')
        return case

    def revision(case, expected):
        if expected!=case.revision:
            raise HTTPException(409, {'message':'Stale case revision','current_revision':case.revision})

    def audit(db, user, case, action, details=None):
        case.updated_at=now()
        db.add(Event(case_id=case.id,tenant=user.tenant,actor=user.subject,action=action,payload=details or {}))
        db.flush()

    def view(case):
        return {'id':case.id,'title':case.title,'status':case.status,'query_kind':case.query_kind,'jurisdiction':case.jurisdiction,'as_of_date':case.as_of,'passport_version':case.passport_version,'revision':case.revision,'created_at':case.created_at,'updated_at':case.updated_at,'context_hash':context(case)}

    def evidence_stale(payload):
        mode=(payload.get('retrieval_trace') or {}).get('mode')
        if mode in {'LOCAL_EXTRACTIVE','HOSTED_RAG'}:
            with sessions() as evidence_db:
                return bool(verify_answer(evidence_db,payload,exact_quotes=mode=='LOCAL_EXTRACTIVE'))
        # Recursively inspect evidence embedded in shared packets and exports.
        return any(evidence_stale(p) for p in payload.get('answers',[])) or any(evidence_stale(r.get('payload',{})) for r in payload.get('records',[]) if not r.get('stale'))

    def stale(record,case):
        return record.context_hash!=context(case) or evidence_stale(record.payload)

    def artifact_view(artifact, case):
        return {'id':artifact.id,'kind':artifact.kind,'context_hash':artifact.context_hash,'stale':stale(artifact,case),'created_at':artifact.created_at,'payload':artifact.payload,'case_revision':case.revision}

    def artifact(db,user,artifact_id,kind,write=False):
        record=db.get(Artifact,artifact_id)
        if not record or record.kind!=kind:
            raise HTTPException(404,'Record not found')
        case=scoped(db,user,record.case_id,write)
        if user.role=='facilitator' and (record.context_hash!=context(case) or kind not in {'classification','answer','escalation'} or (kind=='escalation' and not record.payload.get('active'))):
            raise HTTPException(403,'Sharing consent covers current facts/evidence only')
        return record,case

    def save_artifact(db,user,case,kind,payload,idem=None,request_hash=None):
        record=Artifact(case_id=case.id,kind=kind,context_hash=context(case),payload=payload,idempotency_key=idem,request_hash=request_hash)
        db.add(record)
        audit(db,user,case,kind+'.created')
        return record

    def deactivate_sharing(db,case):
        for record in db.scalars(select(Artifact).where(Artifact.case_id==case.id,Artifact.kind=='escalation')):
            record.payload={**record.payload,'active':False,'withdrawn_reason':'Context changed or consent withdrawn'}

    @app.get('/health')
    def health():
        return {'service':'AYUNEX Module B','status':'ok','rules_reviewed':False,'identity_configured':bool(settings.identity_url),'guidance_configured':bool(settings.guidance_url),'environment':settings.environment}

    @app.get('/api/v1/me')
    def me(user:User,db:DB):
        from .models import Account
        account=db.get(Account,user.subject)
        profile=user.model_dump()
        if account and account.tenant==user.tenant:
            profile.update(email=account.email,display_name=account.display_name or account.email.split('@')[0])
        return profile

    @app.post('/api/v1/cases',status_code=201,response_model=CaseResponse)
    def create_case(body:CreateCase,db:DB,user:User):
        if user.role not in {'user','administrator'}:
            raise HTTPException(403,'Role cannot create cases')
        case=Case(title=body.title,tenant=user.tenant,owner=user.subject,query_kind=body.query_kind,jurisdiction=body.jurisdiction.model_dump(),as_of=body.as_of_date.isoformat(),passport={'facts':{},'ingredients':[]},consent={**body.consent.model_dump(),'recorded_at':now().isoformat(),'actor':user.subject})
        db.add(case);db.flush();audit(db,user,case,'case.created')
        return view(case)

    @app.get('/api/v1/cases',response_model=list[CaseResponse])
    def list_cases(db:DB,user:User,limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),archived:bool=False):
        if user.role not in {'user','administrator'}:
            raise HTTPException(403,'Use the role-specific review/audit API')
        query=select(Case).where(Case.tenant==user.tenant)
        if user.role!='administrator':query=query.where(Case.owner==user.subject)
        if not archived:query=query.where(Case.status!='Archived')
        return [view(c) for c in db.scalars(query.order_by(Case.created_at.desc(),Case.id).limit(limit).offset(offset))]

    @app.get('/api/v1/cases/{case_id}',response_model=CaseResponse)
    def get_case(case_id:str,db:DB,user:User):
        return view(scoped(db,user,case_id))

    @app.patch('/api/v1/cases/{case_id}',response_model=CaseResponse)
    def patch_case(case_id:str,body:PatchCase,db:DB,user:User):
        case=scoped(db,user,case_id,True);revision(case,body.expected_revision)
        old=context(case)
        if body.title is not None:case.title=body.title
        if body.jurisdiction:case.jurisdiction=body.jurisdiction.model_dump()
        if body.as_of_date:case.as_of=body.as_of_date.isoformat()
        if old!=context(case):
            case.status='Needs information';deactivate_sharing(db,case)
        if body.archived is not None:case.status='Archived' if body.archived else 'Needs information'
        audit(db,user,case,'case.updated',{'context_invalidated':old!=context(case)})
        return view(case)

    @app.delete('/api/v1/cases/{case_id}',status_code=204)
    def delete_case(case_id:str,db:DB,user:User,expected_revision:int=Query(ge=1)):
        case=scoped(db,user,case_id,True);revision(case,expected_revision)
        # FK cascades remove all snapshots, answers, exports and local outbox records.
        db.delete(case);db.flush()
        return Response(status_code=204)

    @app.get('/api/v1/cases/{case_id}/passport',response_model=PassportResponse)
    def get_passport(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id)
        return {'passport':case.passport,'version':case.passport_version,'revision':case.revision,'conflicts':contradictions(case.passport)}

    @app.post('/api/v1/cases/{case_id}/passport/answers',response_model=PassportResponse)
    def passport_answers(case_id:str,body:Answers,db:DB,user:User):
        case=scoped(db,user,case_id,True);revision(case,body.expected_revision)
        if case.query_kind=='GENERAL_INFORMATION':raise HTTPException(409,'General questions bypass Passport')
        if any(f.provenance=='facilitator-confirmed' for f in body.passport.facts.values()) and user.role!='administrator':
            raise HTTPException(403,'User cannot claim facilitator provenance')
        normalized=body.passport.model_dump(mode='json')
        if normalized!=case.passport:
            case.passport=normalized;case.passport_version+=1;case.status='Needs information'
            db.add(Snapshot(case_id=case.id,version=case.passport_version,payload=normalized))
            deactivate_sharing(db,case);audit(db,user,case,'passport.versioned',{'version':case.passport_version})
        return {'passport':case.passport,'version':case.passport_version,'revision':case.revision,'conflicts':contradictions(case.passport)}

    @app.get('/api/v1/cases/{case_id}/passport/versions')
    def passport_versions(case_id:str,db:DB,user:User):
        scoped(db,user,case_id,True)
        return [{'id':s.id,'version':s.version,'passport':s.payload,'created_at':s.created_at} for s in db.scalars(select(Snapshot).where(Snapshot.case_id==case_id).order_by(Snapshot.version.desc()).limit(100))]

    @app.post('/api/v1/cases/{case_id}/classify')
    def run_classify(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id,True)
        result=classify(case.passport,case.jurisdiction,case.as_of,case.query_kind)
        result['escalation_recommendation']={'required':result['review_required'],'sharing_consent_required':True,'reason':'Unvalidated rules, unresolved evidence or unsupported context','question':'Please review the product route, origin and evidence gaps.'}
        record=save_artifact(db,user,case,'classification',result)
        return artifact_view(record,case)

    @app.get('/api/v1/classifications/{run_id}')
    def classification(run_id:str,db:DB,user:User):
        record,case=artifact(db,user,run_id,'classification')
        return artifact_view(record,case)

    @app.post('/api/v1/cases/{case_id}/clarifications')
    def clarifications(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id,True)
        result=clarify(case.passport,classify(case.passport,case.jurisdiction,case.as_of,case.query_kind))
        record=save_artifact(db,user,case,'clarification',result)
        return artifact_view(record,case)

    @app.get('/api/v1/cases/{case_id}/domains')
    def domains(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id)
        return services(case.passport,case.jurisdiction,case.as_of)

    @app.get('/api/v1/rulesets')
    def rulesets(user:User):
        return RULESET

    @app.get('/api/v1/portals')
    def portals(user:User):
        return {'records':PORTALS,'status':'DIRECTORY_ONLY_NOT_VERIFIED_CITATIONS','checked_at':None,'forms':[]}

    def verified_guidance(payload):
        try:
            result=GuidanceAnswer.model_validate(app.state.guidance.generate(payload))
        except (ValueError,ValidationError):
            raise HTTPException(502,'Module C returned an invalid evidence envelope') from None
        if result.context_hash!=payload['context_hash'] or result.request_id!=payload['request_id'] or result.jurisdiction.model_dump()!=payload['jurisdiction'] or result.as_of_date.isoformat()!=payload['as_of_date']:
            raise HTTPException(502,'Guidance context mismatch')
        return result.model_dump(mode='json')

    @app.post('/api/v1/cases/{case_id}/guidance')
    def case_guidance(case_id:str,body:Guidance,db:DB,user:User,idempotency_key:Annotated[str,Header(min_length=8,max_length=128)]):
        case=scoped(db,user,case_id,True)
        require_hosted_consent(user,body.allow_hosted_processing)
        fingerprint=digest(body.model_dump())
        cached=db.scalar(select(Artifact).where(Artifact.case_id==case.id,Artifact.kind=='answer',Artifact.idempotency_key==idempotency_key))
        if cached:
            if cached.request_hash!=fingerprint or cached.context_hash!=context(case):raise HTTPException(409,'Idempotency key belongs to a different request/context')
            if evidence_stale(cached.payload):raise HTTPException(409,'Evidence revoked or expired; retrieve again using a new idempotency key')
            return artifact_view(cached,case)
        original_context=context(case)
        unconfirmed=[k for k,f in case.passport.get('facts',{}).items() if f['provenance']=='extracted' and not f['confirmed'] and not f['unknown']]
        if unconfirmed:raise HTTPException(409,{'message':'Confirm extracted facts first','facts':unconfirmed})
        classification_id=str(uuid4()) if case.query_kind=='PRODUCT_SPECIFIC' else None
        snapshot_id=db.scalar(select(Snapshot.id).where(Snapshot.case_id==case.id,Snapshot.version==case.passport_version))
        payload={'request_id':str(uuid4()),'case_id':case.id,'query_kind':case.query_kind,'passport_version_id':snapshot_id,'classification_run_id':classification_id,'passport':case.passport,'jurisdiction':case.jurisdiction,'domains':route_domains(case.passport,case.jurisdiction),'as_of_date':case.as_of,'allowed_access_classes':['PUBLIC'],'context_hash':original_context,**body.model_dump()}
        result=verified_guidance(payload)
        db.refresh(case)
        if context(case)!=original_context:raise HTTPException(409,'Case changed during guidance; stale answer discarded')
        if classification_id:
            db.add(Artifact(id=classification_id,case_id=case.id,kind='classification',context_hash=original_context,payload=classify(case.passport,case.jurisdiction,case.as_of)))
        record=save_artifact(db,user,case,'answer',result,idempotency_key,fingerprint)
        case.status='Guidance ready';db.flush()
        return artifact_view(record,case)

    @app.post('/api/v1/guidance',response_model=GuidanceAnswer)
    def general_guidance(body:GeneralGuidance,user:User):
        require_hosted_consent(user,body.allow_hosted_processing)
        payload={**body.model_dump(mode='json'),'request_id':str(uuid4()),'query_kind':'GENERAL_INFORMATION','case_id':None,'passport_version_id':None,'classification_run_id':None,'allowed_access_classes':['PUBLIC'],'domains':route_domains({},body.jurisdiction.model_dump())}
        payload['context_hash']=digest(body.model_dump(mode='json'))
        return verified_guidance(payload)

    def require_hosted_consent(user,requested):
        if not requested:return
        with sessions() as consent_db:
            granted=consent_db.execute(text("SELECT id FROM platform_consents WHERE tenant=:tenant AND subject=:subject AND purpose='hosted_ai_processing' AND status='GRANTED' LIMIT 1"),{'tenant':user.tenant,'subject':user.subject}).first()
            if not granted:raise HTTPException(403,'Record explicit hosted_ai_processing consent before requesting AI processing')

    @app.get('/api/v1/answers/{answer_id}')
    def answer(answer_id:str,db:DB,user:User):
        record,case=artifact(db,user,answer_id,'answer')
        return artifact_view(record,case)

    @app.get('/api/v1/answers/{answer_id}/citations')
    def citations(answer_id:str,db:DB,user:User):
        record,case=artifact(db,user,answer_id,'answer')
        return {'citations':record.payload['citations'],'stale':stale(record,case)}

    @app.get('/api/v1/answers/{answer_id}/events')
    def answer_events(answer_id:str,db:DB,user:User):
        record,case=artifact(db,user,answer_id,'answer')
        if stale(record,case):raise HTTPException(409,'Cannot stream stale answer')
        events=[{'event_type':'progress','payload':{'message':'Validated answer ready'}}]
        events += [{'event_type':'section_verified','payload':s} for s in record.payload['sections'] if s['support']=='SUPPORTED_IN_SCOPE']
        events.append({'event_type':'answer_complete','payload':record.payload})
        data=''.join('data: '+json.dumps({'run_id':record.id,'sequence':i+1,**e})+'\n\n' for i,e in enumerate(events))
        return StreamingResponse(iter([data]),media_type='text/event-stream')

    @app.post('/api/v1/cases/{case_id}/checklists')
    def create_checklist(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id,True)
        record=save_artifact(db,user,case,'checklist',{'items':checklist(case.passport,case.jurisdiction)})
        return artifact_view(record,case)

    @app.patch('/api/v1/checklists/{checklist_id}/items/{item_id}')
    def update_checklist(checklist_id:str,item_id:str,body:ActionUpdate,db:DB,user:User):
        record,case=artifact(db,user,checklist_id,'checklist',True);revision(case,body.expected_revision)
        if record.context_hash!=context(case):raise HTTPException(409,'Checklist is stale')
        if not any(i['id']==item_id for i in record.payload['items']):raise HTTPException(404,'Item not found')
        record.payload={'items':[{**i,'status':body.status} if i['id']==item_id else i for i in record.payload['items']]}
        audit(db,user,case,'checklist.updated')
        return artifact_view(record,case)

    @app.post('/api/v1/cases/{case_id}/search-records')
    def search_record(case_id:str,body:SearchRecord,db:DB,user:User):
        case=scoped(db,user,case_id,True);revision(case,body.expected_revision)
        return artifact_view(save_artifact(db,user,case,'search',{'record':body.model_dump(exclude={'expected_revision'}),'reviewed_by':user.subject,'authoritative_verification':False}),case)

    @app.post('/api/v1/cases/{case_id}/escalations')
    def escalate(case_id:str,body:Escalate,db:DB,user:User):
        case=scoped(db,user,case_id,True);revision(case,body.expected_revision)
        classification=classify(case.passport,case.jurisdiction,case.as_of,case.query_kind)
        current_answers=[a.payload for a in db.scalars(select(Artifact).where(Artifact.case_id==case.id,Artifact.kind=='answer',Artifact.context_hash==context(case))) if not evidence_stale(a.payload)]
        payload={'active':True,'question':body.question,'scope':body.sharing_scope,'consent_version':body.consent_version,'consented_at':now().isoformat(),'consented_by':user.subject,'passport':case.passport,'passport_version':case.passport_version,'jurisdiction':case.jurisdiction,'as_of_date':case.as_of,'classification':classification,'answers':current_answers,'comments':[],'external_delivery':'NOT_SENT','status':'Under human review'}
        record=save_artifact(db,user,case,'escalation',payload);case.status='Under human review';db.flush()
        return artifact_view(record,case)

    @app.get('/api/v1/facilitator/queue')
    def queue(db:DB,user:User):
        if user.role not in {'facilitator','administrator'}:raise HTTPException(403,'Facilitator role required')
        rows=db.execute(select(Artifact,Case).join(Case,Case.id==Artifact.case_id).where(Case.tenant==user.tenant,Artifact.kind=='escalation').order_by(Artifact.created_at.desc()).limit(100))
        return [artifact_view(a,c) for a,c in rows if a.payload.get('active') and a.context_hash==context(c)]

    @app.patch('/api/v1/escalations/{escalation_id}')
    def review(escalation_id:str,body:Review,db:DB,user:User):
        if user.role not in {'facilitator','administrator'}:raise HTTPException(403,'Facilitator role required')
        record,case=artifact(db,user,escalation_id,'escalation');revision(case,body.expected_revision)
        if not record.payload.get('active') or stale(record,case):raise HTTPException(409,'Consent withdrawn, case changed or evidence expired')
        record.payload={**record.payload,'status':body.status,'comments':record.payload['comments']+[{'actor':user.subject,'at':now().isoformat(),'text':body.comment}]}
        case.status=body.status;audit(db,user,case,'escalation.reviewed')
        return artifact_view(record,case)

    @app.delete('/api/v1/escalations/{escalation_id}')
    def withdraw(escalation_id:str,db:DB,user:User,expected_revision:int=Query(ge=1)):
        record,case=artifact(db,user,escalation_id,'escalation',True);revision(case,expected_revision)
        record.payload={**record.payload,'active':False,'withdrawn_at':now().isoformat()}
        case.status='Needs information';audit(db,user,case,'escalation.withdrawn')
        return artifact_view(record,case)

    @app.post('/api/v1/cases/{case_id}/exports')
    def export_case(case_id:str,db:DB,user:User):
        case=scoped(db,user,case_id,True)
        records=list(db.scalars(select(Artifact).where(Artifact.case_id==case.id,Artifact.kind!='export').order_by(Artifact.created_at)))
        payload={'format':'ayunex-case-v1','disclaimer':DISCLAIMER,'case':{**view(case),'created_at':case.created_at.isoformat(),'updated_at':case.updated_at.isoformat()},'passport':case.passport,'records':[{'id':a.id,'kind':a.kind,'stale':stale(a,case),'payload':a.payload} for a in records]}
        return artifact_view(save_artifact(db,user,case,'export',payload),case)

    @app.get('/api/v1/exports/{export_id}')
    def get_export(export_id:str,db:DB,user:User):
        record,case=artifact(db,user,export_id,'export',True)
        if stale(record,case):raise HTTPException(409,'Export is stale; regenerate it from the current case and evidence')
        return JSONResponse(record.payload,headers={'Content-Disposition':f'attachment; filename="ayunex-{case.id}.json"'})

    @app.delete('/api/v1/exports/{export_id}',status_code=204)
    def delete_export(export_id:str,db:DB,user:User):
        record,case=artifact(db,user,export_id,'export',True)
        db.delete(record);audit(db,user,case,'export.deleted')
        return Response(status_code=204)

    @app.get('/api/v1/cases/{case_id}/activity')
    def activity(case_id:str,db:DB,user:User):
        if user.role=='auditor':
            case=db.get(Case,case_id)
            if not case or case.tenant!=user.tenant:raise HTTPException(404,'Case not found')
        else:scoped(db,user,case_id,True)
        return [{'id':e.id,'action':e.action,'actor':e.actor,'at':e.created_at,'details':e.payload} for e in db.scalars(select(Event).where(Event.case_id==case_id).order_by(Event.created_at.desc()).limit(100))]

    @app.get('/api/v1/cases/{case_id}/artifacts')
    def list_artifacts(case_id:str,db:DB,user:User,limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0)):
        case=scoped(db,user,case_id,True)
        records=db.scalars(select(Artifact).where(Artifact.case_id==case_id).order_by(Artifact.created_at.desc(),Artifact.id).offset(offset).limit(limit))
        return [artifact_view(record,case) for record in records]

    # Production SPA static file serving
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    frontend_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if frontend_dist.is_dir() and (frontend_dist / 'index.html').is_file():
        assets_dir = frontend_dist / 'assets'
        if assets_dir.is_dir():
            app.mount('/assets', StaticFiles(directory=str(assets_dir)), name='assets')

        @app.get('/{full_path:path}')
        async def serve_spa(full_path: str):
            if full_path.startswith(('api/', 'health', 'docs', 'redoc', 'openapi.json', 'readyz', 'healthz')):
                raise HTTPException(status_code=404, detail="Not Found")
            file_candidate = (frontend_dist / full_path).resolve()
            if not file_candidate.is_relative_to(frontend_dist.resolve()):
                raise HTTPException(status_code=404,detail='Not Found')
            if file_candidate.is_file():
                return FileResponse(file_candidate)
            return FileResponse(frontend_dist / 'index.html')

    return app


app=create_app()
