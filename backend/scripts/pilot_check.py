"""Explicit local end-to-end test; sends a public legal question to the provider."""
import argparse
from pathlib import Path
from datetime import date
from fastapi.testclient import TestClient
from app.environment import load_local_env
from app.config import Settings
from app.main import create_app

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:raise SystemExit('Use --execute to authorize the public-question provider test')
    root=Path(__file__).resolve().parents[1];load_local_env(root/'.env')
    settings=Settings()
    if settings.environment!='development':raise SystemExit('Development-only test')
    settings.guidance_mode='hosted'
    if not settings.dev_token:settings.dev_token=(root/'.dev-token').read_text().strip()
    with TestClient(create_app(settings)) as client:
        client.post('/api/v1/consent/record',headers={'Authorization':'Bearer '+settings.dev_token},json={'purpose':'hosted_ai_processing','notice_version':'pilot-check-v1'})
        response=client.post('/api/v1/guidance',headers={'Authorization':'Bearer '+settings.dev_token},json={
            'question':'What does Section 3(p) of the Indian Patents Act say about traditional knowledge?',
            'original_language':'en','allow_hosted_processing':True,
            'jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat()})
        body=response.json()
        # Never print request headers, credentials or private case data.
        print({'http_status':response.status_code,'support':body.get('support'),'trace':body.get('retrieval_trace')})
        for section in body.get('sections',[]):
            for claim in section['claims']:print(claim['text'])
        print({'citations':[(c['provision'],c['review_status']) for c in body.get('citations',[])]})
        if response.status_code!=200 or body.get('retrieval_trace',{}).get('mode')!='HOSTED_RAG':
            raise SystemExit('Live synthesis not confirmed; inspect safe fallback/configuration')
