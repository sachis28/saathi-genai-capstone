"""Contract regression tests using Sachi's pinned six-row export."""
import asyncio
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pandera.pandas as pa
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data.validate import validate_radar_inference
from ml.common import ARTIFACTS, DATA, load_split
from ml.radar import FEATURES, score_rows


@pytest.fixture
def crm():
    return pd.read_json(Path(__file__).parent / 'fixtures/sachi_radar_input.json')


@pytest.fixture
def model():
    return joblib.load(ARTIFACTS / 'radar/model.joblib')


def test_crm_export_scores_overdue_and_filters_consent(crm, model):
    assert crm.loc[crm.customer_id == 'C-450', 'days_to_renewal'].item() == -5
    result = score_rows(model, crm)
    assert {r['customer_id'] for r in result} == set(crm.loc[crm.consent, 'customer_id'])
    assert len(result) == 5
    assert all(np.isfinite(r['risk_score']) and 0 <= r['risk_score'] <= 1 for r in result)
    assert result == sorted(result, key=lambda r: (-r['risk_score'], r['customer_id']))
    crm['consent'] = False
    assert score_rows(model, crm) == []


@pytest.mark.parametrize('field,value', [
    ('annual_premium_inr', 0), ('annual_premium_inr', -1),
    ('annual_premium_inr', float('inf')), ('annual_premium_inr', float('nan')),
    ('sentiment_score', None), ('sentiment_score', 1.1),
    ('sentiment_score', float('inf')), ('interaction_count_90d', -1),
    ('interaction_count_90d', 10001), ('consent', 'true'),
    ('days_to_renewal', 1.5),
])
def test_reject_invalid_input(crm, field, value):
    crm[field] = value
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        validate_radar_inference(crm)


def test_reject_old_premium_and_duplicate_ids(crm):
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        validate_radar_inference(crm.rename(columns={'annual_premium_inr': 'premium'}))
    crm.loc[1, 'customer_id'] = crm.loc[0, 'customer_id']
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        validate_radar_inference(crm)


def test_reject_old_estimator(crm):
    frame = pd.read_csv(DATA / 'radar.csv')
    old_features = FEATURES[:-1] + ['premium']
    old = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    old.fit(frame[FEATURES].set_axis(old_features, axis=1), frame.nonrenewed)
    with pytest.raises(ValueError, match='retrain'):
        score_rows(old, crm)


def test_azure_entrypoint_matches_local(crm, model, tmp_path, monkeypatch):
    from ml.azureml import score
    joblib.dump(model, tmp_path / 'model.joblib')
    monkeypatch.setenv('AZUREML_MODEL_DIR', str(tmp_path))
    score.init()
    assert score.run(json.dumps({'data': crm.to_dict('records')})) == score_rows(model, crm)


def test_adapter_azure_payload_and_results(crm, model, monkeypatch):
    from api.app.services import ml_service
    monkeypatch.setenv('ML_PROVIDER', 'azure')
    monkeypatch.setenv('AZURE_ML_ENDPOINT', 'https://test.example/score')
    monkeypatch.setenv('AZURE_ML_KEY', 'test-only')
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            payload = pd.DataFrame(json['data'])
            assert len(payload) == 5 and payload.consent.all()
            assert 'annual_premium_inr' in payload and 'premium' not in payload
            assert 'C-450' in set(payload.customer_id)
            result = score_rows(model, payload)
            class Response:
                def raise_for_status(self): pass
                def json(self): return result
            return Response()
    monkeypatch.setattr(ml_service.httpx, 'AsyncClient', Client)
    assert asyncio.run(ml_service.renewal_worklist(crm)) == score_rows(model, crm)
    monkeypatch.setenv('ML_PROVIDER', 'local')
    assert asyncio.run(ml_service.renewal_worklist(crm)) == score_rows(model, crm)


def test_radar_regeneration_preserves_locked_intent_files():
    from data.generate_ml import generate_radar
    from ml.common import sha256
    paths = [DATA / f'intent_{s}.csv' for s in ['train', 'dev', 'test']]
    before = [sha256(p) for p in paths]
    radar_hash = sha256(DATA / 'radar.csv')
    generate_radar()
    assert [sha256(p) for p in paths] == before
    assert sha256(DATA / 'radar.csv') == radar_hash
    for split in ['train', 'dev', 'test']: load_split(split)
    assert (pd.read_csv(DATA / 'radar.csv').days_to_renewal < 0).any()
