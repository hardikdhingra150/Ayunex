import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { AppContext, initialCases } from './context'
import { invalidateCase, factsToBackendPassport } from './domain'
import { uiHindi } from './uiHindi'
import { createBackendClient, fetchSession } from './backendClient'

export function AppProvider({children}){
 const [cases,setCases]=useState(()=>structuredClone(initialCases))
 const [language,setLanguage]=useState(()=>localStorage.getItem('ipsakti-language')||'en')
 const [motion,setMotion]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches)
 const [consent,setConsent]=useState(false),[toast,setToast]=useState('')

 const [backendMode,setBackendMode]=useState(()=>sessionStorage.getItem('ipsakti-mode')||'live')
 const [backendToken,setBackendToken]=useState(()=>sessionStorage.getItem('ipsakti-token')||'')
 const [backendRole,setBackendRole]=useState('user')
 const [connectionStatus,setConnectionStatus]=useState('disconnected')

 const backendClient = useMemo(()=>{
  if(!backendToken) return null
  try {
   return createBackendClient({
    getToken: () => backendToken + (backendRole !== 'user' ? `:${backendRole}` : '')
   })
  } catch(err) {
   void err
   return null
  }
 },[backendToken, backendRole])

 const syncLiveCases = useCallback(async (clientInstance = backendClient) => {
  if (!clientInstance) return
  try {
   const serverCases = await clientInstance.cases()
   if (Array.isArray(serverCases)) {
    setCases(old => {
     const serverMap = new Map(serverCases.map(c => [c.id, c]))
     const updated = old.map(c => {
      const sc = serverMap.get(c.id)
      if (!sc) return c
      return {
       ...c,
       title: sc.title,
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
        facts: { name: sc.title },
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
   console.error('Failed to sync cases:', err)
  }
 }, [backendClient])

 const connectBackend = useCallback(async (token, role = 'user') => {
  try {
   setConnectionStatus('connecting')
   const testClient = createBackendClient({
    getToken: () => token.trim() + (role !== 'user' ? `:${role}` : '')
   })
   const user = await testClient.me()
   setBackendToken(token.trim())
   setBackendRole(role)
   setBackendMode('live')
   setConnectionStatus('connected')
   sessionStorage.setItem('ipsakti-mode', 'live')
   sessionStorage.setItem('ipsakti-token', token.trim())
   setToast(language === 'hi' ? 'लाइव बैकएंड से जुड़ा' : `Connected to live backend as ${user.role}`)
   await syncLiveCases(testClient)
   return { ok: true, user }
  } catch (err) {
   setConnectionStatus('disconnected')
   const msg = err.status === 401 ? 'Invalid token' : err.message || 'Connection failed'
   setToast(language === 'hi' ? `कनेक्शन विफल: ${msg}` : `Backend connection failed: ${msg}`)
   return { ok: false, error: msg }
  }
 }, [language, syncLiveCases])

 const disconnectBackend = useCallback(() => {
  setBackendMode('mock')
  setBackendToken('')
  setConnectionStatus('disconnected')
  sessionStorage.setItem('ipsakti-mode', 'mock')
  sessionStorage.removeItem('ipsakti-token')
  setToast(language === 'hi' ? 'स्थानीय सत्र मोड पर स्विच किया गया' : 'Switched to local session mode')
 }, [language])

 useEffect(()=>{localStorage.setItem('ipsakti-language',language);document.documentElement.lang=language},[language])
 useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4000);return ()=>clearTimeout(t)},[toast])

 // Auto-connect on startup: use existing token or provision session automatically
 const autoConnectAttempted = useRef(false)
 useEffect(() => {
  if (autoConnectAttempted.current) return
  autoConnectAttempted.current = true
  const mode = sessionStorage.getItem('ipsakti-mode') || 'live'
  if (mode === 'mock') return
  const token = sessionStorage.getItem('ipsakti-token')
  if (token) {
   setTimeout(() => { connectBackend(token, backendRole) }, 0)
  } else {
   fetchSession(backendRole)
    .then(res => {
     if (res?.token) {
      connectBackend(res.token, backendRole)
     }
    })
    .catch(() => {
     setBackendMode('mock')
     setConnectionStatus('disconnected')
    })
  }
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
   if (currentCase && currentCase.live && patch.facts) {
    const passportPayload = factsToBackendPassport(patch.facts, patch.facts.ingredientRows || [])
    backendClient.savePassport(id, passportPayload, currentCase.revision || 1)
     .then(res => {
      setCases(old => old.map(c => c.id === id ? { ...c, revision: res.revision, passportVersion: res.version } : c))
     })
     .catch(err => {
      if (err.status === 409) setToast('Case modified concurrently on server. Please refresh.')
     })
   }
  }
 }

 return <AppContext.Provider value={{
  cases,setCases,language,setLanguage,motion,setMotion,consent,setConsent,updateCase,
  notify:setToast,
  backendMode,setBackendMode,backendToken,backendRole,setBackendRole,
  connectionStatus,backendClient,connectBackend,disconnectBackend,syncLiveCases
 }}>{children}{toast&&<div className="toast" role="status">{language==='hi'?(uiHindi[toast]||toast):toast}</div>}</AppContext.Provider>
}

