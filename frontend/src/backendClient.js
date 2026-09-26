// Module B contract, explicitly opt-in. The existing demo remains mock-only.
// Keep bearer credentials in memory; never save them to localStorage.
export function defaultApiBase(){return typeof window==='undefined'?'http://127.0.0.1:8000':window.location.origin}
export function createBackendClient({baseUrl=defaultApiBase(),getToken=()=>'',cookieAuth=false,fetchImpl=fetch,timeoutMs=140000}){
 const base=new URL(baseUrl)
 if(base.protocol!=='https:'&&!['127.0.0.1','localhost'].includes(base.hostname))throw new Error('HTTPS required outside loopback')
 async function request(path,{method='GET',body,idempotencyKey,signal}={}){
  const token=await getToken()
  if(!token&&!cookieAuth)throw new Error('Module D identity or local development token required')
  const response=await fetchImpl(new URL('/api/v1'+path,base),{method,credentials:cookieAuth?'same-origin':'omit',headers:{...(token?{Authorization:'Bearer '+token}:{}),'X-CSRF-Protection':'1',...(body?{'Content-Type':'application/json'}:{}),...(idempotencyKey?{'Idempotency-Key':idempotencyKey}:{})},body:body?JSON.stringify(body):undefined,signal:signal?AbortSignal.any([signal,AbortSignal.timeout(timeoutMs)]):AbortSignal.timeout(timeoutMs)})
  if(!response.ok){const problem=await response.json().catch(()=>({}));const error=new Error(typeof problem.detail==='string'?problem.detail:'Backend request failed');error.status=response.status;error.details=problem.detail;throw error}
  return response.status===204?null:response.json().catch(()=>null)
 }
 const id=value=>encodeURIComponent(value)
 return {
  me:()=>request('/me'),cases:()=>request('/cases'),createCase:body=>request('/cases',{method:'POST',body}),
  getCase:caseId=>request('/cases/'+id(caseId)),
  patchCase:(caseId,body)=>request('/cases/'+id(caseId),{method:'PATCH',body}),
  deleteCase:(caseId,revision)=>request('/cases/'+id(caseId)+'?expected_revision='+Number(revision),{method:'DELETE'}),
  passport:caseId=>request('/cases/'+id(caseId)+'/passport'),
  savePassport:(caseId,passport,revision)=>request('/cases/'+id(caseId)+'/passport/answers',{method:'POST',body:{passport,expected_revision:revision}}),
  passportVersions:caseId=>request('/cases/'+id(caseId)+'/passport/versions'),
  classify:caseId=>request('/cases/'+id(caseId)+'/classify',{method:'POST'}),
  clarify:caseId=>request('/cases/'+id(caseId)+'/clarifications',{method:'POST'}),
  domains:caseId=>request('/cases/'+id(caseId)+'/domains'),
  guidance:(caseId,body,idempotencyKey,signal)=>request('/cases/'+id(caseId)+'/guidance',{method:'POST',body,idempotencyKey,signal}),
  ask:(body,signal)=>request('/guidance',{method:'POST',body,signal}),
  answerCitations:answerId=>request('/answers/'+id(answerId)+'/citations'),
  createChecklist:caseId=>request('/cases/'+id(caseId)+'/checklists',{method:'POST'}),
  updateChecklistItem:(checklistId,itemId,status,revision)=>request('/checklists/'+id(checklistId)+'/items/'+id(itemId),{method:'PATCH',body:{status,expected_revision:Number(revision)}}),
  escalate:(caseId,body)=>request('/cases/'+id(caseId)+'/escalations',{method:'POST',body}),
  reviewEscalation:(escalationId,comment,status,revision)=>request('/escalations/'+id(escalationId),{method:'PATCH',body:{comment,status,expected_revision:Number(revision)}}),
  withdrawEscalation:(escalationId,revision)=>request('/escalations/'+id(escalationId)+'?expected_revision='+Number(revision),{method:'DELETE'}),
  queue:()=>request('/facilitator/queue'),
  exportCase:caseId=>request('/cases/'+id(caseId)+'/exports',{method:'POST'}),
  getExport:exportId=>request('/exports/'+id(exportId)),
  deleteExport:exportId=>request('/exports/'+id(exportId),{method:'DELETE'}),
  activity:caseId=>request('/cases/'+id(caseId)+'/activity'),
  artifacts:caseId=>request('/cases/'+id(caseId)+'/artifacts'),
  recordConsent:(purpose,version='dpdp-v1',metadata={})=>request('/consent/record',{method:'POST',body:{purpose,notice_version:version,metadata}}),
  consentHistory:()=>request('/consent/history'),
  withdrawConsent:purpose=>request('/consent/withdraw',{method:'POST',body:{purpose}}),
  requestErasure:()=>request('/privacy/erasure',{method:'POST',body:{confirm_erasure:true}}),
  auditEvents:limit=>request('/audit/events'+(limit?'?limit='+limit:'')),
  verifyAudit:()=>request('/audit/verify'),
 }
}

export async function fetchSession(role='user',baseUrl=defaultApiBase()){
 if(role!=='user')throw new Error('Privileged roles require verified identity, not self-selection')
 const base=new URL(baseUrl)
 const res=await fetch(new URL('/api/v1/auth/session',base),{
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({role})
 })
 if(!res.ok)throw new Error('Failed to obtain session from server')
 return res.json()
}
