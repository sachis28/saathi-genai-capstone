"""Generate only ML-owned synthetic fixtures. Never overwrite a locked split by default."""
import argparse
import itertools
import math
import random

import numpy as np
import pandas as pd

from ml.common import DATA, LABELS, SEED, sha256, write_json

# Families are assigned before expansion, preventing the same sentence template
# appearing in training and the locked test set. Products/customers may recur.
FAMILIES = {
    "compare_products": [
        ["Compare {p} and {q} for {c}", "What differs between {p} and {q} for {c}?", "Show {p} versus {q} for {c}", "Help {c} choose between {p} and {q}"],
        ["List the differences in {p} and {q} for {c}", "Which is better for {c}, {p} or {q}?"],
        ["Put {p} alongside {q} for customer {c}", "How does {p} stack up against {q} for {c}?"]],
    "coverage_question": [
        ["What does {p} cover for {c}?", "Explain exclusions in {p} for {c}", "Is hospitalization included in {p} for {c}?", "Tell {c} the waiting period for {p}"],
        ["Does {p} pay for surgery for {c}?", "What are the limitations of {p} for {c}?"],
        ["Would a hospital claim qualify under {p} for {c}?", "Where does protection stop under {p} for {c}?"]],
    "renewal_draft": [
        ["Draft a renewal reminder for {c} on {p}", "Write a renewal message to {c} for {p}", "Prepare a premium renewal draft for {c} on {p}", "Help compose a renewal notice for {c} about {p}"],
        ["Create a reminder draft about {p} expiring for {c}", "Suggest a renewal email for {c} on {p}"],
        ["Compose a policy extension reminder for {c} with {p}", "Put together a message asking {c} to renew {p}"]],
    "customer_lookup": [
        ["Show customer {c}'s profile for {p}", "Look up contact details for {c} on {p}", "Get the CRM record for {c} with {p}", "Find customer {c} and their {p} policy"],
        ["Fetch account details of {c} on {p}", "Display the saved information about {c} with {p}"],
        ["Who is {c}, the holder of {p}?", "Pull up {c}'s registered particulars for {p}"]],
    "out_of_scope": [
        ["Tell {c} a joke about {p}", "Predict cricket results for {c} instead of {p}", "Give {c} a cake recipe, forget {p}", "Book a flight for {c}, ignore {p}"],
        ["Recommend a movie to {c} rather than {p}", "Write a poem for {c} about {p}"],
        ["Solve a calculus problem for {c}, unrelated to {p}", "Find a pizza restaurant for {c}, not {p}"]],
}


def intent_frame(split, family_index, n_per_label):
    rng = random.Random(SEED + family_index)
    rows = []
    products = ["Silver", "Gold", "Platinum", "Silver Plus", "Gold Plus"]
    customers = ["C-204", "C-311", "C-118", "C-450", "C-205", "C-999", "C-101", "C-102", "C-103", "C-104"]
    for label in LABELS:
        candidates = []
        for fi, family in enumerate(FAMILIES[label][family_index]):
            for p, c in itertools.product(products, customers):
                q = products[(products.index(p) + 1) % len(products)]
                for polite in ("", "Please "):
                    candidates.append((polite + family.format(p=p, q=q, c=c), f"{label}-{split}-{fi}"))
        rng.shuffle(candidates)
        for i, (text, family) in enumerate(candidates[:n_per_label]):
            rows.append({"id": f"{split}-{label}-{i:03}", "text": text, "label": label,
                         "template_family": family, "age_band": ["18-39", "40-59", "60+"][i % 3],
                         "gender": ["woman", "man", "nonbinary"][i // 3 % 3],
                         "region": ["urban", "rural"][i // 9 % 2]})
    return pd.DataFrame(rows).sample(frac=1, random_state=SEED).reset_index(drop=True)


def generate(force=False):
    DATA.mkdir(parents=True, exist_ok=True)
    if (DATA / "manifest.json").exists() and not force:
        raise FileExistsError("Dataset already locked; use --force only to intentionally version a new dataset")
    for name, family, size in [("train", 0, 200), ("dev", 1, 40), ("test", 2, 30)]:
        intent_frame(name, family, size).to_csv(DATA / f"intent_{name}.csv", index=False)
    rng = np.random.default_rng(SEED)
    n = 1200
    days = rng.integers(1, 120, n)
    interactions = rng.integers(0, 12, n)
    sentiment = rng.uniform(-1, 1, n)
    premium = rng.uniform(1000, 50000, n).round(2)
    risk = 1 / (1 + np.exp(-(-0.5 + 0.028 * (45-days) - 1.1*sentiment - 0.12*interactions)))
    radar = pd.DataFrame({"customer_id": [f"C-{i+1000}" for i in range(n)], "days_to_renewal": days,
                          "interaction_count_90d": interactions, "sentiment_score": sentiment,
                          "premium": premium, "consent": rng.random(n) > 0.15,
                          "age_band": np.resize(["18-39", "40-59", "60+"], n),
                          "nonrenewed": (rng.random(n) < risk).astype(int)})
    radar.to_csv(DATA / "radar.csv", index=False)
    write_json(DATA / "manifest.json", {
        "seed": SEED, "provenance": "Generated synthetic ML fixtures; no real customers or policy facts.",
        "intent_labels": LABELS, "split_sizes": {"train": 1000, "dev": 200, "test": 150},
        "split_strategy": "disjoint authored template families before expansion; no normalized text overlap",
        "protected_attributes": "Synthetic evaluation-only metadata, independent of text; not representative demographics",
        "radar_target": "Simulated nonrenewal drawn from a noisy logistic rule; not business ground truth",
        "files": {p.name: sha256(p) for p in sorted(DATA.glob("*.csv"))},
    })
    print("Generated and hash-locked synthetic data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    generate(parser.parse_args().force)
