"""Fixed-endpoint hosted adapters. No calls occur without explicit configuration.

Official schemas: OpenAI Responses/Embeddings; Gemini generateContent and
batchEmbedContents; Groq chat completions (generation only).
This transport is fixture-tested, not live-account certified.
"""
import json
import math
import re
import time
import httpx


class ProviderError(ValueError):
    pass

class ProviderUnavailableError(ProviderError):
    """Safe transport-only message; never includes provider bodies or keys."""


def vector(value):
    if not isinstance(value,list) or not 1<=len(value)<=4096:
        raise ProviderError('Invalid embedding dimensions')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in value):
        raise ProviderError('Non-finite embedding')
    norm=math.sqrt(sum(x*x for x in value))
    if not math.isfinite(norm) or norm==0:raise ProviderError('Zero/overflowed embedding')
    return [x/norm for x in value]


class HostedProvider:
    def __init__(self,settings):
        self.settings=settings
        self.model=settings.ai_model
        self.embedding_model=settings.ai_provider+':'+settings.embedding_model
        self._blocked_until=0

    def request(self,path,payload):
        if time.monotonic()<self._blocked_until:
            raise ProviderUnavailableError('Hosted provider is rate limited; retry later')
        s=self.settings
        if not s.cloud_processing_allowed or not s.ai_key:raise ProviderError('Hosted processing disabled')
        if s.ai_provider=='openai':
            base='https://api.openai.com/v1/';headers={'Authorization':'Bearer '+s.ai_key}
        elif s.ai_provider=='gemini':
            base='https://generativelanguage.googleapis.com/v1beta/';headers={'x-goog-api-key':s.ai_key}
        elif s.ai_provider=='groq':
            base='https://api.groq.com/openai/v1/';headers={'Authorization':'Bearer '+s.ai_key}
        else:raise ProviderError('Unsupported provider')
        if len(json.dumps(payload).encode())>300000:raise ProviderError('AI input budget exceeded')
        try:
            with httpx.stream('POST',base+path,json=payload,headers=headers,timeout=httpx.Timeout(60,connect=10),follow_redirects=False,trust_env=False) as response:
                response.raise_for_status();body=bytearray()
                for part in response.iter_bytes():
                    if len(body)+len(part)>2_000_000:raise ProviderError('AI output budget exceeded')
                    body.extend(part)
                result=json.loads(body)
                if not isinstance(result,dict):raise ProviderError('Expected JSON object')
                return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code==429:self._blocked_until=time.monotonic()+60
            raise ProviderUnavailableError('Hosted provider returned HTTP '+str(exc.response.status_code)) from None
        except httpx.TimeoutException:
            raise ProviderUnavailableError('Hosted provider timed out') from None
        except httpx.RequestError:
            raise ProviderUnavailableError('Hosted provider network connection failed') from None
        except ValueError:
            # Never propagate response bodies, request text or credentials to logs/errors.
            raise ProviderError('Hosted provider unavailable or response invalid') from None

    def embed(self,texts):
        if self.settings.ai_provider=='groq':
            raise ProviderError('Groq adapter is generation-only; no embedding service configured')
        if not 1<=len(texts)<=16 or any(not text or len(text)>10000 for text in texts):
            raise ProviderError('Embedding batch/input budget exceeded')
        model=self.settings.embedding_model
        if not re.fullmatch(r'[A-Za-z0-9._-]+',model):raise ProviderError('Invalid embedding model ID')
        if self.settings.ai_provider=='openai':
            result=self.request('embeddings',{'model':model,'input':texts,'encoding_format':'float'})
            rows=sorted(result.get('data',[]),key=lambda r:r.get('index',-1))
            if [r.get('index') for r in rows]!=list(range(len(texts))):raise ProviderError('Missing/duplicate embeddings')
            values=[r.get('embedding') for r in rows]
        else:
            result=self.request('models/'+model+':batchEmbedContents',{'requests':[{'model':'models/'+model,'content':{'parts':[{'text':t}]}} for t in texts]})
            values=[r.get('values') for r in result.get('embeddings',[])]
        if len(values)!=len(texts):raise ProviderError('Embedding count mismatch')
        normalized=[vector(v) for v in values]
        if len({len(v) for v in normalized})!=1:raise ProviderError('Mixed embedding dimensions')
        return normalized

    def structured(self,instruction,payload,schema):
        s=self.settings;model=s.ai_model
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]*(?:/[A-Za-z0-9_-][A-Za-z0-9._-]*)?',model):raise ProviderError('Invalid generation model ID')
        content=json.dumps(payload,ensure_ascii=False)
        if s.ai_provider=='openai':
            result=self.request('responses',{'model':model,'store':False,'max_output_tokens':2500,
                'input':[{'role':'system','content':instruction},{'role':'user','content':content}],
                'text':{'format':{'type':'json_schema','name':'evidence_response','strict':True,'schema':schema}}})
            if result.get('status')!='completed':raise ProviderError('Incomplete model response')
            parts=[part['text'] for item in result.get('output',[]) if item.get('type')=='message'
                   for part in item.get('content',[]) if part.get('type')=='output_text']
        elif s.ai_provider=='groq':
            strict_models={'qwen/qwen3.8-27b','openai/gpt-oss-20b','openai/gpt-oss-120b'}
            response_format=({'type':'json_schema','json_schema':{'name':'evidence_response','strict':True,'schema':schema}}
                if model in strict_models else {'type':'json_object'})
            result=self.request('chat/completions',{'model':model,'max_completion_tokens':2500,
                'messages':[{'role':'system','content':instruction+'\nReturn only JSON matching this schema: '+json.dumps(schema)},
                            {'role':'user','content':content}], 'response_format':response_format})
            choices=result.get('choices',[])
            if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':
                raise ProviderError('Incomplete model response')
            message=choices[0].get('message',{})
            if message.get('refusal') or not isinstance(message.get('content'),str):
                raise ProviderError('Model refused or returned invalid content')
            parts=[message['content']]
        else:
            result=self.request('models/'+model+':generateContent',{'systemInstruction':{'parts':[{'text':instruction}]},
                'contents':[{'role':'user','parts':[{'text':content}]}],
                'generationConfig':{'maxOutputTokens':2500,'responseMimeType':'application/json','responseJsonSchema':schema}})
            candidates=result.get('candidates',[])
            if len(candidates)!=1 or candidates[0].get('finishReason')!='STOP':raise ProviderError('Incomplete model response')
            parts=[p['text'] for p in candidates[0].get('content',{}).get('parts',[]) if 'text' in p and not p.get('thought')]
        try:return json.loads(''.join(parts))
        except (ValueError,TypeError):raise ProviderError('Invalid structured model output') from None
