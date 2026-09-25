"""Ingress limits; no request bodies, queries or credentials enter logs."""
import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from uuid import uuid4
from starlette.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError

log=logging.getLogger('ayunex.requests')
log.setLevel(logging.INFO)
if not log.handlers:log.addHandler(logging.StreamHandler())
log.propagate=False


class RequestGuard:
    def __init__(self,app,settings):
        self.app=app;self.settings=settings;self.local=OrderedDict()
        self.redis=Redis.from_url(settings.redis_url,socket_timeout=2,socket_connect_timeout=2) if settings.redis_url else None

    def allowed(self,key):
        bucket=int(time.time()//60)
        key='ayunex:rate:'+hashlib.sha256(key.encode()).hexdigest()+':'+str(bucket)
        if self.redis:
            count=self.redis.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],70) end; return n",1,key)
        else:
            count=self.local.get(key,0)+1;self.local[key]=count
            while len(self.local)>10000:self.local.popitem(last=False)
        return count<=self.settings.rate_limit

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        request_id=str(uuid4());scope['request_id']=request_id
        async def reject(status,message):
            await JSONResponse({'detail':message,'request_id':request_id},status_code=status,headers={'X-Request-ID':request_id,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',**({'Retry-After':'60'} if status==429 else {})})(scope,receive,send)
        # Health probes are cheap and do not consume user API budgets.
        if not scope['path'].startswith('/health'):
            try:allowed=await asyncio.to_thread(self.allowed,(scope.get('client') or ['unknown'])[0])
            except RedisError:return await reject(503,'Request limiter unavailable')
            if not allowed:return await reject(429,'Request limit exceeded')
        headers=dict(scope['headers'])
        if headers.get(b'content-encoding',b'identity') not in (b'identity',):return await reject(415,'Compressed request bodies are not accepted')
        try:declared=int(headers.get(b'content-length',b'0'))
        except ValueError:return await reject(400,'Invalid Content-Length')
        if declared<0 or declared>self.settings.max_body_bytes:return await reject(413,'Request body too large')
        chunks=[];size=0
        try:
            async with asyncio.timeout(15):
                while True:
                    message=await receive()
                    if message['type']=='http.disconnect':return
                    part=message.get('body',b'');size+=len(part)
                    if size>self.settings.max_body_bytes:return await reject(413,'Request body too large')
                    chunks.append(part)
                    if not message.get('more_body'):break
        except TimeoutError:return await reject(408,'Request body timed out')
        consumed=False;status=500;started=time.monotonic()
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed=True;return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        async def tracked(message):
            nonlocal status
            if message['type']=='http.response.start':
                status=message['status'];message['headers']=[*message.get('headers',[]),(b'x-request-id',request_id.encode())]
            await send(message)
        try:await self.app(scope,replay,tracked)
        finally:log.info(json.dumps({'request_id':request_id,'method':scope['method'],'route':getattr(scope.get('route'),'path','unmatched'),'status':status,'duration_ms':round((time.monotonic()-started)*1000)}))
