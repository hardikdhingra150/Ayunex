import { z } from 'zod'

export const scenarios=['ready','partial','missing_facts','missing_evidence','conflict','unsupported','restricted','translation_unavailable','timeout']
const contextSchema=z.object({id:z.string(),jurisdiction:z.enum(['IN','TREATY','US','EU']),asOf:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),facts:z.record(z.string(),z.unknown())})
export const contextKey=c=>JSON.stringify([c.id,c.jurisdiction,c.asOf,c.facts])
export function delay(ms,signal){return new Promise((resolve,reject)=>{if(signal?.aborted)return reject(new DOMException('Cancelled','AbortError'));const abort=()=>{clearTimeout(timer);reject(new DOMException('Cancelled','AbortError'))};const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve()},ms);signal?.addEventListener('abort',abort,{once:true})})}
export const sectionTitles=[['Product route','उत्पाद मार्ग'],['Immediate next actions','अगले कदम'],['IP opportunities','बौद्धिक संपदा'],['ABS and traditional knowledge','जैव संसाधन और पारंपरिक ज्ञान'],['Evidence checklist','प्रमाण सूची'],['Labelling and advertising','लेबल और विज्ञापन'],['Target market','लक्षित बाजार'],['Missing information','अनुपलब्ध जानकारी'],['Human review','विशेषज्ञ समीक्षा']]
export function fixtureFor(input,scenario='ready'){
 const c=contextSchema.parse(input)
 if(!scenarios.includes(scenario))throw new Error('Unknown mock scenario')
 const support={ready:'SUPPORTED_IN_SCOPE',partial:'REVIEW_REQUIRED',missing_facts:'MISSING_FACTS',missing_evidence:'MISSING_EVIDENCE',conflict:'CONFLICTING_SOURCES',unsupported:'OUT_OF_SCOPE',restricted:'MISSING_EVIDENCE',translation_unavailable:'REVIEW_REQUIRED'}[scenario]||'MISSING_EVIDENCE'
 const source={id:'fixture-protocol-1',authority:'Naut IQ fictional test corpus — NOT a legal authority',title:'UI verification fixture',locator:'TEST-ONLY §1',excerpt:'For this interface test, record product facts, preserve unknown fields, keep jurisdiction contexts separate, and refer unresolved questions for review.',version:'fixture-v1',jurisdiction:c.jurisdiction,effectiveFrom:null,effectiveTo:null,retrievedAt:new Date().toISOString(),asOf:c.asOf,reviewStatus:'Synthetic UI fixture only',url:null}
 return {mock:true,id:crypto.randomUUID(),contextKey:contextKey(c),jurisdiction:c.jurisdiction,asOf:c.asOf,support,scenario,ruleset:'fictional-ui-rules-v1',sources:scenario==='restricted'?[]:[source],sections:sectionTitles.map(([title,hi],i)=>({id:`section-${i}`,title,hi,support:scenario==='partial'&&i>2?'MISSING_EVIDENCE':support,verified:(scenario==='ready'||scenario==='translation_unavailable'||scenario==='partial'&&i<3),text:'Synthetic workflow example: record the product facts and unresolved questions before requesting review. No legal classification, clearance or patentability conclusion is made.',textHi:'कृत्रिम उदाहरण: समीक्षा से पहले उत्पाद के तथ्य और खुले प्रश्न दर्ज करें। यह कानूनी वर्गीकरण, अनुमति या पेटेंट-योग्यता का निष्कर्ष नहीं है।',citationIds:['fixture-protocol-1']})),assessments:['Regulatory','IP','ABS'].map(domain=>({domain,candidate:'UNRESOLVED — synthetic preview',conditions:[{name:'Intended use recorded',state:c.facts.use&&c.facts.use!=='Unknown'?'met':'unknown'},{name:'Authoritative evidence reviewed',state:'unknown'},{name:'Clearance established',state:'not_met'}]}))}
}
export async function* guidanceEvents(input,{scenario='ready',signal}={}){
 const result=fixtureFor(input,scenario)
 yield {type:'progress',contextKey:result.contextKey,message:'Preparing synthetic evidence'}
 await delay(350,signal)
 if(scenario==='timeout')throw new Error('MOCK_TIMEOUT')
 for(const section of result.sections){if(section.verified){await delay(55,signal);yield {type:'section_verified',contextKey:result.contextKey,section,sources:result.sources}}}
 yield {type:'answer_complete',contextKey:result.contextKey,answer:result}
}
// Accept only verified events for this exact context. Never render progress/draft text as an answer.
export function acceptEvent(current,event,key){
 if(event.contextKey!==key)return current
 if(event.type==='section_verified'){
  if(!event.section?.verified||!Array.isArray(event.section.citationIds)||!event.section.citationIds.length||!Array.isArray(event.sources)||event.section.citationIds.some(id=>!event.sources.some(s=>s.id===id)))return current
  return {...current,sections:[...(current.sections||[]).filter(s=>s.id!==event.section.id),event.section],sources:event.sources}
 }
 if(event.type==='answer_complete'&&event.answer?.contextKey===key){
  const answer=event.answer
  if(!Array.isArray(answer.sections)||!Array.isArray(answer.sources))return current
  if(answer.sections.some(s=>s.verified&&(!Array.isArray(s.citationIds)||!s.citationIds.length||s.citationIds.some(id=>!answer.sources.some(source=>source.id===id)))))return current
  return answer
 }
 return current
}
export async function prepareEscalation(item,question,consent,signal){
 if(!consent||!question.trim())throw new Error('Question and explicit consent required')
 await delay(300,signal)
 return {mock:true,id:crypto.randomUUID(),question,scope:'Current facts and open questions',contextKey:contextKey(item),consented_at:new Date().toISOString(),consentVersion:'mock-sharing-v1',sent:false,status:'Under human review',comments:[]}
}
