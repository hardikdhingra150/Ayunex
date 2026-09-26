import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from './context'

export default function Login(){
 const {connectBackend}=useApp(),navigate=useNavigate()
 const [link]=useState(()=>new URLSearchParams(window.location.hash.slice(1)))
 const [mode,setMode]=useState(()=>link.has('reset')?'reset-password':link.has('verify')?'verify-email':'login')
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('')
 const [options,setOptions]=useState({email_verification_required:false,password_reset_available:false})
 const [displayName,setDisplayName]=useState('')
 useEffect(()=>{const controller=new AbortController();fetch('/api/v1/auth/options',{signal:controller.signal}).then(r=>r.ok?r.json():Promise.reject()).then(setOptions).catch(()=>{});return()=>controller.abort()},[])
 useEffect(()=>{if(window.location.hash)window.history.replaceState(null,'',window.location.pathname)},[])
 const titles={login:'Welcome back',signup:'Create your account','forgot-password':'Reset your password','reset-password':'Choose a new password','verify-email':'Verify your email'}
 async function submit(event){
  event.preventDefault();setBusy(true);setError('');setMessage('')
  const body=mode==='verify-email'?{token:link.get('verify')}:mode==='reset-password'?{token:link.get('reset'),password}:mode==='forgot-password'?{email}:{email,password}
  if(mode==='signup')body.display_name=displayName.trim()
  try{
   const response=await fetch('/api/v1/auth/'+mode,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Protection':'1'},body:JSON.stringify(body),signal:AbortSignal.timeout(30000)})
   const data=await response.json()
   if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Check your email address and password (12–128 characters).')
   if(mode==='signup'&&!options.email_verification_required){
    const login=await fetch('/api/v1/auth/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Protection':'1'},body:JSON.stringify({email,password}),signal:AbortSignal.timeout(30000)})
    if(!login.ok){setMode('login');throw new Error('Please sign in with your existing password, or retry if your account is temporarily locked.')}
   }
   setPassword('');setMessage(data.message||'Signed in')
   if(mode==='login'||(mode==='signup'&&!options.email_verification_required)){const result=await connectBackend();if(!result.ok)throw new Error(result.error);navigate('/workspace')}
   else if(mode==='verify-email'||mode==='reset-password')setMode('login')
  }catch(err){setError(err.message||'Unable to connect. Please retry.')}finally{setBusy(false)}
 }
 return <section className="panel" style={{maxWidth:480,margin:'48px auto',padding:32}}><div className="eyebrow">YOUR PRIVATE RESEARCH WORKSPACE</div><h1>{titles[mode]}</h1><p>Save your cases and explore evidence-backed guidance.</p><form onSubmit={submit}>
 {['login','signup','forgot-password'].includes(mode)&&<div className="field"><label htmlFor="account-email">Email address</label><input id="account-email" type="email" autoComplete="email" maxLength={254} required value={email} onChange={e=>setEmail(e.target.value)} disabled={busy}/></div>}
 {mode==='signup'&&<div className="field"><label htmlFor="account-name">Your name</label><input id="account-name" autoComplete="name" maxLength={80} required value={displayName} onChange={e=>setDisplayName(e.target.value)} disabled={busy}/></div>}
 {['login','signup','reset-password'].includes(mode)&&<div className="field"><label htmlFor="account-password">Password</label><input id="account-password" type="password" autoComplete={mode==='login'?'current-password':'new-password'} minLength={12} maxLength={128} required value={password} onChange={e=>setPassword(e.target.value)} disabled={busy}/><small>Use a unique passphrase of at least 12 characters.</small></div>}
 {mode==='signup'&&<p><small>{options.email_verification_required?'Check your inbox to verify your account.':'No email verification required. Create your account and start immediately.'} AI processing is optional and requires separate consent.</small></p>}
 {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 <button className="button primary" disabled={busy}>{busy?'Please wait…':mode==='login'?'Sign in':mode==='signup'?'Create account':mode==='verify-email'?'Verify email':mode==='reset-password'?'Save new password':'Send reset link'}</button></form>
 <div style={{display:'flex',flexWrap:'wrap',gap:12,marginTop:24}}>{['login','signup',...(options.password_reset_available?['forgot-password']:[])].filter(m=>m!==mode).map(m=><button className="text-link" disabled={busy} key={m} onClick={()=>{setMode(m);setError('');setMessage('');setPassword('')}}>{m==='login'?'Sign in':m==='signup'?'Create account':'Forgot password?'}</button>)}</div><p><small>Information, not legal advice. Never submit confidential formulations.</small></p></section>
}
