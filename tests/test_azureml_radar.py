"""Deployment-boundary checks; never invoke Azure or provision compute."""
import asyncio
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from ml.azureml.train_job import main as train_job
from ml.common import ROOT, sha256


def test_cloud_training_rejects_wrong_input_hash(tmp_path):
    with pytest.raises(ValueError, match='hash mismatch'):
        train_job(ROOT/'data/generated/radar.csv', tmp_path/'model', '0'*64)


def test_cloud_training_refuses_six_rows(tmp_path):
    data = tmp_path/'six.csv'
    pd.read_csv(ROOT/'data/generated/radar.csv').head(6).to_csv(data,index=False)
    with pytest.raises(ValueError, match='never six CRM'):
        train_job(data,tmp_path/'model',sha256(data))


def test_actual_cloud_job_model_and_isolated_scoring_bundle(tmp_path,monkeypatch):
    from ml.azureml import preflight
    data=ROOT/'data/generated/radar.csv'
    train_job(data,tmp_path/'model',sha256(data))
    monkeypatch.setattr(preflight,'ARTIFACTS',tmp_path/'receipts')
    result=preflight.check(tmp_path/'model')
    assert result['inference_n']==6
    assert 'C-450' in result['negative_days_ids']
    assert result['no_consent_ids']==['C-205']
    assert {r['customer_id'] for r in result['scores']}=={'C-204','C-311','C-118','C-450','C-205','C-999'}


def test_live_smoke_uses_auth_gate_and_counts_no_consent_visibility(tmp_path,monkeypatch):
    from ml.azureml import smoke_test
    token='synthetic-test-only-radar-token'
    credentials=tmp_path/'test-credentials.json'
    credentials.write_text(json.dumps([{'agent_id':'A-002','allowed_products':['Health'],
        'token_sha256':hashlib.sha256(token.encode()).hexdigest()}]))
    monkeypatch.setenv('ML_PROVIDER','azure')
    monkeypatch.setenv('SAATHI_AS_OF_DATE','2026-10-28')
    monkeypatch.setenv('SAATHI_LIVE_AGENT_TOKEN',token)
    monkeypatch.setenv('SAATHI_AGENT_CREDENTIALS_FILE',str(credentials))
    captured={}
    async def fake_call(frame):
        assert set(frame.customer_id)=={'C-311','C-205'}
        return [{'customer_id':cid,'risk_score':0.5} for cid in frame.customer_id]
    monkeypatch.setattr(smoke_test,'renewal_worklist',fake_call)
    monkeypatch.setattr(smoke_test,'write_json',lambda p,r:captured.update(r))
    asyncio.run(smoke_test.main())
    assert captured['submitted_n']==2
    assert captured['no_consent_submitted_ids']==['C-205']
