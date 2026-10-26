import json

import pandas as pd
import pandera.pandas as pa

from ml.common import ARTIFACTS, DATA, LABELS, load_split, sha256, write_json

intent_schema = pa.DataFrameSchema({
    "id": pa.Column(str, unique=True),
    "text": pa.Column(str, pa.Check.str_length(min_value=5, max_value=2000)),
    "label": pa.Column(str, pa.Check.isin(LABELS)),
    "template_family": pa.Column(str),
    "age_band": pa.Column(str, pa.Check.isin(["18-39", "40-59", "60+"])),
    "gender": pa.Column(str, pa.Check.isin(["woman", "man", "nonbinary"])),
    "region": pa.Column(str, pa.Check.isin(["urban", "rural"])),
}, strict=True)

radar_schema = pa.DataFrameSchema({
    "customer_id": pa.Column(str, unique=True),
    "days_to_renewal": pa.Column(int, pa.Check.in_range(0, 365)),
    "interaction_count_90d": pa.Column(int, pa.Check.in_range(0, 10000)),
    "sentiment_score": pa.Column(float, pa.Check.in_range(-1, 1)),
    "premium": pa.Column(float, pa.Check.gt(0)),
    "consent": pa.Column(bool),
    "age_band": pa.Column(str, pa.Check.isin(["18-39", "40-59", "60+"])),
    "nonrenewed": pa.Column(int, pa.Check.isin([0, 1])),
}, strict=True)

radar_inference_schema = radar_schema.remove_columns(["age_band", "nonrenewed"])


def validate_radar_inference(frame):
    # Known training/audit columns may be supplied by the local fixture loader,
    # but are stripped before inference and are never sent to a cloud endpoint.
    return radar_inference_schema.validate(frame.drop(columns=["age_band", "nonrenewed"], errors="ignore"), lazy=True)


def normalized(text):
    return " ".join(text.lower().split())


def validate_splits(splits):
    for name, expected in [("train", 1000), ("dev", 200), ("test", 150)]:
        frame = intent_schema.validate(splits[name], lazy=True)
        if len(frame) != expected or set(frame.label) != set(LABELS):
            raise ValueError(f"Invalid {name} size or missing labels")
        if frame.text.map(normalized).duplicated().any():
            raise ValueError(f"Duplicate normalized text within {name}")
    names = list(splits)
    for i, name in enumerate(names):
        for other in names[i+1:]:
            if set(splits[name].text.map(normalized)) & set(splits[other].text.map(normalized)):
                raise ValueError(f"Text leakage between {name} and {other}")
            if set(splits[name].template_family) & set(splits[other].template_family):
                raise ValueError(f"Template leakage between {name} and {other}")


def main():
    splits = {s: load_split(s) for s in ["train", "dev", "test"]}
    validate_splits(splits)
    manifest = json.loads((DATA / "manifest.json").read_text())
    if sha256(DATA / "radar.csv") != manifest["files"]["radar.csv"]:
        raise ValueError("Radar hash mismatch")
    radar_schema.validate(pd.read_csv(DATA / "radar.csv"), lazy=True)
    write_json(ARTIFACTS / "data_validation.json", {
        "status": "passed", "rows": {k: len(v) for k,v in splits.items()},
        "radar_rows": 1200, "normalized_text_overlap": 0, "template_family_overlap": 0,
        "scope": "ML fixtures only; CRM/API schemas await Sachi and Shreya's contracts",
    })
    print("Pandera schemas, counts, hashes, and split leakage checks passed")


if __name__ == "__main__":
    main()
