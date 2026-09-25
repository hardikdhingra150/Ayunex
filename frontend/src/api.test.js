import { test } from 'node:test'
import assert from 'node:assert/strict'
import { guidanceSchema } from './api.js'
test('uncited supported output fails validation',()=>{
 assert.equal(guidanceSchema.safeParse({jurisdiction:'IN',asOf:'2026-09-10',support:'SUPPORTED_IN_SCOPE',claims:[],citations:[]}).success,false)
})
test('dangling citation references fail validation',()=>{
 assert.equal(guidanceSchema.safeParse({jurisdiction:'IN',asOf:'2026-09-10',support:'SUPPORTED_IN_SCOPE',claims:[{text:'Example',citationIds:['missing']}],citations:[]}).success,false)
})
