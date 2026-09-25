"""No network by default. --execute sends synthetic text only and may incur fees."""
import argparse
from pathlib import Path
from app.environment import load_local_env
from app.config import Settings
from app.ai_provider import HostedProvider, ProviderError


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    load_local_env(Path(__file__).resolve().parents[1]/'.env');settings=Settings()
    ready=all((settings.ai_provider in {'openai','gemini','groq'},settings.ai_key,settings.ai_model,
               settings.ai_provider=='groq' or settings.embedding_model,settings.cloud_processing_allowed))
    print({'configured':bool(ready),'provider':settings.ai_provider or 'NOT_SELECTED','key_present':bool(settings.ai_key),'network_requested':args.execute})
    if args.execute:
        if not ready:raise SystemExit('Configure provider, models, key and processing permission first')
        provider=HostedProvider(settings)
        schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
        try:
            embedding=provider.embed(['Synthetic connectivity check. No user or legal data.']) if settings.ai_provider!='groq' else None
            answer=provider.structured('Connectivity test. Return ok=true.',{'test':'synthetic'},schema)
        except ProviderError as exc:
            raise SystemExit(str(exc)) from None
        if answer!={'ok':True}:raise SystemExit('Structured-output test failed')
        print({'synthetic_test':'PASSED','model':settings.ai_model,'embedding_dimensions':len(embedding[0]) if embedding else None,'legal_accuracy_tested':False})
