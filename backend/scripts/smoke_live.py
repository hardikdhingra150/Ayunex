"""Explicit local smoke: guest isolation, consent, public Qwen query, cleanup.
Never reads/prints API keys. --execute permits the hosted synthetic pilot query.
"""
import argparse
from datetime import date
import httpx

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:raise SystemExit('Use --execute to authorize a public-question live test')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=150,trust_env=False) as c:
        assert c.post('/api/v1/auth/session',json={'role':'administrator'}).status_code==422
        a=c.post('/api/v1/auth/session').json();b=c.post('/api/v1/auth/session').json()
        headers={'Authorization':'Bearer '+a['token']};other={'Authorization':'Bearer '+b['token']}
        result=c.post('/api/v1/cases',headers=headers,json={'title':'Synthetic release smoke - temporary',
            'jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat(),
            'consent':{'accepted':True,'notice_version':'case-notice-v1'}})
        result.raise_for_status();case=result.json()
        try:
            assert c.get('/api/v1/cases/'+case['id'],headers=other).status_code==404
            query={'question':'What does Section 3(p) of the Indian Patents Act say about traditional knowledge?',
                'original_language':'en','allow_hosted_processing':True,
                'jurisdiction':{'layer':'NATIONAL','country':'IN'},'as_of_date':date.today().isoformat()}
            assert c.post('/api/v1/guidance',headers=headers,json=query).status_code==403
            c.post('/api/v1/consent/record',headers=headers,json={'purpose':'hosted_ai_processing','notice_version':'smoke-v1'}).raise_for_status()
            response=c.post('/api/v1/guidance',headers=headers,json=query);response.raise_for_status();answer=response.json()
            print({'http':response.status_code,'guest_isolation':'PASS','privilege_escalation':'BLOCKED',
                'consent_required':'PASS','model':answer['retrieval_trace']['model'],
                'mode':answer['retrieval_trace']['mode'],'citations':len(answer['citations']),'support':answer['support']})
            assert answer['retrieval_trace']['mode']=='HOSTED_RAG','Provider used safe fallback; live generation not confirmed'
            c.post('/api/v1/consent/withdraw',headers=headers,json={'purpose':'hosted_ai_processing'}).raise_for_status()
            assert c.post('/api/v1/guidance',headers=headers,json=query).status_code==403
        finally:
            c.delete('/api/v1/cases/'+case['id'],headers=headers,params={'expected_revision':case['revision']}).raise_for_status()
            print('Temporary smoke case removed; consent/audit records retained.')
