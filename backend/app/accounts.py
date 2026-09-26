"""Email-verified accounts, revocable opaque sessions, purpose-bound reset tokens.

Browser cookies are HttpOnly, SameSite=Strict and Secure in production.
Passwords use salted PBKDF2-HMAC-SHA256 (600,000 iterations); no JWT/password
or API credential is returned to the browser. SMTP uses TLS verification.
"""
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import Field,field_validator,ConfigDict
from sqlalchemy import select,delete
from .schemas import Strict,Principal
from .models import Account,AccountSession,AccountAction
from .hardening import RequestGuard


def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def password_hash(password):
    salt=secrets.token_hex(16)
    value=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
    return 'pbkdf2_sha256$600000$'+salt+'$'+value
def password_matches(password,stored):
    try:
        scheme,rounds,salt,expected=stored.split('$')
        if scheme!='pbkdf2_sha256' or rounds!='600000':return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError):return False
_DUMMY_HASH=password_hash(secrets.token_urlsafe(32))


def cookie_name(settings):return '__Host-ayunex_session' if settings.environment=='production' else 'ayunex_session'


def csrf(request):
    if request.method in {'GET','HEAD','OPTIONS'}:return
    if request.headers.get('x-csrf-protection')!='1':raise HTTPException(403,'CSRF protection required')
    origin=request.headers.get('origin')
    if origin:
        settings=request.app.state.settings
        allowed={settings.public_app_url.rstrip('/')}
        if settings.environment!='production':allowed.update(settings.cors_origins)
        if origin not in allowed:raise HTTPException(403,'Request origin rejected')


def cookie_identity(request):
    settings=request.app.state.settings
    raw=request.cookies.get(cookie_name(settings),'')
    if not raw or len(raw)>256:return None
    csrf(request)
    with request.app.state.sessions() as db:
        row=db.get(AccountSession,digest(raw))
        if not row or row.expires<=int(time.time()):return None
        account=db.get(Account,row.account_id)
        if not account or (settings.require_email_verification and not account.verified) or account.role!='user':return None
        return Principal(subject=account.id,tenant=account.tenant,role=account.role)


class EmailIn(Strict):
    email:str=Field(min_length=3,max_length=254)
    @field_validator('email')
    @classmethod
    def email_shape(cls,value):
        value=value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Valid email required')
        return value

class Credentials(EmailIn):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    password:str=Field(min_length=12,max_length=128)

class ActionIn(Strict):
    token:str=Field(min_length=32,max_length=256)

class ResetIn(ActionIn):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    password:str=Field(min_length=12,max_length=128)


def send_action(settings,email,purpose,token):
    link=settings.public_app_url.rstrip('/')+'/login#'+purpose+'='+token
    message=EmailMessage();message['Subject']='AYUNEX — '+('verify your email' if purpose=='verify' else 'reset your password')
    message['From']=settings.mail_from or 'local@ayunex.invalid';message['To']=email
    message.set_content('Open this link within 30 minutes:\n'+link+'\n\nIf you did not request this, ignore this message.')
    if settings.smtp_host:
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context());smtp.login(settings.smtp_user,settings.smtp_password);smtp.send_message(message)
    elif settings.environment in {'development','test'}:
        outbox=Path(__file__).resolve().parents[1]/'.mail-outbox';outbox.mkdir(mode=0o700,exist_ok=True)
        target=outbox/(secrets.token_hex(12)+'.eml')
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(message.as_string())
    else:raise RuntimeError('Email delivery is not configured')


