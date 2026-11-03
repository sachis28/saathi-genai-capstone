"""Exercise the exact CLI staging wrapper, signed days, consent and runtime aliases."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from ml.azureml.train_job import main as train_job
from ml.common import ROOT, sha256


def load_prepare():
    spec=importlib.util.spec_from_file_location('radar_cli_prepare',ROOT/'radar/deploy/prepare.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_package_scores_actual_crm_rows_from_isolated_directory(tmp_path):
    data=ROOT/'data/generated/radar.csv'
    train_job(data,tmp_path/'model',sha256(data))
    stage=load_prepare().prepare(tmp_path/'code')
    request=json.loads((ROOT/'radar/deploy/sample-request.json').read_text())
    env=os.environ.copy()
    env.update(PYTHONPATH=str(stage),AZUREML_MODEL_DIR=str(tmp_path/'model'),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-c',
        'import json,sys; from score import init,run; init(); print(json.dumps(run(sys.stdin.read())))'],
        input=json.dumps(request),cwd=stage,env=env,text=True,capture_output=True,check=True)
    rows=json.loads(result.stdout)
    assert {r['customer_id'] for r in rows}=={'C-204','C-450','C-205'}
    assert all(type(r['risk_score']) is float and 0<=r['risk_score']<=1 for r in rows)
    assert [r['risk_score'] for r in rows]==sorted([r['risk_score'] for r in rows],reverse=True)
    assert next(r for r in request['data'] if r['customer_id']=='C-450')['days_to_renewal']==-5
    assert next(r for r in request['data'] if r['customer_id']=='C-205')['consent'] is False


def test_cli_package_refuses_unknown_or_secret_files(tmp_path):
    stage=tmp_path/'code'
    stage.mkdir()
    (stage/'.env').write_text('synthetic-test-only')
    with pytest.raises(ValueError,match='Unexpected files'):
        load_prepare().prepare(stage)


def test_preferred_radar_runtime_names_are_used(monkeypatch):
    from app.services import ml_service
    monkeypatch.setenv('ML_PROVIDER','azure')
    monkeypatch.setenv('RADAR_ENDPOINT_URL','https://new-endpoint.example/score')
    monkeypatch.setenv('RADAR_ENDPOINT_KEY','synthetic-test-only-key')
    monkeypatch.setenv('AZURE_ML_ENDPOINT','https://old-endpoint.example/score')
    monkeypatch.setenv('AZURE_ML_KEY','old-synthetic-test-key')
    request=json.loads((ROOT/'radar/deploy/sample-request.json').read_text())
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return [{'customer_id':r['customer_id'],'risk_score':0.5} for r in request['data']]
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,headers,json):
            assert url=='https://new-endpoint.example/score'
            assert headers=={'Authorization':'Bearer synthetic-test-only-key'}
            assert len(json['data'])==3
            return Response()
    monkeypatch.setattr(ml_service.httpx,'AsyncClient',Client)
    assert len(asyncio.run(ml_service.renewal_worklist(pd.DataFrame(request['data']))))==3


def test_secret_helper_writes_ignored_private_env_without_printing_key(tmp_path,monkeypatch,capsys):
    spec=importlib.util.spec_from_file_location('radar_env_save',ROOT/'radar/deploy/save-local-env.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    (tmp_path/'.gitignore').write_text('.env\n')
    (tmp_path/'.env').write_text('UNRELATED_TEST_SETTING=preserved\n')
    secret='synthetic-test-only-secret'
    def fake_run(command,**kwargs):
        if command[:2]==['git','rev-parse']:
            return subprocess.CompletedProcess(command,1,b'',b'')
        value=secret if 'get-credentials' in command else 'https://radar-test.example/score'
        return subprocess.CompletedProcess(command,0,value+'\n','')
    monkeypatch.setattr(module.subprocess,'run',fake_run)
    module.main()
    assert secret not in capsys.readouterr().out
    contents=(tmp_path/'.env').read_text()
    assert 'RADAR_ENDPOINT_KEY='+secret in contents
    assert 'UNRELATED_TEST_SETTING=preserved' in contents
    assert (tmp_path/'.env').stat().st_mode & 0o777 == 0o600
