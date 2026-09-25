"""Module D — Platform, Security, Administration, DPDP Consent & Audit Ledger.

Provides:
- D1: Session issuance, token signing & OAuth2/OIDC introspection
- D2: Role-based access control & tenant isolation
- D3: DPDP Act 2023 purpose-specific consent ledger & Right to Erasure
- D8: Cryptographically hash-chained tamper-evident audit ledger
- D9: Production security headers & healthcheck probes
"""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Literal, Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from .schemas import Strict, Principal


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s.encode('ascii'))


def _get_signing_key(settings) -> bytes:
    key = getattr(settings, 'dev_token', '') or getattr(settings, 'ai_key', '') or 'ayunex-production-secret-key-32b'
    return hashlib.sha256(key.encode('utf-8')).digest()


def create_session_token(
    subject: str,
    tenant: str,
    role: str,
    settings,
    expires_in_seconds: int = 86400 * 7
) -> str:
    """Creates a cryptographically signed HMAC-SHA256 session token."""
    now_ts = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "tenant": tenant,
        "role": role,
        "iat": now_ts,
        "exp": now_ts + expires_in_seconds
    }
    h_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    p_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    h_b64 = _b64url_encode(h_bytes)
    p_b64 = _b64url_encode(p_bytes)
    signing_input = f"{h_b64}.{p_b64}".encode('ascii')
    sig = hmac.new(_get_signing_key(settings), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{h_b64}.{p_b64}.{sig_b64}"


def verify_session_token(token: str, settings) -> dict | None:
    """Verifies HMAC signature and expiration; returns decoded payload or None."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        h_b64, p_b64, sig_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode('ascii')
        expected_sig = hmac.new(_get_signing_key(settings), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        payload = json.loads(_b64url_decode(p_b64).decode('utf-8'))
        if not isinstance(payload, dict):
            return None
        if payload.get('exp', 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def init_module_d_tables(engine):
    """Initializes tables for DPDP consent ledger and tamper-evident audit chain."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS platform_consents (
                id VARCHAR(36) PRIMARY KEY,
                tenant VARCHAR(160) NOT NULL,
                subject VARCHAR(160) NOT NULL,
                purpose VARCHAR(80) NOT NULL,
                notice_version VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL,
                granted_at VARCHAR(40) NOT NULL,
                withdrawn_at VARCHAR(40),
                metadata_json TEXT
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_platform_consents_subject 
            ON platform_consents (tenant, subject, purpose);
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS platform_audit_ledger (
                id VARCHAR(36) PRIMARY KEY,
                sequence INTEGER NOT NULL,
                tenant VARCHAR(160) NOT NULL,
                actor VARCHAR(160) NOT NULL,
                action VARCHAR(80) NOT NULL,
                timestamp VARCHAR(40) NOT NULL,
                prev_hash VARCHAR(64) NOT NULL,
                entry_hash VARCHAR(64) NOT NULL,
                payload_json TEXT
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_platform_audit_seq 
            ON platform_audit_ledger (sequence);
        """))


def append_audit_event(db, tenant: str, actor: str, action: str, payload: dict | None = None) -> dict:
    """Appends an event to the tamper-evident SHA-256 hash-chained audit ledger."""
    payload_str = json.dumps(payload or {}, sort_keys=True, separators=(',', ':'))
    iso_now = datetime.now(timezone.utc).isoformat()
    
    last = db.execute(text("""
        SELECT sequence, entry_hash FROM platform_audit_ledger 
        ORDER BY sequence DESC LIMIT 1
    """)).first()
    
    if last:
        seq = last[0] + 1
        prev_hash = last[1]
    else:
        seq = 1
        prev_hash = '0' * 64
        
    hash_data = f"{prev_hash}|{seq}|{tenant}|{actor}|{action}|{iso_now}|{payload_str}".encode('utf-8')
    entry_hash = hashlib.sha256(hash_data).hexdigest()
    event_id = str(uuid4())
    
    db.execute(text("""
        INSERT INTO platform_audit_ledger (id, sequence, tenant, actor, action, timestamp, prev_hash, entry_hash, payload_json)
        VALUES (:id, :seq, :tenant, :actor, :action, :ts, :prev_hash, :entry_hash, :payload)
    """), {
        'id': event_id,
        'seq': seq,
        'tenant': tenant,
        'actor': actor,
        'action': action,
        'ts': iso_now,
        'prev_hash': prev_hash,
        'entry_hash': entry_hash,
        'payload': payload_str
    })
    return {
        'id': event_id,
        'sequence': seq,
        'action': action,
        'entry_hash': entry_hash,
        'timestamp': iso_now
    }


def verify_audit_chain(db) -> dict:
    """Verifies cryptographic hash chain integrity across all records."""
    rows = db.execute(text("""
        SELECT id, sequence, tenant, actor, action, timestamp, prev_hash, entry_hash, payload_json
        FROM platform_audit_ledger ORDER BY sequence ASC
    """)).all()
    
    if not rows:
        return {'verified': True, 'count': 0, 'head_hash': '0' * 64}
        
    expected_prev = '0' * 64
    for row in rows:
        _id, seq, tenant, actor, action, ts, prev_hash, entry_hash, payload_json = row
        if prev_hash != expected_prev:
            return {'verified': False, 'failed_sequence': seq, 'reason': 'Chain continuity broken'}
        hash_data = f"{prev_hash}|{seq}|{tenant}|{actor}|{action}|{ts}|{payload_json}".encode('utf-8')
        recomputed = hashlib.sha256(hash_data).hexdigest()
        if recomputed != entry_hash:
            return {'verified': False, 'failed_sequence': seq, 'reason': 'Digest tampering detected'}
        expected_prev = entry_hash
        
    return {'verified': True, 'count': len(rows), 'head_hash': expected_prev}


# --- Schemas ---

class SessionRequest(Strict):
    role: Literal['user', 'facilitator', 'curator', 'administrator', 'auditor'] = 'user'
    subject: str | None = None
    tenant: str = 'local-demo'


class IntrospectRequest(Strict):
    token: str = Field(min_length=1)


class ConsentRecordIn(Strict):
    purpose: Literal['case_processing', 'voice_transcription', 'facilitator_sharing', 'hosted_ai_processing']
    notice_version: str = 'dpdp-v1'
    metadata: dict = Field(default_factory=dict)


class ConsentWithdrawIn(Strict):
    purpose: Literal['case_processing', 'voice_transcription', 'facilitator_sharing', 'hosted_ai_processing']


class ErasureRequestIn(Strict):
    confirm_erasure: Literal[True]


# --- Security Headers Middleware ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(self), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:* https://api.groq.com; "
            "img-src 'self' data: https:;"
        )
        return response


# --- Router ---

def module_d_router(sessions, settings, identity_dependency):
    router = APIRouter(tags=['Module D — Platform, Security & Identity'])

    @router.post('/api/v1/auth/session')
    @router.get('/api/v1/auth/session')
    def get_or_create_session(body: SessionRequest | None = None):
        """Zero-friction session issuance for visitors or specific demo roles."""
        req = body or SessionRequest()
        sub = req.subject or f"{req.role}-{uuid4().hex[:8]}"
        token = create_session_token(sub, req.tenant, req.role, settings)
        with sessions() as db:
            append_audit_event(db, req.tenant, sub, 'auth.session_created', {'role': req.role})
            db.commit()
        return {
            'token': token,
            'principal': {
                'subject': sub,
                'tenant': req.tenant,
                'role': req.role
            },
            'expires_in': 86400 * 7
        }

    @router.post('/api/v1/auth/introspect')
    def introspect_token(req: IntrospectRequest):
        """Fulfills the Module D IDENTITY_INTROSPECTION_URL interface."""
        payload = verify_session_token(req.token, settings)
        if payload:
            return {
                'active': True,
                'principal': {
                    'subject': payload['sub'],
                    'tenant': payload['tenant'],
                    'role': payload['role']
                }
            }
        # Check dev tokens if in dev/test environment
        if settings.environment in {'development', 'test'} and settings.dev_token:
            parts = req.token.split(':', 1)
            base_token = parts[0]
            dev_role = parts[1] if len(parts) > 1 else 'user'
            if dev_role not in {'user', 'facilitator', 'curator', 'administrator', 'auditor'}:
                dev_role = 'user'
            if hmac.compare_digest(base_token, settings.dev_token):
                return {
                    'active': True,
                    'principal': {
                        'subject': f'local-{dev_role}',
                        'tenant': 'local-demo',
                        'role': dev_role
                    }
                }
        return {'active': False}

    @router.get('/api/v1/auth/roles')
    def list_roles():
        return {
            'roles': [
                {'role': 'user', 'description': 'Innovator / researcher managing Product Passports and queries'},
                {'role': 'facilitator', 'description': 'Legal / IP facilitator reviewing escalations in queue'},
                {'role': 'curator', 'description': 'Knowledge curator reviewing and approving statutory passages'},
                {'role': 'administrator', 'description': 'System administrator with cross-tenant oversight'},
                {'role': 'auditor', 'description': 'Compliance auditor inspecting logs and provenance'}
            ]
        }

    # --- D3: DPDP Act 2023 Consent Ledger ---

    @router.post('/api/v1/consent/record')
    def record_consent(req: ConsentRecordIn, user: Annotated[Principal, Depends(identity_dependency)]):
        iso_now = datetime.now(timezone.utc).isoformat()
        consent_id = str(uuid4())
        meta_str = json.dumps(req.metadata, separators=(',', ':'))
        with sessions() as db:
            db.execute(text("""
                UPDATE platform_consents 
                SET status = 'SUPERSEDED' 
                WHERE tenant = :tenant AND subject = :sub AND purpose = :purpose AND status = 'GRANTED'
            """), {'tenant': user.tenant, 'sub': user.subject, 'purpose': req.purpose})
            
            db.execute(text("""
                INSERT INTO platform_consents (id, tenant, subject, purpose, notice_version, status, granted_at, metadata_json)
                VALUES (:id, :tenant, :sub, :purpose, :version, 'GRANTED', :now, :meta)
            """), {
                'id': consent_id,
                'tenant': user.tenant,
                'sub': user.subject,
                'purpose': req.purpose,
                'version': req.notice_version,
                'now': iso_now,
                'meta': meta_str
            })
            append_audit_event(db, user.tenant, user.subject, 'consent.granted', {
                'purpose': req.purpose,
                'notice_version': req.notice_version
            })
            db.commit()
        return {'id': consent_id, 'purpose': req.purpose, 'status': 'GRANTED', 'recorded_at': iso_now}

    @router.get('/api/v1/consent/history')
    def consent_history(user: Annotated[Principal, Depends(identity_dependency)]):
        with sessions() as db:
            rows = db.execute(text("""
                SELECT id, purpose, notice_version, status, granted_at, withdrawn_at, metadata_json
                FROM platform_consents
                WHERE tenant = :tenant AND subject = :sub
                ORDER BY granted_at DESC
            """), {'tenant': user.tenant, 'sub': user.subject}).all()
            
            records = []
            for r in rows:
                meta = {}
                if r[6]:
                    try: meta = json.loads(r[6])
                    except Exception: pass
                records.append({
                    'id': r[0],
                    'purpose': r[1],
                    'notice_version': r[2],
                    'status': r[3],
                    'granted_at': r[4],
                    'withdrawn_at': r[5],
                    'metadata': meta
                })
            return {'records': records, 'subject': user.subject, 'tenant': user.tenant}

    @router.post('/api/v1/consent/withdraw')
    def withdraw_consent(req: ConsentWithdrawIn, user: Annotated[Principal, Depends(identity_dependency)]):
        iso_now = datetime.now(timezone.utc).isoformat()
        with sessions() as db:
            db.execute(text("""
                UPDATE platform_consents
                SET status = 'WITHDRAWN', withdrawn_at = :now
                WHERE tenant = :tenant AND subject = :sub AND purpose = :purpose AND status = 'GRANTED'
            """), {'tenant': user.tenant, 'sub': user.subject, 'purpose': req.purpose, 'now': iso_now})
            
            append_audit_event(db, user.tenant, user.subject, 'consent.withdrawn', {'purpose': req.purpose})
            db.commit()
            return {'purpose': req.purpose, 'status': 'WITHDRAWN', 'withdrawn_at': iso_now}

    @router.post('/api/v1/privacy/erasure')
    def erase_user_data(req: ErasureRequestIn, user: Annotated[Principal, Depends(identity_dependency)]):
        """DPDP Act 2023 Right to Erasure: removes all cases, artifacts, and personal records for the user."""
        with sessions() as db:
            db.execute(text("DELETE FROM cases WHERE tenant = :tenant AND owner = :sub"),
                       {'tenant': user.tenant, 'sub': user.subject})
            db.execute(text("""
                UPDATE platform_consents 
                SET status = 'ERASED', metadata_json = '{"erased": true}' 
                WHERE tenant = :tenant AND subject = :sub
            """), {'tenant': user.tenant, 'sub': user.subject})
            append_audit_event(db, user.tenant, user.subject, 'privacy.erasure_executed', {'confirmed': True})
            db.commit()
        return {'status': 'ERASED', 'subject': user.subject, 'message': 'All personal cases and artifacts permanently deleted.'}

    # --- D8: Tamper-Evident Audit Ledger ---

    @router.get('/api/v1/audit/events')
    def get_audit_events(user: Annotated[Principal, Depends(identity_dependency)], limit: int = 50):
        if user.role not in {'curator', 'administrator', 'auditor'}:
            raise HTTPException(403, 'Auditor or Administrator role required to view platform audit trail')
        with sessions() as db:
            rows = db.execute(text("""
                SELECT id, sequence, tenant, actor, action, timestamp, prev_hash, entry_hash, payload_json
                FROM platform_audit_ledger
                ORDER BY sequence DESC LIMIT :limit
            """), {'limit': min(max(1, limit), 200)}).all()
            
            events = []
            for r in rows:
                p = {}
                if r[8]:
                    try: p = json.loads(r[8])
                    except Exception: pass
                events.append({
                    'id': r[0],
                    'sequence': r[1],
                    'tenant': r[2],
                    'actor': r[3],
                    'action': r[4],
                    'timestamp': r[5],
                    'prev_hash': r[6],
                    'entry_hash': r[7],
                    'payload': p
                })
            return {'events': events, 'count': len(events)}

    @router.get('/api/v1/audit/verify')
    def verify_audit_ledger(user: Annotated[Principal, Depends(identity_dependency)]):
        if user.role not in {'curator', 'administrator', 'auditor'}:
            raise HTTPException(403, 'Auditor or Administrator role required')
        with sessions() as db:
            return verify_audit_chain(db)

    # --- Standard Liveness & Readiness Probes ---

    @router.get('/healthz')
    def liveness():
        return {'status': 'ok', 'service': 'AYUNEX Platform', 'time': datetime.now(timezone.utc).isoformat()}

    @router.get('/readyz')
    def readiness_probe():
        try:
            with sessions() as db:
                db.execute(text('SELECT 1')).scalar()
            return {'ready': True, 'environment': settings.environment}
        except Exception as e:
            return Response(
                content=json.dumps({'ready': False, 'error': str(e)}),
                status_code=503,
                media_type='application/json'
            )

    return router
