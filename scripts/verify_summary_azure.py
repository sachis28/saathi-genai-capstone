"""Explicit live Azure adapter check through the authenticated summary router.

Configure Azure endpoint/key/deployment and existing server-side agent credentials.
SAATHI_LIVE_AGENT_TOKEN must belong to C-204's authorized agent/product scope.
No dependency overrides or default credentials. Ordinary pytest never runs this.
"""
import argparse
import os


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true',required=True)
    parser.parse_args()
    required=('AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','AZURE_OPENAI_DEPLOYMENT',
              'SAATHI_AGENT_CREDENTIALS_FILE','SAATHI_LIVE_AGENT_TOKEN')
    if any(not os.environ.get(name) for name in required):
        parser.error('Configure Azure runtime and approved server-side agent credentials securely')
    os.environ['LLM_PROVIDER']='azure'
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import summary
    summary.get_llm.cache_clear()
    app=FastAPI()
    app.include_router(summary.router)
    with TestClient(app) as client:
        response=client.get('/customers/C-204/summary',headers={
            'Authorization':'Bearer '+os.environ['SAATHI_LIVE_AGENT_TOKEN']})
    if response.status_code!=200:
        raise SystemExit(f'Live authenticated summary failed: HTTP {response.status_code}; provider details withheld')
    result=response.json()
    if set(result['interaction_ids'])!={'I-0001','I-0002','I-0003'}:
        raise SystemExit('Live check failed: incomplete interaction history')
    print('PASS: real Azure adapter + authenticated summary router + grounding; all 3 C-204 interactions')


if __name__=='__main__':
    main()
