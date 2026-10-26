"""Descriptive synthetic subgroup audits, not a fairness certification."""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from ml.common import ARTIFACTS, DOCS, LABELS, SEED, load_split, write_json


def bootstrap_accuracy(y,pred):
    rng = np.random.default_rng(SEED)
    values = np.asarray(y)==np.asarray(pred)
    samples = [float(values[rng.integers(0,len(values),len(values))].mean()) for _ in range(1000)]
    return [float(v) for v in np.quantile(samples,[0.025,0.975])]


def main():
    DOCS.mkdir(exist_ok=True)
    rows, counterfactual = [], []
    for path in sorted(ARTIFACTS.glob("*/predictions.csv")):
        frame = pd.read_csv(path)
        if not {"age_band","gender","region"}.issubset(frame.columns):
            continue
        for attribute in ["age_band","gender","region"]:
            for group,part in frame.groupby(attribute):
                interval = bootstrap_accuracy(part.label,part.prediction)
                rows.append({"model":path.parent.name,"attribute":attribute,"group":str(group),"n":len(part),
                    "accuracy":float(accuracy_score(part.label,part.prediction)),
                    "macro_f1":float(f1_score(part.label,part.prediction,labels=LABELS,average="macro",zero_division=0)),
                    "accuracy_ci95":interval,"small_group":len(part)<30})
    model = joblib.load(ARTIFACTS / "tfidf_lr" / "model.joblib")
    # Separate surface probe; synthetic metadata above is not part of input text.
    base = "Compare Silver and Gold for C-204"
    baseline = model.predict([base])[0]
    for suffix in ["The customer is a woman.","The customer is a man.","The customer is nonbinary.",
                   "The customer is 25 years old.","The customer is 70 years old.",
                   "The customer lives in a rural area.","The customer lives in an urban area."]:
        prediction = model.predict([base+". "+suffix])[0]
        counterfactual.append({"text":base+". "+suffix,"prediction":prediction,"unchanged":bool(prediction==baseline)})
    write_json(ARTIFACTS / "fairness.json",{"subgroups":rows,"tfidf_surface_probes":counterfactual})
    lines = ["# Fairness evaluation", "", "Scope: synthetic English intent fixtures with artificial demographic metadata. These results cannot establish fairness for real customers or multilingual inputs.",
             "", "Protected attributes are excluded from predictive features. Metadata-only demographic changes cannot influence a text-only model; that is an architectural property, not proof of unbiased language behavior.",
             "", "| Model | Attribute | Group | n | Accuracy | Macro F1 | Bootstrap accuracy 95% interval |", "|---|---|---|---:|---:|---:|---|"]
    for row in rows:
        lo,hi = row["accuracy_ci95"]
        lines.append(f"| {row['model']} | {row['attribute']} | {row['group']} | {row['n']} | {row['accuracy']:.3f} | {row['macro_f1']:.3f} | {lo:.3f}–{hi:.3f} |")
    lines += ["", "Intervals use 1,000 bootstrap resamples (seed 42); they do not correct for multiple comparisons or correlated templates. Small or intersecting groups need more independent examples.",
              "", f"TF-IDF surface probes: {sum(r['unchanged'] for r in counterfactual)}/{len(counterfactual)} preserved the baseline intent. This covers one question only.",
              "", "Before release: collect consented representative English/Marathi/Hindi questions, review labels with domain experts, evaluate subgroup recall and intersectional errors, define acceptable gaps with the team, and repeat on real data. No fairness pass threshold was specified in the execution plan.",
              "", "Renewal Radar excludes age, gender and region, but proxy bias is still possible. Synthetic outcomes are unsuitable for real eligibility, premium, or customer prioritization decisions."]
    (DOCS / "fairness_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
