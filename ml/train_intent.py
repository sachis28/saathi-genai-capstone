import argparse

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from ml.common import ARTIFACTS, LABELS, SEED, evaluate, load_split, write_json


def train():
    train, dev = load_split("train"), load_split("dev")
    candidates = []
    for c in [0.5, 2.0, 8.0]:
        model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                          ("classifier", LogisticRegression(C=c, max_iter=1000, random_state=SEED))])
        model.fit(train.text, train.label)
        score = float(f1_score(dev.label, model.predict(dev.text), average="macro", labels=LABELS))
        candidates.append((score, c, model))
    score, c, model = max(candidates, key=lambda x: x[0])
    output = ARTIFACTS / "tfidf_lr"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output / "model.joblib")
    write_json(output / "selection.json", {"criterion": "dev macro F1 only", "selected_C": c,
               "dev_macro_f1": score, "candidates": [{"C": x[1], "dev_macro_f1": x[0]} for x in candidates]})
    test = load_split("test")
    return evaluate("tfidf_lr", test, model.predict(test.text), {"selected_C": c, "dev_macro_f1": score})


if __name__ == "__main__":
    train()
