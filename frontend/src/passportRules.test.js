import {test} from 'node:test'
import assert from 'node:assert/strict'
import {applicableSteps,ingredientSummary,validateIngredient} from './passportRules.js'
test('food has a food-route question without legal classification',()=>assert.ok(applicableSteps({use:'Food'}).some(s=>s.fields.some(([k])=>k==='foodRoute'))))
test('research omits claims',()=>assert.ok(!applicableSteps({use:'Research'}).some(s=>s.fields.some(([k])=>k==='claims'))))
test('questions are grouped to at most three fields',()=>assert.ok(applicableSteps({use:'Food'}).every(s=>s.fields.length<=3)))
test('ingredients require a name and explicit origin',()=>{assert.equal(validateIngredient({name:' ',kind:'Plant',origin:'India'}),'name');assert.equal(validateIngredient({name:'Unknown',kind:'Unknown',origin:'Unknown'}),null)})
test('summary retains unknowns',()=>assert.match(ingredientSummary([{name:'Test'}]),/Unknown/))
