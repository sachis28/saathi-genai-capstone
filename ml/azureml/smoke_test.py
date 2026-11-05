"""Explicit live Azure ML check using real agent authentication and CRM access rules.

Requires ML_PROVIDER=azure, SAATHI_LIVE_AGENT_TOKEN and the server credential store.
Run with PYTHONPATH=.:api. Ordinary unit tests never execute main().
"""
import asyncio
import os

from fastapi.security import HTTPAuthorizationCredentials
from app.services.ml_service import renewal_worklist
from app.services.worklist_access import authenticate_agent, load_authorized_radar_frame
from ml.common import ARTIFACTS, write_json


async def main():
    if os.getenv('ML_PROVIDER') != 'azure':
        raise RuntimeError('Set ML_PROVIDER=azure for a real endpoint smoke test')
    token = os.environ.get('SAATHI_LIVE_AGENT_TOKEN')
    if not token:
        raise RuntimeError('Configure SAATHI_LIVE_AGENT_TOKEN securely; no default identity')
    principal = authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials=token))
    frame = load_authorized_radar_frame(principal)
    if frame.empty:
        raise RuntimeError('No authorized eligible CRM rows; no Azure call made')
    result = await renewal_worklist(frame)
    write_json(ARTIFACTS / 'azure_smoke_test.json',{
        'status':'passed','provider':'azure','synthetic':True,
        'submitted_n':len(frame),'received_n':len(result),
        'submitted_customer_ids':frame.customer_id.tolist(),
        'no_consent_submitted_ids':frame.loc[~frame.consent,'customer_id'].tolist(),
        'response':result})
    print('Authenticated CRM Azure ML endpoint check passed; receipt: artifacts/azure_smoke_test.json')


if __name__ == '__main__':
    asyncio.run(main())
