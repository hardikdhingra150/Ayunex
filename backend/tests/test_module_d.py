"""Comprehensive tests for Module D: Platform, Security, Administration, DPDP Consent & Audit."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "module_d_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_file}",
        environment="development",
        dev_token="test-dev-token-secret-12345-very-long-32-chars"
    )
    from app.models import Base
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as tc:
        yield tc, app


def test_auth_session_and_roles(client):
    tc, app = client
    # 1. Test public session creation (default role: user)
    res = tc.post('/api/v1/auth/session')
    assert res.status_code == 200
    data = res.json()
    assert 'token' in data
    assert data['principal']['role'] == 'user'
    token = data['token']

    # Use this token against /api/v1/me
    me_res = tc.get('/api/v1/me', headers={'Authorization': f'Bearer {token}'})
    assert me_res.status_code == 200
    assert me_res.json()['role'] == 'user'

    # 2. Test facilitator session creation
    fac_res = tc.post('/api/v1/auth/session', json={'role': 'facilitator'})
    assert fac_res.status_code == 200
    fac_token = fac_res.json()['token']
    fac_me = tc.get('/api/v1/me', headers={'Authorization': f'Bearer {fac_token}'})
    assert fac_me.status_code == 200
    assert fac_me.json()['role'] == 'facilitator'

    # 3. Test roles listing
    roles_res = tc.get('/api/v1/auth/roles')
    assert roles_res.status_code == 200
    roles = [r['role'] for r in roles_res.json()['roles']]
    assert 'user' in roles
    assert 'facilitator' in roles
    assert 'curator' in roles
    assert 'administrator' in roles


def test_auth_introspect(client):
    tc, app = client
    # 1. Valid token introspection
    session_res = tc.post('/api/v1/auth/session', json={'role': 'curator'})
    token = session_res.json()['token']
    
    intro_res = tc.post('/api/v1/auth/introspect', json={'token': token})
    assert intro_res.status_code == 200
    intro_data = intro_res.json()
    assert intro_data['active'] is True
    assert intro_data['principal']['role'] == 'curator'

    # 2. Invalid token introspection
    bad_intro = tc.post('/api/v1/auth/introspect', json={'token': 'invalid.token.here'})
    assert bad_intro.status_code == 200
    assert bad_intro.json()['active'] is False

    # 3. Dev token introspection
    dev_intro = tc.post('/api/v1/auth/introspect', json={'token': 'test-dev-token-secret-12345-very-long-32-chars:administrator'})
    assert dev_intro.status_code == 200
    assert dev_intro.json()['active'] is True
    assert dev_intro.json()['principal']['role'] == 'administrator'


def test_dpdp_consent_lifecycle(client):
    tc, app = client
    # Create session
    session = tc.post('/api/v1/auth/session', json={'role': 'user'}).json()
    headers = {'Authorization': f"Bearer {session['token']}"}

    # Record consent
    grant = tc.post('/api/v1/consent/record', json={
        'purpose': 'voice_transcription',
        'notice_version': 'dpdp-v1',
        'metadata': {'preferred_language': 'hi'}
    }, headers=headers)
    assert grant.status_code == 200
    assert grant.json()['status'] == 'GRANTED'

    # Check history
    hist = tc.get('/api/v1/consent/history', headers=headers)
    assert hist.status_code == 200
    records = hist.json()['records']
    assert len(records) >= 1
    assert records[0]['purpose'] == 'voice_transcription'
    assert records[0]['status'] == 'GRANTED'

    # Withdraw consent
    withdraw = tc.post('/api/v1/consent/withdraw', json={'purpose': 'voice_transcription'}, headers=headers)
    assert withdraw.status_code == 200
    assert withdraw.json()['status'] == 'WITHDRAWN'

    # Verify updated history
    hist2 = tc.get('/api/v1/consent/history', headers=headers)
    records2 = hist2.json()['records']
    assert records2[0]['status'] == 'WITHDRAWN'
    assert records2[0]['withdrawn_at'] is not None


def test_tamper_evident_audit_ledger(client):
    tc, app = client
    admin_session = tc.post('/api/v1/auth/session', json={'role': 'administrator'}).json()
    admin_headers = {'Authorization': f"Bearer {admin_session['token']}"}

    # Verify initial audit chain
    verify_res = tc.get('/api/v1/audit/verify', headers=admin_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()['verified'] is True
    assert verify_res.json()['count'] >= 1

    # Check events listing
    events_res = tc.get('/api/v1/audit/events', headers=admin_headers)
    assert events_res.status_code == 200
    events = events_res.json()['events']
    assert len(events) >= 1
    # Verify hash structure
    assert len(events[0]['entry_hash']) == 64
    assert len(events[0]['prev_hash']) == 64

    # Tamper detection test: directly mutate database payload
    with app.state.sessions() as db:
        db.execute(text("UPDATE platform_audit_ledger SET action = 'tampered_action' WHERE sequence = 1"))
        db.commit()

    # Chain verification must now fail
    tampered_verify = tc.get('/api/v1/audit/verify', headers=admin_headers)
    assert tampered_verify.status_code == 200
    assert tampered_verify.json()['verified'] is False
    assert 'Digest tampering detected' in tampered_verify.json()['reason']


def test_security_headers_and_healthz(client):
    tc, app = client
    # Health checks
    hz = tc.get('/healthz')
    assert hz.status_code == 200
    assert hz.json()['status'] == 'ok'

    rz = tc.get('/readyz')
    assert rz.status_code == 200
    assert rz.json()['ready'] is True

    # Security headers check
    res = tc.get('/health')
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('X-Frame-Options') == 'DENY'
    assert res.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'microphone=(self)' in res.headers.get('Permissions-Policy', '')


def test_privacy_erasure(client):
    tc, app = client
    user_session = tc.post('/api/v1/auth/session', json={'role': 'user'}).json()
    headers = {'Authorization': f"Bearer {user_session['token']}"}

    # Create a case for this user
    case_res = tc.post('/api/v1/cases', json={
        'title': 'Test Case to Erase',
        'query_kind': 'PRODUCT_SPECIFIC',
        'jurisdiction': {'layer': 'NATIONAL', 'country': 'IN'},
        'as_of_date': '2026-09-10',
        'consent': {'accepted': True, 'notice_version': 'case-notice-v1'}
    }, headers=headers)
    assert case_res.status_code == 201
    case_id = case_res.json()['id']

    # Confirm case exists
    get_res = tc.get(f'/api/v1/cases/{case_id}', headers=headers)
    assert get_res.status_code == 200

    # Request erasure
    erase_res = tc.post('/api/v1/privacy/erasure', json={'confirm_erasure': True}, headers=headers)
    assert erase_res.status_code == 200
    assert erase_res.json()['status'] == 'ERASED'

    # Case should now be gone
    get_res2 = tc.get(f'/api/v1/cases/{case_id}', headers=headers)
    assert get_res2.status_code == 404


def test_spa_serving_and_fallback(client):
    tc, app = client
    # Root route should serve index.html (since frontend/dist exists)
    root_res = tc.get('/')
    assert root_res.status_code == 200
    assert 'text/html' in root_res.headers.get('content-type', '')
    assert '<html' in root_res.text.lower() or '<!doctype' in root_res.text.lower()

    # Client-side SPA route fallback should also return index.html
    spa_res = tc.get('/cases/test-case-id')
    assert spa_res.status_code == 200
    assert 'text/html' in spa_res.headers.get('content-type', '')

    # Non-existent API route should return 404 JSON, not HTML
    api_404 = tc.get('/api/v1/nonexistent')
    assert api_404.status_code == 404
    assert api_404.headers.get('content-type', '').startswith('application/json')

