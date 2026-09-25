export function registerNavigationTools(){
 const context=document.modelContext
 if(!context?.registerTool)return ()=>{}
 const lifecycle=new AbortController()
 try {
  Promise.resolve(context.registerTool({
   name:'start_product_case',title:'Start Product Passport',
   description:'Open the new case form. Does not create a case, submit facts or acknowledge consent.',
   inputSchema:{type:'object',properties:{},additionalProperties:false},
   annotations:{readOnlyHint:false,untrustedContentHint:false},
   execute(input){
    if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length)throw new Error('Expected an empty object')
    window.history.pushState({},'', '/cases/new')
    window.dispatchEvent(new PopStateEvent('popstate'))
    return new Promise(resolve=>requestAnimationFrame(()=>resolve({route:'/cases/new',status:'form_opened',caseCreated:false})))
   },
  },{signal:lifecycle.signal})).catch(()=>{})
 }catch{/* Experimental API availability must not affect the interface. */}
 return ()=>lifecycle.abort()
}
