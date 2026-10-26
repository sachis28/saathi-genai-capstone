import json

import joblib
import pandas as pd
import pandera.pandas as pa
import pytest
import torch
from fastapi.testclient import TestClient

from app.main import app
from data.validate import intent_schema, radar_schema, validate_splits
from ml.common import ARTIFACTS, DATA, LABELS, load_split
from ml.mini_transformer import MiniTransformer, encode
from ml.prompt_experiment import CONTEXT, grade, make_cases
from ml.radar import FEATURES, score_rows


def test_locked_splits_and_no_leakage():
    splits = {s:load_split(s) for s in ["train","dev","test"]}
    validate_splits(splits)
    for name,frame in splits.items():
        assert frame.label.value_counts().nunique()==1


def test_validator_rejects_invalid_label_and_text_leakage():
    splits = {s:load_split(s) for s in ["train","dev","test"]}
    invalid = splits["train"].copy()
    invalid.loc[0,"label"] = "invalid"
    with pytest.raises(pa.errors.SchemaError):
        intent_schema.validate(invalid)
    splits["test"].loc[0,"text"] = splits["train"].loc[0,"text"]
    with pytest.raises(ValueError,match="leakage"):
        validate_splits(splits)


def test_tfidf_vocabulary_excludes_heldout_only_word():
    model = joblib.load(ARTIFACTS / "tfidf_lr/model.joblib")
    assert "calculus" not in model["tfidf"].vocabulary_
    assert model.predict(["Draft a renewal reminder for C-204 on Gold"])[0]=="renewal_draft"


def test_transformer_padding_cannot_receive_attention():
    torch.manual_seed(42)
    model = MiniTransformer(vocab_size=8).eval()
    ids = torch.tensor([[2,3,0,0]])
    with torch.no_grad():
        logits,attention = model(ids)
        longer,_ = model(torch.tensor([[2,3,0,0,0,0]]))
    assert logits.shape==(1,5)
    assert attention.shape==(1,4,4,4)
    assert torch.all(attention[:,:,:,2:]==0)
    assert torch.allclose(logits,longer,atol=1e-5)
    with pytest.raises(ValueError):
        model(torch.zeros((1,4),dtype=torch.long))


def test_radar_consent_feature_exclusion_and_sort_order():
    frame = pd.read_csv(DATA / "radar.csv").head(12)
    frame.loc[frame.index[0],"consent"] = False
    model = joblib.load(ARTIFACTS / "radar/model.joblib")
    assert not {"age_band","consent","nonrenewed","customer_id"} & set(FEATURES)
    rows = score_rows(model,frame)
    assert frame.iloc[0].customer_id not in [r["customer_id"] for r in rows]
    assert all(0<=r["risk_score"]<=1 for r in rows)
    assert rows==sorted(rows,key=lambda r:(-r["risk_score"],r["customer_id"]))
    frame["consent"] = False
    assert score_rows(model,frame)==[]


def test_radar_rejects_invalid_sentiment():
    frame = pd.read_csv(DATA / "radar.csv").head(2)
    frame.loc[0,"sentiment_score"] = 2.0
    with pytest.raises(pa.errors.SchemaError):
        radar_schema.validate(frame)


def test_azure_scoring_matches_local(tmp_path,monkeypatch):
    from ml.azureml import score
    import shutil
    shutil.copy2(ARTIFACTS / "radar/model.joblib",tmp_path / "model.joblib")
    monkeypatch.setenv("AZUREML_MODEL_DIR",str(tmp_path))
    score.init()
    data = pd.read_csv(DATA / "radar.csv").head(5)
    body = {"data":data.to_dict(orient="records")}
    assert score.run(json.dumps(body))==score_rows(score.model,data)


def test_prompt_grader_rejects_fake_citations_sent_and_wrong_decision():
    cases = make_cases()
    assert len(cases)==25 and len({c["id"] for c in cases})==25
    assert all(len(case["required_citations"])==2 for case in cases[2:5])
    good = {"decision":"answer","answer":"Synthetic Silver limit is INR 500000.","citations":cases[0]["required_citations"],"draft_status":None,"sent":False}
    assert grade(cases[0],json.dumps(good))["passed"]
    for patch in [{"sent":True},{"decision":"draft"},{"citations":[]},{"citations":[{"source_id":"FAKE"}]},{"answer":""}]:
        assert not grade(cases[0],json.dumps({**good,**patch}))["passed"]
    assert not grade(cases[0],"[]")["passed"]


def test_api_real_intent_and_local_worklist(monkeypatch):
    monkeypatch.setenv("INTENT_PROVIDER","tfidf_lr")
    monkeypatch.setenv("ML_PROVIDER","local")
    with TestClient(app) as client:
        response = client.post("/chat",json={"customer_id":"C-204","question":"Draft a renewal reminder for C-204 on Gold"})
        assert response.status_code==200
        assert response.json()["intent"]=="renewal_draft"
        worklist = client.get("/worklist?limit=3")
        assert worklist.status_code==200
        assert len(worklist.json()["items"])==3
        assert worklist.json()["synthetic"] is True
        assert client.get("/worklist?limit=0").status_code==422


def test_distilbert_adapter_uses_local_trained_weights(monkeypatch):
    if not (ARTIFACTS / "distilbert/config.json").exists():
        pytest.skip("Optional pretrained training stage not run")
    from app.services.ml_service import classify_intent
    monkeypatch.setenv("INTENT_PROVIDER","distilbert")
    value = classify_intent("Draft a renewal reminder for C-204")
    assert value["intent"]=="renewal_draft"
    assert value["model"]=="distilbert"
    assert 0<=value["confidence"]<=1


def test_azure_worklist_validates_response_and_filters_consent(monkeypatch):
    import asyncio
    from app.services import ml_service
    frame = pd.read_csv(DATA / "radar.csv").head(2)
    frame.loc[frame.index[0],"consent"] = False
    frame.loc[frame.index[1],"consent"] = True
    monkeypatch.setenv("ML_PROVIDER","azure")
    monkeypatch.setenv("AZURE_ML_ENDPOINT","https://test.example/score")
    monkeypatch.setenv("AZURE_ML_KEY","test-only")
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return [{"customer_id":"UNAUTHORIZED","risk_score":0.9}]
    class Client:
        def __init__(self,**kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self,*args):
            pass
        async def post(self,url,headers,json):
            assert len(json["data"])==1
            assert json["data"][0]["consent"] is True
            assert "nonrenewed" not in json["data"][0]
            assert "age_band" not in json["data"][0]
            return Response()
    monkeypatch.setattr(ml_service.httpx,"AsyncClient",Client)
    with pytest.raises(ValueError,match="Invalid Azure"):
        asyncio.run(ml_service.renewal_worklist(frame))
