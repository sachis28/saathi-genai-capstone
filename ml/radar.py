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

# The four model inputs. Consent and age band are deliberately NOT features (fairness + policy).
FEATURES = ["days_to_renewal", "interaction_count_90d", "sentiment_score", "annual_premium_inr"]


# Scores customers with a trained model and returns them highest-risk first.
def score_rows(model, frame):
    # Refuse a model that was trained on different features (protects the input contract).
    if list(getattr(model, "feature_names_in_", [])) != FEATURES:
        raise ValueError("Incompatible Radar model contract; retrain with annual_premium_inr and signed days")
    # Consent is not a scoring/visibility filter or predictive feature. Check it before send.
    valid = validate_radar_inference(frame.copy())
    eligible = valid.copy()
    if eligible.empty:
        return []
    # predict_proba gives [P(renews), P(does not renew)]; column 1 is the risk score.
    probabilities = model.predict_proba(eligible[FEATURES])[:,1]
    # Explanation: each feature's standardized value x its logistic regression weight.
    # The biggest contribution is reported as the "main risk factor" (a hint, not a cause).
    contributions = model[0].transform(eligible[FEATURES])*model[1].coef_[0]
    rows = []
    for (_,customer),score,terms in zip(eligible.iterrows(),probabilities,contributions):
        rows.append({"customer_id":customer.customer_id,"risk_score":float(score),
            "main_risk_factor":FEATURES[int(terms.argmax())],
            "explanation_type":"largest standardized logistic feature contribution; not causal",
            "synthetic":True})
    return sorted(rows,key=lambda row:(-row["risk_score"],row["customer_id"]))


# Trains the Renewal Radar model on synthetic data and saves the model + metrics.
def train():
    data = radar_schema.validate(pd.read_csv(DATA / "radar.csv"))
    # Hold out 25% for testing; stratify keeps the same share of non-renewals in both parts.
    train,test = train_test_split(data,test_size=0.25,stratify=data.nonrenewed,random_state=SEED)
    # Pipeline: scale each feature to mean 0 / std 1, then logistic regression.
    model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=SEED))
    model.fit(train[FEATURES],train.nonrenewed)
    p = model.predict_proba(test[FEATURES])[:,1]
    # ROC-AUC = ranking quality, average precision = quality on the rare positive class,
    # Brier score = how well calibrated the probabilities are (lower is better).
    metrics = {"data":"synthetic noisy renewal outcomes", "seed":SEED,"train_n":len(train),"test_n":len(test),
        "roc_auc":float(roc_auc_score(test.nonrenewed,p)),"average_precision":float(average_precision_score(test.nonrenewed,p)),
        "brier_score":float(brier_score_loss(test.nonrenewed,p)),"positive_prevalence":float(test.nonrenewed.mean()),
        "features":FEATURES,"contract":"radar-v2-annual-inr-signed-days",
        "train_overdue_n":int((train.days_to_renewal < 0).sum()), "test_overdue_n":int((test.days_to_renewal < 0).sum()),"excluded_features":["customer_id","age_band","consent","nonrenewed"],
        "limitations":"No real-world validation, no causal explanations, no eligibility or pricing decisions"}
    out = ARTIFACTS / "radar"
    out.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,out / "model.joblib")
    write_json(out / "metrics.json",metrics)
    write_json(out / "top10.json",score_rows(model,data)[:10])
    print(metrics,flush=True)


if __name__ == "__main__":
    train()
