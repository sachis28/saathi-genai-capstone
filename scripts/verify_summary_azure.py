"""Explicit paid live check, never collected by ordinary pytest.

PYTHONPATH=.:api python scripts/verify_summary_azure.py --run-live
Requires Azure endpoint, API key and deployment in the environment.
Uses only checked-in synthetic customer C-204, through the actual summary router.
"""
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live', action='store_true', required=True)
    parser.parse_args()
    required = ('AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','AZURE_OPENAI_DEPLOYMENT')
    if any(not os.environ.get(key) for key in required):
        parser.error('Configure Azure endpoint, API key and deployment securely before running')
    os.environ['LLM_PROVIDER'] = 'azure'
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import summary
    summary.get_llm.cache_clear()
    app = FastAPI()
    app.include_router(summary.router)
    with TestClient(app) as client:
        response = client.get('/customers/C-204/summary')
    if response.status_code != 200:
        raise SystemExit(f'Live summary check failed: HTTP {response.status_code}; provider details withheld')
    result = response.json()
    expected = {'I-0001','I-0002','I-0003'}
    if set(result['interaction_ids']) != expected:
        raise SystemExit('Live check failed: incomplete interaction history')
    print('PASS: Azure adapter + summary route + grounding; C-204, all 3 interaction IDs')


if __name__ == '__main__':
    main()
