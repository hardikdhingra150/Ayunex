from test_module_d import client
from sqlalchemy import select
from app.models import Account,AccountSession
from app.accounts import password_matches
import secrets
import pytest

HEADERS={'X-CSRF-Protection':'1'}
PASSWORD=secrets.token_urlsafe(24)

@pytest.fixture(autouse=True)
def verification_mode(client):
    client[1].state.settings.require_email_verification=True
    client[1].state.settings.environment='test'

def register(c,monkeypatch,email='person@example.org'):
    mail=[]
    monkeypatch.setattr('app.accounts.send_action',lambda settings,address,purpose,token:mail.append((purpose,token)))
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json={'email':email,'password':PASSWORD}).status_code==202
    assert c.post('/api/v1/auth/verify-email',headers=HEADERS,json={'token':mail[-1][1]}).status_code==200
    return mail

def test_verified_login_logout_cookie(client,monkeypatch):
    c,app=client;register(c,monkeypatch)
    response=c.post('/api/v1/auth/login',headers=HEADERS,json={'email':'person@example.org','password':PASSWORD})
    assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
    assert 'token' not in response.json()
    assert c.get('/api/v1/me').status_code==200
    assert c.post('/api/v1/auth/logout').status_code==403
    assert c.post('/api/v1/auth/logout',headers=HEADERS).status_code==200
    assert c.get('/api/v1/me').status_code==401
    with app.state.sessions() as db:
        account=db.scalar(select(Account));assert account.password_hash!=PASSWORD
        assert password_matches(PASSWORD,account.password_hash)
        assert db.scalar(select(AccountSession)) is None

def test_reset_revokes_sessions_and_token_single_use(client,monkeypatch):
    c,_=client;mail=register(c,monkeypatch)
    c.post('/api/v1/auth/login',headers=HEADERS,json={'email':'person@example.org','password':PASSWORD})
    assert c.post('/api/v1/auth/forgot-password',headers=HEADERS,json={'email':'person@example.org'}).status_code==202
    token=mail[-1][1]
    body={'token':token,'password':secrets.token_urlsafe(24)}
    assert c.post('/api/v1/auth/reset-password',headers=HEADERS,json=body).status_code==200
    assert c.get('/api/v1/me').status_code==401
    assert c.post('/api/v1/auth/reset-password',headers=HEADERS,json=body).status_code==400

def test_csrf_unverified_and_no_role_assignment(client,monkeypatch):
    c,_=client
    monkeypatch.setattr('app.accounts.send_action',lambda *args:None)
    body={'email':'person@example.org','password':PASSWORD}
    assert c.post('/api/v1/auth/signup',json=body).status_code==403
    assert c.post('/api/v1/auth/signup',headers={**HEADERS,'Origin':'https://evil.example'},json=body).status_code==403
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json={**body,'role':'administrator'}).status_code==422
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json=body).status_code==202
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=body).status_code==401

def test_unverified_registration_replaces_unverified_password(client,monkeypatch):
    c,_=client;mail=[]
    monkeypatch.setattr('app.accounts.send_action',lambda settings,address,purpose,token:mail.append(token))
    body={'email':'person@example.org','password':PASSWORD}
    c.post('/api/v1/auth/signup',headers=HEADERS,json=body)
    replacement={**body,'password':secrets.token_urlsafe(24)}

    c.post('/api/v1/auth/signup',headers=HEADERS,json=replacement)
    assert c.post('/api/v1/auth/verify-email',headers=HEADERS,json={'token':mail[0]}).status_code==400
    assert c.post('/api/v1/auth/verify-email',headers=HEADERS,json={'token':mail[1]}).status_code==200
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=body).status_code==401
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=replacement).status_code==200

def test_showcase_signup_login_without_email_and_duplicate_cannot_reset(client,monkeypatch):
    c,app=client;app.state.settings.require_email_verification=False
    monkeypatch.setattr('app.accounts.send_action',lambda *args:pytest.fail('Signup must not send email'))
    body={'email':'showcase@example.org','password':secrets.token_urlsafe(24)}
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json=body).status_code==202
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=body).status_code==200
    assert c.get('/api/v1/me').status_code==200
    c.post('/api/v1/auth/logout',headers=HEADERS)
    replacement={**body,'password':secrets.token_urlsafe(24)}
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json=replacement).status_code==202
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=replacement).status_code==401
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=body).status_code==200
    with app.state.sessions() as db:
        assert db.scalar(select(Account)).verified is False

def test_existing_unverified_account_can_login_in_showcase_mode(client,monkeypatch):
    c,app=client
    monkeypatch.setattr('app.accounts.send_action',lambda *args:None)
    body={'email':'existing@example.org','password':secrets.token_urlsafe(24)}
    c.post('/api/v1/auth/signup',headers=HEADERS,json=body)
    app.state.settings.require_email_verification=False
    assert c.post('/api/v1/auth/login',headers=HEADERS,json=body).status_code==200

def test_account_profile_is_persisted_and_returned_only_to_its_owner(client):
    c,app=client;app.state.settings.require_email_verification=False
    body={'email':'profile@example.org','password':secrets.token_urlsafe(24),'display_name':'  Example   User  '}
    assert c.post('/api/v1/auth/signup',headers=HEADERS,json=body).status_code==202
    assert c.post('/api/v1/auth/login',headers=HEADERS,json={k:body[k] for k in ('email','password')}).status_code==200
    me=c.get('/api/v1/me').json()
    assert me['display_name']=='Example User' and me['email']==body['email']
    assert 'password_hash' not in me
    with app.state.sessions() as db:
        assert db.scalar(select(Account)).display_name=='Example User'
    c.post('/api/v1/auth/logout',headers=HEADERS)
    assert c.get('/api/v1/me').status_code==401
