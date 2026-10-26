"""Synthetic renewal risk demo, never a production insurance decision model."""
import argparse

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data.validate import radar_schema, validate_radar_inference
from ml.common import ARTIFACTS, DATA, SEED, write_json

FEATURES = ["days_to_renewal", "interaction_count_90d", "sentiment_score", "premium"]


def score_rows(model, frame):
    # Consent is a business filter, not a predictive feature. It never authorizes a send.
    valid = validate_radar_inference(frame.copy())
    eligible = valid[valid.consent].copy()
    if eligible.empty:
        return []
    probabilities = model.predict_proba(eligible[FEATURES])[:,1]
    contributions = model[0].transform(eligible[FEATURES])*model[1].coef_[0]
    rows = []
    for (_,customer),score,terms in zip(eligible.iterrows(),probabilities,contributions):
        rows.append({"customer_id":customer.customer_id,"risk_score":float(score),
            "main_risk_factor":FEATURES[int(terms.argmax())],
            "explanation_type":"largest standardized logistic feature contribution; not causal",
            "synthetic":True})
    return sorted(rows,key=lambda row:(-row["risk_score"],row["customer_id"]))


def train():
    data = radar_schema.validate(pd.read_csv(DATA / "radar.csv"))
    train,test = train_test_split(data,test_size=0.25,stratify=data.nonrenewed,random_state=SEED)
    model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=SEED))
    model.fit(train[FEATURES],train.nonrenewed)
    p = model.predict_proba(test[FEATURES])[:,1]
    metrics = {"data":"synthetic noisy renewal outcomes", "seed":SEED,"train_n":len(train),"test_n":len(test),
        "roc_auc":float(roc_auc_score(test.nonrenewed,p)),"average_precision":float(average_precision_score(test.nonrenewed,p)),
        "brier_score":float(brier_score_loss(test.nonrenewed,p)),"positive_prevalence":float(test.nonrenewed.mean()),
        "features":FEATURES,"excluded_features":["customer_id","age_band","consent","nonrenewed"],
        "limitations":"No real-world validation, no causal explanations, no eligibility or pricing decisions"}
    out = ARTIFACTS / "radar"
    out.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,out / "model.joblib")
    write_json(out / "metrics.json",metrics)
    write_json(out / "top10.json",score_rows(model,data)[:10])
    print(metrics,flush=True)


if __name__ == "__main__":
    train()
