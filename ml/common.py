import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "generated"
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"
LABELS = ["compare_products", "coverage_question", "renewal_draft", "customer_lookup", "out_of_scope"]
SEED = 42


def seed_everything():
    random.seed(SEED)
    np.random.seed(SEED)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def load_split(name):
    path = DATA / f"intent_{name}.csv"
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    if sha256(path) != manifest["files"][path.name]:
        raise ValueError(f"Dataset hash mismatch: {path.name}; restore the locked dataset")
    return pd.read_csv(path)


def evaluate(name, frame, predictions, metadata=None):
    output = ARTIFACTS / name
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "model": name, "seed": SEED, "dataset": "synthetic template-family holdout",
        "test_sha256": sha256(DATA / "intent_test.csv"), "n": len(frame),
        "macro_f1": float(f1_score(frame.label, predictions, labels=LABELS, average="macro", zero_division=0)),
        "classification_report": classification_report(frame.label, predictions, labels=LABELS, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(frame.label, predictions, labels=LABELS).tolist(),
        "label_order": LABELS, "metadata": metadata or {},
    }
    write_json(output / "metrics.json", result)
    frame.assign(prediction=list(predictions)).to_csv(output / "predictions.csv", index=False)
    print(f"{name}: held-out macro F1 = {result['macro_f1']:.4f}", flush=True)
    return result
