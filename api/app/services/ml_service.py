"""Adapters for Sairaj's local intent model and local/Azure renewal risk model."""
import math
import os
from functools import lru_cache

import httpx
import joblib
import pandas as pd

from data.validate import validate_radar_inference
from ml.common import ARTIFACTS, DATA
from ml.radar import score_rows


# Load each intent model once and cache it (maxsize=2: one per provider).
@lru_cache(maxsize=2)
def intent_model(provider):
    # tfidf_lr = TF-IDF features + logistic regression, small and fast (used in CI).
    if provider=="tfidf_lr":
        return joblib.load(ARTIFACTS / "tfidf_lr" / "model.joblib")
    # distilbert = fine-tuned DistilBERT transformer, more accurate, heavier.
    if provider=="distilbert":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        torch.set_num_threads(4)
        path = ARTIFACTS / "distilbert"
        if not (path / "config.json").exists():
            raise FileNotFoundError("Train DistilBERT before selecting this provider")
        tokenizer = AutoTokenizer.from_pretrained(path,local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True).eval()
        return tokenizer,model
    raise ValueError("INTENT_PROVIDER must be distilbert or tfidf_lr")


# Returns the predicted intent label (e.g. coverage, renewal) and the model's confidence.
def classify_intent(text):
    provider = os.getenv("INTENT_PROVIDER","distilbert")
    loaded = intent_model(provider)
    if provider=="tfidf_lr":
        # predict_proba gives one probability per intent; we take the highest.
        probabilities = loaded.predict_proba([text])[0]
        index = int(probabilities.argmax())
        confidence = float(probabilities[index])
        label = str(loaded.classes_[index])
    else:
        import torch
        tokenizer,model = loaded
        # inference_mode turns off gradient tracking: faster prediction, no training.
        with torch.inference_mode():
            probabilities = model(**tokenizer(text,return_tensors="pt",truncation=True,max_length=48)).logits.softmax(-1)[0]
        index = int(probabilities.argmax())
        confidence = float(probabilities[index])
        label = model.config.id2label[index]
    # This score is uncalibrated and not an authorization or grounding decision.
    return {"intent":label,"confidence":confidence,"model":provider}


# Renewal Radar: score each customer's lapse risk. frame = rows already filtered for this agent.
async def renewal_worklist(frame=None):
    # validate_radar_inference checks the feature columns and types before scoring.
    data = validate_radar_inference(pd.read_csv(DATA / "radar.csv") if frame is None else frame.copy())
    if data.empty:
        return []
    provider = os.getenv("ML_PROVIDER","local")
    # Local mode: load the trained model file and score in this process.
    if provider == "local":
        return score_rows(joblib.load(ARTIFACTS / "radar" / "model.joblib"),data)
    if provider != "azure":
        raise ValueError("ML_PROVIDER must be local or azure")
    # Azure mode: send the rows to the Azure ML managed online endpoint over HTTPS.
    url = os.getenv("RADAR_ENDPOINT_URL") or os.environ["AZURE_ML_ENDPOINT"]
    if not url.startswith("https://"):
        raise ValueError("Azure ML endpoint must use HTTPS")
    key = os.getenv("RADAR_ENDPOINT_KEY") or os.environ["AZURE_ML_KEY"]
    headers = {"Authorization":f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url,headers=headers,json={"data":data.to_dict(orient="records")})
        response.raise_for_status()
    results = response.json()
    # Never trust the cloud response blindly: same customers, no duplicates, scores between 0 and 1.
    allowed = set(data.customer_id)
    if not isinstance(results,list) or len(results)!=len(allowed):
        raise ValueError("Azure response count does not match submitted customers")
    seen = set()
    for row in results:
        customer = row.get("customer_id")
        risk = row.get("risk_score")
        if customer not in allowed or customer in seen or not isinstance(risk,(int,float)) or not math.isfinite(risk) or not 0<=risk<=1:
            raise ValueError("Invalid Azure worklist result")
        seen.add(customer)
    # Highest risk first; ties broken by customer_id so the order is stable.
    return sorted(results,key=lambda r:(-r["risk_score"],r["customer_id"]))
