import { test } from 'node:test'
import assert from 'node:assert/strict'
import { fixtureFor, contextKey, acceptEvent, guidanceEvents, prepareEscalation } from './mockApi.js'
const item={id:'test',jurisdiction:'IN',asOf:'2026-09-10',facts:{use:'Food'}}
test('synthetic sources never impersonate official law',()=>{const a=fixtureFor(item);assert.equal(a.mock,true);assert.equal(a.sources[0].url,null);assert.match(a.sources[0].authority,/NOT a legal authority/)})
test('stale jurisdiction events are ignored',()=>{const old={sections:[]},a=fixtureFor(item);assert.equal(acceptEvent(old,{type:'answer_complete',contextKey:a.contextKey,answer:a},contextKey({...item,jurisdiction:'EU'})),old)})
test('draft events never expose prose',()=>{const old={sections:[]};assert.equal(acceptEvent(old,{type:'draft',contextKey:contextKey(item),text:'Unverified'},contextKey(item)),old)})
test('verified event with a dangling citation is rejected',()=>{const old={sections:[]};assert.equal(acceptEvent(old,{type:'section_verified',contextKey:contextKey(item),section:{id:'s',verified:true,citationIds:['bad']},sources:[]},contextKey(item)),old)})
test('partial fixture retains unresolved sections',()=>{const a=fixtureFor(item,'partial');assert.equal(a.sections.filter(s=>s.verified).length,3);assert.equal(a.sections.length,9)})
test('restricted fixture grants no evidence access',()=>assert.deepEqual(fixtureFor(item,'restricted').sources,[]))
test('language is independent of the context key',()=>assert.equal(contextKey({...item,language:'hi'}),contextKey({...item,language:'en'})))
test('cancelled stream stops before any verified section',async()=>{const c=new AbortController(),stream=guidanceEvents(item,{signal:c.signal});assert.equal((await stream.next()).value.type,'progress');c.abort();await assert.rejects(stream.next(),{name:'AbortError'})})
test('mock timeout is explicit',async()=>{await assert.rejects(async()=>{for await(const event of guidanceEvents(item,{scenario:'timeout'})){assert.equal(event.type,'progress')}},/MOCK_TIMEOUT/)})
test('handoff requires explicit consent',async()=>await assert.rejects(prepareEscalation(item,'Help',false),/consent/))
test('completed answers with broken citations are rejected',()=>{const old={sections:[]},answer=fixtureFor(item);answer.sources=[];assert.equal(acceptEvent(old,{type:'answer_complete',contextKey:contextKey(item),answer},contextKey(item)),old)})
test('cancelled handoff never creates a packet',async()=>{const c=new AbortController();c.abort();await assert.rejects(prepareEscalation(item,'QA',true,c.signal),{name:'AbortError'})})
