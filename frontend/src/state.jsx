import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { AppContext } from './context'
import { invalidateCase, factsToBackendPassport, backendPassportToFacts } from './domain'
import { uiHindi } from './uiHindi'
import { createBackendClient } from './backendClient'

export function AppProvider({children}){
 const [cases,setCases]=useState([])
 const [profile,setProfile]=useState(null)
 const [language,setLanguage]=useState(()=>localStorage.getItem('ipsakti-language')||'en')
 const [motion,setMotion]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches)
 const [consent,setConsent]=useState(false),[toast,setToast]=useState('')

 const [backendMode,setBackendMode]=useState('disconnected')
 const [backendToken,setBackendToken]=useState('')
 const [backendRole,setBackendRole]=useState('user')
 const [connectionStatus,setConnectionStatus]=useState('checking')
 const identityEpoch=useRef(0)
 const saveQueues=useRef(new Map()),savedRevisions=useRef(new Map())

 const backendClient = useMemo(()=>{
  if(connectionStatus!=='connected') return null
  try {
   return createBackendClient({
    cookieAuth: true
   })
  } catch(err) {
   void err
   return null
  }
 },[connectionStatus])

 const syncLiveCases = useCallback(async (clientInstance = backendClient) => {
  if (!clientInstance) return
  const epoch=identityEpoch.current
  try {
   const serverCases = await clientInstance.cases()
   const passports=new Map()
   for(let index=0;index<serverCases.length;index+=4){
    await Promise.all(serverCases.slice(index,index+4).map(async sc=>{
     const stored=await clientInstance.passport(sc.id)
     passports.set(sc.id,stored)
    }))
   }
   if(epoch!==identityEpoch.current)return
   if (Array.isArray(serverCases)) {
    setCases(old => {
     const serverMap = new Map(serverCases.map(c => [c.id, c]))
     const updated = old.filter(c=>!c.live||serverMap.has(c.id)).map(c => {
      const sc = serverMap.get(c.id)
      if (!sc) return c
      return {
       ...c,
       title: sc.title,
       facts:backendPassportToFacts(passports.get(sc.id)?.passport,sc.title),
       status: sc.status,
       revision: sc.revision,
       passportVersion: sc.passport_version,
       asOf: sc.as_of_date,
       live: true
      }
     })
     for (const sc of serverCases) {
      if (!old.some(c => c.id === sc.id)) {
       updated.unshift({
        id: sc.id,
        title: sc.title,
        sample: false,
        status: sc.status,
        jurisdiction: sc.jurisdiction?.country || (sc.jurisdiction?.layer === 'TREATY_FRAMEWORK' ? 'TREATY' : 'IN'),
        asOf: sc.as_of_date,
        facts: backendPassportToFacts(passports.get(sc.id)?.passport,sc.title),
        revision: sc.revision,
        passportVersion: sc.passport_version,
        confirmed: false,
        completed: [],
        versions: [],
        live: true
       })
      }
     }
     return updated
    })
   }
  } catch (err) {
   if(epoch===identityEpoch.current)setToast(err.status===401?'Your session expired. Please sign in again.':'Could not load saved cases. Reload to retry; no local copies were created.')
  }
 }, [backendClient])

 const connectBackend = useCallback(async () => {
  const epoch=++identityEpoch.current
  try {
   setConnectionStatus('connecting')
   const testClient = createBackendClient({
    cookieAuth: true
   })
   const user = await testClient.me()
   if(epoch!==identityEpoch.current)return {ok:false,error:'Connection superseded'}
   setBackendToken('')
   setBackendRole(user.role)
   setProfile(user)
   setCases([])
   setBackendMode('live')
   setConnectionStatus('connected')
   sessionStorage.setItem('ipsakti-mode', 'live')
   sessionStorage.removeItem('ipsakti-token')
   setToast(language === 'hi' ? 'लाइव बैकएंड से जुड़ा' : `Connected to live backend as ${user.role}`)
   await syncLiveCases(testClient)
   return { ok: true, user }
  } catch (err) {
   setConnectionStatus('disconnected')
   setBackendMode('disconnected')
   setProfile(null)
   setCases([])
   const msg = err.status === 401 ? 'Please sign in to save your work.' : err.message || 'Connection failed'
   return { ok: false, error: msg }
  }
 }, [language, syncLiveCases])

 const disconnectBackend = useCallback(async () => {
  try {
   const response=await fetch('/api/v1/auth/logout',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Protection':'1'},signal:AbortSignal.timeout(15000)})
   if(!response.ok)throw new Error('Sign out failed')
  } catch {setToast('Could not sign out. Please retry.');return}
  identityEpoch.current++
  setBackendMode('disconnected')
  setProfile(null)
  setBackendToken('')
  setBackendRole('user')
  setCases([])
  setConnectionStatus('disconnected')
  sessionStorage.setItem('ipsakti-mode', 'mock')
  sessionStorage.removeItem('ipsakti-token')
  setToast(language === 'hi' ? 'साइन आउट हो गया' : 'Signed out')
 }, [language])

 useEffect(()=>{localStorage.setItem('ipsakti-language',language);document.documentElement.lang=language},[language])
 useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4000);return ()=>clearTimeout(t)},[toast])

 // Auto-connect on startup: use existing token or provision session automatically
 const autoConnectAttempted = useRef(false)
 useEffect(() => {
  if (autoConnectAttempted.current) return
  autoConnectAttempted.current = true
  sessionStorage.removeItem('ipsakti-token')
   Promise.resolve().then(()=>connectBackend())
    .catch(() => {
     setBackendMode('disconnected')
     setConnectionStatus('disconnected')
    })
 }, [backendRole, connectBackend])

 function updateCase(id,patch,invalidate=false){
  setCases(old=>old.map(c=>{
   if(c.id!==id)return c;
   const at=new Date().toISOString();
   const next=invalidate?invalidateCase(c,patch):{...c,...patch};
   return {...next,updatedAt:at,timeline:[...(c.timeline||[]),{at,action:invalidate?'Facts/context changed; results invalidated':'Case updated'}]}
  }))
  // If in live mode and connected, sync passport or patch to backend asynchronously
  if (backendMode === 'live' && backendClient) {
   const currentCase = cases.find(c => c.id === id)
   if (currentCase && currentCase.live && (patch.facts||patch.jurisdiction||patch.asOf)) {
    const epoch=identityEpoch.current
    const pending=(saveQueues.current.get(id)||Promise.resolve()).then(async()=>{
     if(epoch!==identityEpoch.current)return
     let revision=savedRevisions.current.get(id)||currentCase.revision||1
     let res
     if(patch.jurisdiction||patch.asOf){
      const jur=patch.jurisdiction
      res=await backendClient.patchCase(id,{expected_revision:revision,...(patch.asOf?{as_of_date:patch.asOf}:{}),...(jur?{jurisdiction:jur==='IN'?{layer:'NATIONAL',country:'IN'}:jur==='TREATY'?{layer:'TREATY_FRAMEWORK',framework:'PCT'}:{layer:'EXPORT_MARKET',country:jur}}:{})})
      revision=res.revision
     }
     if(patch.facts)res=await backendClient.savePassport(id,factsToBackendPassport(patch.facts,patch.facts.ingredientRows||[]),revision)
     if(epoch!==identityEpoch.current)return
     savedRevisions.current.set(id,res.revision)
     setCases(old=>old.map(c=>c.id===id?{...c,revision:res.revision,passportVersion:res.version??c.passportVersion,saveError:null}:c))
    }).catch(err=>{
     if(epoch!==identityEpoch.current)return
     const message=err.status===409?'A newer server version exists. Reload before editing further.':'Your latest edit was not saved. Check your connection and retry.'
     setCases(old=>old.map(c=>c.id===id?{...c,saveError:message}:c));setToast(message)
    })
    saveQueues.current.set(id,pending)
   }
  }
 }

 return <AppContext.Provider value={{
  cases,setCases,profile,language,setLanguage,motion,setMotion,consent,setConsent,updateCase,
  notify:setToast,
  backendMode,setBackendMode,backendToken,backendRole,setBackendRole,
  connectionStatus,backendClient,connectBackend,disconnectBackend,syncLiveCases
 }}>{children}{toast&&<div className="toast" role="status">{language==='hi'?(uiHindi[toast]||toast):toast}</div>}</AppContext.Provider>
}
