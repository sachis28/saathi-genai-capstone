"""Read-only details for the UI: why the Renewal Radar scored a customer, and their interaction sentiment.

Nothing here changes who can see what. /worklist still filters rows through worklist_access before
scoring; these helpers only add explanation to rows that already passed that gate.
"""
import json
from pathlib import Path

import joblib

from ml.common import ARTIFACTS, ROOT
from ml.radar import FEATURES

DATA = ROOT / "data"

# Plain-English names for the four Radar features, shown in the UI.
FEATURE_LABELS = {
    "days_to_renewal": "Days to renewal",
    "interaction_count_90d": "Interactions in last 90 days",
    "sentiment_score": "Sentiment (90-day average)",
    "annual_premium_inr": "Annual premium (INR)",
}


def _load(name: str):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


# For each scored row: the four input values and, with the local model, how much each one
# pushed the risk up (+) or down (-). contribution = standardized value x logistic weight.
def radar_details(frame, model_path: Path = ARTIFACTS / "radar" / "model.joblib"):
    try:
        model = joblib.load(model_path)
        contributions = model[0].transform(frame[FEATURES]) * model[1].coef_[0]
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        contributions = None  # Azure-only deployment without a local model: values, no weights
    details = {}
    for i, (_, row) in enumerate(frame.iterrows()):
        details[row.customer_id] = [
            {"feature": f, "label": FEATURE_LABELS[f], "value": float(row[f]),
             "contribution": None if contributions is None else round(float(contributions[i][j]), 4)}
            for j, f in enumerate(FEATURES)
        ]
    return details


# Per-customer sentiment: the 90-day score the Radar uses, plus each interaction with its
# Azure AI Language label and confidences (produced offline by ml/sentiment.py).
def customer_sentiment(customer_id: str) -> dict:
    texts = {r["interaction_id"]: r for r in _load("interactions.json") if r.get("customer_id") == customer_id}
    labels = [r for r in _load("interaction_sentiment.json") if r.get("customer_id") == customer_id]
    score = next((r for r in _load("customer_sentiment.json") if r.get("customer_id") == customer_id), None)
    interactions = []
    for r in sorted(labels, key=lambda r: r.get("date", ""), reverse=True):
        source = texts.get(r["interaction_id"], {})
        interactions.append({
            "interaction_id": r["interaction_id"], "date": r.get("date"), "channel": source.get("channel"),
            "text": source.get("text"), "sentiment": r.get("sentiment"),
            "confidence_scores": r.get("confidence_scores") or {}, "provider": r.get("provider"),
        })
    return {
        "customer_id": customer_id,
        "sentiment_score_90d": None if score is None else score.get("sentiment_score"),
        "as_of_date": None if score is None else score.get("as_of_date"),
        "interactions": interactions,
    }
