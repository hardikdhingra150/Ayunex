import secrets
import json
import httpx
from typing import Annotated
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from .schemas import Principal, GuidanceAnswer


bearer=HTTPBearer(auto_error=False)


def bounded_post(url, payload, service_token, timeout, max_bytes):
    """Bound upstream bodies while streaming, before parsing or allocation."""
    with httpx.stream('POST',url,json=payload,headers={'Authorization':'Bearer '+service_token},
                      timeout=timeout,follow_redirects=False,trust_env=False) as response:
        response.raise_for_status()
        data=bytearray()
        for chunk in response.iter_bytes():
            if len(data)+len(chunk)>max_bytes:raise ValueError('Upstream response exceeds byte limit')
            data.extend(chunk)
        return json.loads(data)


def identity(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    config = request.app.state.settings
    authorization = request.headers.get('authorization', '')
    if credentials is None and config.auth_mode=='builtin':
        from .accounts import cookie_identity
        principal=cookie_identity(request)
        if principal:return principal
    if credentials is None or len(authorization)>8192:
        raise HTTPException(401, 'Bearer authentication required')
    token = credentials.credentials
    from .module_d import verify_session_token
    session_payload = verify_session_token(token, config)
    if session_payload:
        return Principal(
            subject=session_payload['sub'],
            tenant=session_payload['tenant'],
            role=session_payload['role']
        )
    if config.environment in {'development','test'} and config.dev_token:
        if secrets.compare_digest(token, config.dev_token):
            return Principal(subject='local-developer', tenant='local-demo', role='user')
    if not config.identity_url:
        raise HTTPException(401, 'Module D identity unavailable or invalid credential')
    try:
        data=bounded_post(config.identity_url,{'token':token},config.identity_service_token,5,65536)
        if not isinstance(data,dict):raise ValueError('Invalid identity response')
        if data.get('active') is not True:
            raise HTTPException(401, 'Inactive identity')
        return Principal.model_validate(data['principal'])
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, ValidationError):
        raise HTTPException(503, 'Identity verification failed; access denied') from None


class GuidanceClient:
    def __init__(self, settings):
        self.settings=settings

    def generate(self, payload):
        if not self.settings.guidance_url:
            raise HTTPException(503, 'Module C is not configured. No fabricated answer will be returned.')
        try:
            data=bounded_post(self.settings.guidance_url,payload,self.settings.guidance_service_token,20,2_000_000)
            result=GuidanceAnswer.model_validate(data)
            if result.context_hash!=payload['context_hash'] or result.request_id!=payload['request_id'] or result.jurisdiction.model_dump()!=payload['jurisdiction'] or result.as_of_date.isoformat()!=payload['as_of_date']:
                raise ValueError('Context mismatch')
            return result.model_dump(mode='json')
        except httpx.TimeoutException:
            raise HTTPException(504, 'Module C timed out; retry safely with the same idempotency key') from None
        except (httpx.HTTPError, ValueError, ValidationError):
            raise HTTPException(502, 'Module C response failed evidence/context policy') from None