def accounts_router(sessions,settings):
    router=APIRouter(prefix='/api/v1/auth',tags=['Accounts'])
    @router.get('/options')
    def options():
        return {'email_verification_required':settings.require_email_verification,'password_reset_available':bool(settings.smtp_host)}
    # Shared Redis in production; bounded local limiter in development.
    from dataclasses import replace
    limiter=RequestGuard(None,replace(settings,rate_limit=10))
    lock=threading.Lock()
    def guard(request,email=''):
        if settings.auth_mode!='builtin':raise HTTPException(404,'Use the configured identity provider')
        csrf(request)
        ip=request.client.host if request.client else 'unknown'
        try:
            with lock:allowed=limiter.allowed('auth:'+ip) and (not email or limiter.allowed('auth-email:'+digest(email)))
        except Exception:raise HTTPException(503,'Authentication limiter unavailable') from None
        if not allowed:raise HTTPException(429,'Too many authentication attempts; retry later')
    def issue_action(db,account,purpose):
        db.execute(delete(AccountAction).where(AccountAction.account_id==account.id,AccountAction.purpose==purpose))
        token=secrets.token_urlsafe(32)
        db.add(AccountAction(digest=digest(token),account_id=account.id,purpose=purpose,expires=int(time.time())+1800))
        try:send_action(settings,account.email,purpose,token)
        except Exception:raise HTTPException(503,'Email delivery unavailable; retry later') from None
    @router.post('/signup',status_code=202)
    def signup(body:Credentials,request:Request):
        guard(request,body.email)
        with sessions() as db:
            account=db.scalar(select(Account).where(Account.email==body.email).with_for_update())
            if not account:
                account=Account(email=body.email,password_hash=password_hash(body.password));db.add(account);db.flush()
            if settings.require_email_verification and not account.verified:
                account.password_hash=password_hash(body.password)
                issue_action(db,account,'verify')
            db.commit()
        return {'message':'If eligible, a verification email has been sent. Check your inbox.' if settings.require_email_verification else 'You can now sign in using your email and password. If you already have an account, use its existing password.'}
    @router.post('/verify-email')
    def verify(body:ActionIn,request:Request):
        guard(request)
        with sessions() as db:
            action=db.get(AccountAction,digest(body.token))
            if not action or action.purpose!='verify' or action.expires<=int(time.time()):raise HTTPException(400,'Invalid or expired verification link')
            account=db.scalar(select(Account).where(Account.id==action.account_id).with_for_update())
            consumed=db.execute(delete(AccountAction).where(AccountAction.digest==action.digest))
            if consumed.rowcount!=1:raise HTTPException(400,'Link already used')
            account.verified=True;db.commit()
        return {'message':'Email verified. You can now sign in.'}
    @router.post('/login')
    def login(body:Credentials,request:Request,response:Response):
        guard(request,body.email)
        with sessions() as db:
            account=db.scalar(select(Account).where(Account.email==body.email).with_for_update())
            valid=password_matches(body.password,account.password_hash if account else _DUMMY_HASH)
            if not account or not valid or (settings.require_email_verification and not account.verified) or account.locked_until>int(time.time()):
                if account and not valid:
                    account.failures+=1
                    if account.failures>=5:account.locked_until=int(time.time())+900;account.failures=0
                    db.commit()
                raise HTTPException(401,'Invalid credentials or temporarily locked account' if not settings.require_email_verification else 'Invalid credentials, unverified email or temporarily locked account')
            account.failures=0;account.locked_until=0
            raw=secrets.token_urlsafe(32)
            db.execute(delete(AccountSession).where(AccountSession.expires<=int(time.time())))
            db.add(AccountSession(digest=digest(raw),account_id=account.id,expires=int(time.time())+86400));db.commit()
            response.set_cookie(cookie_name(settings),raw,httponly=True,secure=settings.environment=='production',samesite='strict',max_age=86400,path='/')
            return {'principal':{'subject':account.id,'tenant':account.tenant,'role':account.role}}
    @router.post('/logout')
    def logout(request:Request,response:Response):
        csrf(request)
        raw=request.cookies.get(cookie_name(settings),'')
        with sessions() as db:
            db.execute(delete(AccountSession).where(AccountSession.digest==digest(raw)));db.commit()
        response.delete_cookie(cookie_name(settings),path='/',secure=settings.environment=='production',httponly=True,samesite='strict')
        return {'message':'Signed out'}
    @router.post('/forgot-password',status_code=202)
    def forgot(body:EmailIn,request:Request):
        guard(request,body.email)
        if settings.environment!='test' and not settings.smtp_host:raise HTTPException(503,'Password reset is not available until email delivery is configured')
        with sessions() as db:
            account=db.scalar(select(Account).where(Account.email==body.email))
            if account:issue_action(db,account,'reset')
            db.commit()
        return {'message':'If eligible, a password-reset email has been sent.'}
    @router.post('/reset-password')
    def reset(body:ResetIn,request:Request):
        guard(request)
        with sessions() as db:
            action=db.get(AccountAction,digest(body.token))
            if not action or action.purpose!='reset' or action.expires<=int(time.time()):raise HTTPException(400,'Invalid or expired reset link')
            account=db.scalar(select(Account).where(Account.id==action.account_id).with_for_update())
            consumed=db.execute(delete(AccountAction).where(AccountAction.digest==action.digest))
            if consumed.rowcount!=1:raise HTTPException(400,'Link already used')
            account.password_hash=password_hash(body.password);account.failures=0;account.locked_until=0
            db.execute(delete(AccountSession).where(AccountSession.account_id==account.id));db.commit()
        return {'message':'Password changed. All existing sessions revoked.'}
    return router
