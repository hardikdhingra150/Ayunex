export const SUPPORT_STATES=['SUPPORTED_IN_SCOPE','MISSING_FACTS','MISSING_EVIDENCE','CONFLICTING_SOURCES','OUT_OF_SCOPE','REVIEW_REQUIRED']
export function invalidateCase(item,patch){return {...item,...patch,status:'Needs information',confirmed:false,assessment:null,mockAnswer:null,sharing:null,completed:[]}}
export function missingFacts(facts){return ['use','form','source','ingredients','origin'].filter(k=>!facts[k]||facts[k]==='Unknown')}
export function progressFor(facts){return Math.round(['use','form','source','ingredients','origin','processing','applicant','stage','market','disclosure'].filter(k=>facts[k]&&facts[k]!=='Unknown').length*10)}
export function exportPayload(c){return {format:'ip-sakti-case-v1',disclaimer:'Frontend demonstration. Information, not legal advice. No authoritative legal assessment has been performed.',generated_at:new Date().toISOString(),timeline:c.timeline||[],updated_at:c.updatedAt||null,case_id:c.id,title:c.title,jurisdiction:c.jurisdiction,as_of_date:c.asOf,facts:c.facts,confirmed:c.confirmed,support_status:c.assessment?.support||'MISSING_EVIDENCE',classification:'UNRESOLVED',citations:c.mockAnswer?.sources||[],mock_answer:c.mockAnswer||null,evidence_files:c.evidenceFiles||[],missing_facts:missingFacts(c.facts),checklist:c.completed,versions:c.versions,sharing:c.sharing||null}}
export function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
export function exportHtml(c){const d=exportPayload(c);return `<!doctype html><html lang="en"><meta charset="utf-8"><title>AYUNEX case</title><style>body{font:16px system-ui;max-width:900px;margin:50px auto;padding:20px;line-height:1.7;color:#173321}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5ef;padding:24px}h1{font-size:30px}</style><h1>${escapeHtml(c.title)}</h1><p>${escapeHtml(d.disclaimer)}</p><pre>${escapeHtml(JSON.stringify(d,null,2))}</pre></html>`}
export function downloadFile(content,name,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export function factsToBackendPassport(facts, ingredientRows = []) {
  const backendFacts = {}
  for(const [ui,key] of Object.entries({form:'dosage_form',claims:'claims',evidence:'evidence',stage:'commercial_stage',market:'target_market',disclosure:'prior_disclosure',ingredients:'ingredient_summary'})){
    if(facts[ui])backendFacts[key]={value:facts[ui]==='Unknown'?null:facts[ui],provenance:'user-entered',confirmed:facts[ui]!=='Unknown',unknown:facts[ui]==='Unknown'}
  }
  const useMap = { 'Therapeutic': 'THERAPEUTIC', 'Food': 'FOOD', 'Cosmetic': 'COSMETIC', 'Research': 'RESEARCH' }
  if (facts.use) {
    const val = useMap[facts.use]
    backendFacts['intended_use'] = { value: val || null, provenance: 'user-entered', confirmed: true, unknown: facts.use === 'Unknown' }
  }
  const adminMap = { 'Oral': 'ORAL', 'External': 'EXTERNAL' }
  if (facts.administration) {
    const val = adminMap[facts.administration] || facts.administration.toUpperCase()
    backendFacts['administration_route'] = { value: val || null, provenance: 'user-entered', confirmed: true, unknown: facts.administration === 'Unknown' }
  }
  if (facts.foodRoute) {
    const val = facts.foodRoute.includes('Ayurveda Aahara') ? 'AYURVEDA_AAHARA' : 'OTHER'
    backendFacts['food_subroute'] = { value: val, provenance: 'user-entered', confirmed: true, unknown: facts.foodRoute === 'Unknown' }
  }
  if (facts.source) {
    const isUnknown = facts.source === 'Unknown'
    backendFacts['formula_source'] = { value: isUnknown ? null : facts.source, provenance: 'user-entered', confirmed: !isUnknown, unknown: isUnknown }
    for(const key of ['formula_matches_text','method_matches_text','ingredients_in_texts']){
      const explicit=facts[key]
      backendFacts[key]={value:typeof explicit==='boolean'?explicit:null,provenance:'user-entered',confirmed:typeof explicit==='boolean',unknown:typeof explicit!=='boolean'}
    }
  }
  if (facts.processing) {
    for(const key of ['modified','purified_fraction']){
      const explicit=facts[key]
      backendFacts[key]={value:typeof explicit==='boolean'?explicit:null,provenance:'user-entered',confirmed:typeof explicit==='boolean',unknown:typeof explicit!=='boolean'}
    }
    backendFacts['processing'] = { value: facts.processing, provenance: 'user-entered', confirmed: true, unknown: facts.processing === 'Unknown' }
  }
  if (facts.origin) {
    const originMap = { 'India': 'IN', 'Outside India': 'FOREIGN', 'Mixed': 'MIXED', 'Unknown': 'UNKNOWN' }
    backendFacts['origin'] = { value: originMap[facts.origin] || facts.origin, provenance: 'user-entered', confirmed: true, unknown: facts.origin === 'Unknown' }
  }
  if (facts.applicant) {
    backendFacts['applicant'] = { value: facts.applicant, provenance: 'user-entered', confirmed: true, unknown: facts.applicant === 'Unknown' }
  }
  const ingredients = (ingredientRows || []).map(r => ({
    name: r.name || 'Unknown',
    biological_type: ['PLANT', 'ANIMAL', 'MICROBIAL', 'NON_BIOLOGICAL'].includes(r.kind) ? r.kind : 'UNKNOWN',
    part: r.part || 'Unknown',
    origin: ['IN', 'FOREIGN', 'MIXED'].includes(r.origin) ? r.origin : 'UNKNOWN',
    sourcing: ['CULTIVATED', 'WILD', 'PURCHASED'].includes(r.sourcing) ? r.sourcing : 'UNKNOWN',
    alias_unresolved: true
  }))
  return { facts: backendFacts, ingredients }
}

export function backendPassportToFacts(passport,title){
 const facts={name:title},mapping={intended_use:'use',administration_route:'administration',food_subroute:'foodRoute',formula_source:'source',dosage_form:'form',commercial_stage:'stage',target_market:'market',prior_disclosure:'disclosure',ingredient_summary:'ingredients'}
 const values={intended_use:{THERAPEUTIC:'Therapeutic',FOOD:'Food',COSMETIC:'Cosmetic',RESEARCH:'Research'},administration_route:{ORAL:'Oral',EXTERNAL:'External',OTHER:'Other'},food_subroute:{AYURVEDA_AAHARA:'Ayurveda Aahara',OTHER:'Other food / nutraceutical'},origin:{IN:'India',FOREIGN:'Outside India',MIXED:'Mixed'}}
 for(const [key,fact] of Object.entries(passport?.facts||{}))facts[mapping[key]||key]=fact.unknown||fact.value===null?'Unknown':values[key]?.[fact.value]??fact.value
 facts.ingredientRows=(passport?.ingredients||[]).map((r,i)=>({id:`stored-${i}`,name:r.name,kind:r.biological_type,part:r.part,origin:r.origin,sourcing:r.sourcing}))
 return facts
}
