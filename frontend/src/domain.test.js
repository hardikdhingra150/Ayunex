import { test } from 'node:test'
import assert from 'node:assert/strict'
import { invalidateCase, missingFacts, progressFor, exportPayload, exportHtml, factsToBackendPassport } from './domain.js'

const sample = { id:'test', title:'Synthetic concept', jurisdiction:'IN', asOf:'2026-09-10', facts:{use:'Cosmetic'}, confirmed:true, completed:[0], versions:[], assessment:{support:'SUPPORTED_IN_SCOPE'}, sharing:{sent:false} }
test('context changes invalidate assessment, confirmation and handoff',()=>{
 const next=invalidateCase(sample,{jurisdiction:'EU'})
 assert.equal(next.assessment,null); assert.equal(next.sharing,null)
 assert.equal(next.confirmed,false); assert.deepEqual(next.completed,[])
 assert.equal(sample.jurisdiction,'IN'); assert.equal(next.jurisdiction,'EU')
})
test('unknown decisive facts remain unresolved',()=>{
 assert.deepEqual(missingFacts({use:'Cosmetic',form:'Topical',source:'Unknown',ingredients:'Unknown',origin:'Unknown'}),['source','ingredients','origin'])
})
test('progress counts known facts, not confidence',()=>{
 assert.equal(progressFor({}),0); assert.equal(progressFor({use:'Cosmetic',origin:'Unknown'}),10)
})
test('export never invents citations or classification',()=>{
 const result=exportPayload(invalidateCase(sample,{}))
 assert.deepEqual(result.citations,[]); assert.equal(result.classification,'UNRESOLVED')
 assert.match(result.disclaimer,/not legal advice/)
})
test('HTML export escapes user content',()=>{
 const html=exportHtml({...sample,title:'<script>alert(1)</script>'})
 assert.ok(!html.includes('<script>')); assert.ok(html.includes('&lt;script&gt;'))
})
test('factsToBackendPassport formats facts and ingredients for backend schema',()=>{
 const facts={use:'Therapeutic',administration:'Oral',source:'Charaka Samhita',processing:'Modified with extraction',origin:'India'}
 const rows=[{name:'Ashwagandha',kind:'PLANT',part:'Root',origin:'IN',sourcing:'CULTIVATED'}]
 const p=factsToBackendPassport(facts,rows)
 assert.equal(p.facts.intended_use.value,'THERAPEUTIC')
 assert.equal(p.facts.administration_route.value,'ORAL')
 assert.equal(p.facts.formula_matches_text.value,null)
 assert.equal(p.facts.formula_matches_text.unknown,true)
 assert.equal(p.facts.modified.value,null)
 assert.equal(p.facts.modified.unknown,true)
 assert.equal(p.facts.origin.value,'IN')
 assert.equal(p.ingredients.length,1)
 assert.equal(p.ingredients[0].name,'Ashwagandha')
 assert.equal(p.ingredients[0].biological_type,'PLANT')
})
