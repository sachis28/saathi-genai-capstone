"""Azure ML scoring entry point. The package root is included in code configuration."""
import json
import os
from pathlib import Path

import joblib
import pandas as pd

from ml.radar import score_rows

model = None


def init():
    global model
    root = Path(os.environ["AZUREML_MODEL_DIR"])
    matches = list(root.rglob("model.joblib"))
    if len(matches)!=1:
        raise RuntimeError("Expected exactly one registered model.joblib")
    model = joblib.load(matches[0])


def run(raw_data):
    if model is None:
        raise RuntimeError("init must run before scoring")
    body = json.loads(raw_data) if isinstance(raw_data,str) else raw_data
    if not isinstance(body,dict) or not isinstance(body.get("data"),list) or not body["data"]:
        raise ValueError("Expected a nonempty data array")
    return score_rows(model,pd.DataFrame(body["data"]))
