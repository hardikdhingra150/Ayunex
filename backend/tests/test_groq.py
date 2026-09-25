"""Offline Groq wire fixtures; never call a live account."""
from contextlib import contextmanager
import httpx
import pytest
from app.ai_provider import HostedProvider, ProviderError
from app.config import Settings


def settings(**overrides):
    return Settings(**{'guidance_mode':'hosted','ai_provider':'groq','ai_key':'synthetic',
                       'ai_model':'qwen/qwen3.8-27b','cloud_processing_allowed':True,**overrides})


@pytest.mark.parametrize('model,mode',[('qwen/qwen3.8-27b','json_schema'),('other-model','json_object')])
def test_groq_wire(monkeypatch,model,mode):
    @contextmanager
    def stream(method,url,**kwargs):
        assert method=='POST' and url=='https://api.groq.com/openai/v1/chat/completions'
        assert kwargs['headers']['Authorization']=='Bearer synthetic'
        assert kwargs['json']['model']==model
        assert kwargs['json']['response_format']['type']==mode
        assert not kwargs['follow_redirects'] and not kwargs['trust_env']
        yield httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]},request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'stream',stream)
    assert HostedProvider(settings(ai_model=model)).structured('test',{}, {'type':'object'})=={'ok':True}


@pytest.mark.parametrize('message,finish', [({'content':'{}'},'length'),({'content':None},'stop'),({'content':'{}','refusal':'no'},'stop'),({'content':'not-json'},'stop')])
def test_groq_rejects_incomplete_or_invalid(monkeypatch,message,finish):
    provider=HostedProvider(settings())
    monkeypatch.setattr(provider,'request',lambda *args:{'choices':[{'finish_reason':finish,'message':message}]})
    with pytest.raises(ProviderError):provider.structured('test',{}, {})


def test_groq_generation_only_configuration():
    settings().validate()
    with pytest.raises(ValueError):settings(embedding_model='invented').validate()
    with pytest.raises(ValueError):settings(cloud_processing_allowed=False).validate()
    with pytest.raises(ProviderError,match='generation-only'):HostedProvider(settings()).embed(['synthetic'])


@pytest.mark.parametrize('model',['../unsafe','qwen/../../unsafe','https://host/model','model?key=secret'])
def test_model_identifier_cannot_change_endpoint(model):
    with pytest.raises(ProviderError,match='model ID'):HostedProvider(settings(ai_model=model)).structured('test',{}, {})
