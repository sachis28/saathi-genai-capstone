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


@lru_cache(maxsize=2)
def intent_model(provider):
    if provider=="tfidf_lr":
        return joblib.load(ARTIFACTS / "tfidf_lr" / "model.joblib")
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


def classify_intent(text):
    provider = os.getenv("INTENT_PROVIDER","distilbert")
    loaded = intent_model(provider)
    if provider=="tfidf_lr":
        probabilities = loaded.predict_proba([text])[0]
        index = int(probabilities.argmax())
        confidence = float(probabilities[index])
        label = str(loaded.classes_[index])
    else:
        import torch
        tokenizer,model = loaded
        with torch.inference_mode():
            probabilities = model(**tokenizer(text,return_tensors="pt",truncation=True,max_length=48)).logits.softmax(-1)[0]
        index = int(probabilities.argmax())
        confidence = float(probabilities[index])
        label = model.config.id2label[index]
    # This score is uncalibrated and not an authorization or grounding decision.
    return {"intent":label,"confidence":confidence,"model":provider}


async def renewal_worklist(frame=None):
    data = validate_radar_inference(pd.read_csv(DATA / "radar.csv") if frame is None else frame.copy())
    data = data[data.consent].copy()
    if data.empty:
        return []
    provider = os.getenv("ML_PROVIDER","local")
    if provider == "local":
        return score_rows(joblib.load(ARTIFACTS / "radar" / "model.joblib"),data)
    if provider != "azure":
        raise ValueError("ML_PROVIDER must be local or azure")
    url = os.environ["AZURE_ML_ENDPOINT"]
    if not url.startswith("https://"):
        raise ValueError("Azure ML endpoint must use HTTPS")
    headers = {"Authorization":f"Bearer {os.environ['AZURE_ML_KEY']}"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url,headers=headers,json={"data":data.to_dict(orient="records")})
        response.raise_for_status()
    results = response.json()
    allowed = set(data.customer_id)
    if not isinstance(results,list) or len(results)!=len(allowed):
        raise ValueError("Azure response count does not match consented customers")
    seen = set()
    for row in results:
        customer = row.get("customer_id")
        risk = row.get("risk_score")
        if customer not in allowed or customer in seen or not isinstance(risk,(int,float)) or not math.isfinite(risk) or not 0<=risk<=1:
            raise ValueError("Invalid Azure worklist result")
        seen.add(customer)
    return sorted(results,key=lambda r:(-r["risk_score"],r["customer_id"]))
