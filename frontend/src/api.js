import { z } from 'zod'

// Integration contract only; the demo never sends case data to this adapter.
const citation = z.object({id:z.string().min(1),url:z.url(),provision:z.string().min(1),excerpt:z.string().min(1),version:z.string().min(1)})
export const guidanceSchema=z.object({
 jurisdiction:z.string(), asOf:z.string(),
 support:z.enum(['SUPPORTED_IN_SCOPE','MISSING_FACTS','MISSING_EVIDENCE','CONFLICTING_SOURCES','OUT_OF_SCOPE','REVIEW_REQUIRED']),
 claims:z.array(z.object({text:z.string(),citationIds:z.array(z.string()).min(1)})),
 citations:z.array(citation),
}).superRefine((value,ctx)=>{
 const ids=new Set(value.citations.map(c=>c.id))
 if(value.claims.some(c=>c.citationIds.some(id=>!ids.has(id))))ctx.addIssue({code:'custom',message:'Claim references missing evidence'})
 if(value.support==='SUPPORTED_IN_SCOPE'&&!value.claims.length)ctx.addIssue({code:'custom',message:'Supported guidance requires cited claims'})
})
export async function requestGuidance(baseUrl,payload,signal){
 const endpoint=new URL('/api/v1/guidance',baseUrl)
 if(endpoint.protocol!=='https:'&&endpoint.hostname!=='localhost'&&endpoint.hostname!=='127.0.0.1')throw new Error('HTTPS required')
 const response=await fetch(endpoint,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(20000)]):AbortSignal.timeout(20000)})
 if(!response.ok)throw new Error(`Guidance unavailable (${response.status})`)
 const result=guidanceSchema.parse(await response.json())
 if(result.jurisdiction!==payload.jurisdiction||result.asOf!==payload.asOf)throw new Error('Response context does not match the requested jurisdiction and date')
 return result
}
