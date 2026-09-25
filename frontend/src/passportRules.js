import { steps } from './data.js'
export function applicableSteps(facts){
 const result=steps.map((step,i)=>({...step,fields:step.fields.filter(([key])=>!(key==='claims'&&facts.use==='Research')),helpHi:['दावे और उपयोग से आवश्यक प्रश्न तय होते हैं।','सामग्री के नाम और मूल दर्ज करें। गोपनीय अनुपात आवश्यक नहीं हैं।','प्रक्रिया में परिवर्तन और उपलब्ध प्रमाण दर्ज करें।','आवेदक और विकास चरण जैव संसाधन समीक्षा के लिए आवश्यक हैं।','लक्षित बाजार और सार्वजनिक प्रकटीकरण दर्ज करें।'][i]}))
 result.splice(1,0,{name:'Administration & category',hi:'प्रयोग और श्रेणी',help:'Record how the product is used. This is a user description, not a legal classification.',helpHi:'उत्पाद के प्रयोग का तरीका दर्ज करें। यह कानूनी वर्गीकरण नहीं है।',fields:[['administration','Route of administration','प्रयोग का तरीका',facts.use==='Cosmetic'?['External','Other','Unknown']:['Oral','External','Other','Unknown']],...(facts.use==='Food'?[['foodRoute','Proposed food route','प्रस्तावित खाद्य मार्ग',['Ayurveda Aahara','Other food / nutraceutical','Unknown']]]:[])]})
 return result
}
export function ingredientSummary(rows){return rows.map(r=>`${r.name||'Unknown'} (${r.part||'Unknown'}; ${r.kind||'Unknown'}; ${r.origin||'Unknown'}; ${r.sourcing||'Unknown'})`).join('; ')}
export function validateIngredient(row){if(!row.name.trim())return 'name';if(!row.kind)return 'kind';if(!row.origin)return 'origin';return null}
