"""Export CRM-linked Radar features using the agreed field names."""

import argparse
import json
from datetime import date
from pathlib import Path

from data.schemas import CustomerRecord, InteractionRecord
from ml.radar_contract import interaction_counts_90d

ROOT = Path(__file__).resolve().parents[1]


def build_rows(customers, interactions, sentiment, as_of):
    customers = [
        CustomerRecord.model_validate(row).model_dump(mode="json")
        for row in customers
    ]
    interactions = [
        InteractionRecord.model_validate(row).model_dump(mode="json")
        for row in interactions
    ]
    counts = interaction_counts_90d(customers, interactions, as_of)

    by_id = {row["customer_id"]: row for row in sentiment}
    if len(by_id) != len(sentiment):
        raise ValueError("Duplicate customer sentiment IDs")
    if set(by_id) != set(counts):
        raise ValueError("Customer sentiment IDs do not match CRM")

    rows = []
    for customer in customers:
        cid = customer["customer_id"]
        record = by_id[cid]

        if record["as_of_date"] != as_of.isoformat():
            raise ValueError(f"{cid}: sentiment reference date mismatch")

        score = record["sentiment_score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not -1 <= score <= 1
        ):
            raise ValueError(f"{cid}: missing or invalid sentiment score")

        if counts[cid] > 10000:
            raise ValueError(f"{cid}: interaction count exceeds contract")

        rows.append({
            "customer_id": cid,
            "days_to_renewal": (
                date.fromisoformat(customer["renewal_date"]) - as_of
            ).days,
            "interaction_count_90d": counts[cid],
            "sentiment_score": float(score),
            "annual_premium_inr": customer["annual_premium_inr"],
            "consent": customer["consent"],
        })

    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    def load(filename):
        return json.loads(
            (ROOT / "data" / filename).read_text(encoding="utf-8")
        )

    rows = build_rows(
        load("customers.json"),
        load("interactions.json"),
        load("customer_sentiment.json"),
        args.as_of,
    )

    output = ROOT / "data/radar_input.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(rows, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)

    print(f"Created {output.name}: {len(rows)} feature rows")
    for row in rows:
        print(
            row["customer_id"],
            "days:", row["days_to_renewal"],
            "premium INR:", row["annual_premium_inr"],
            "consent:", row["consent"],
        )


if __name__ == "__main__":
    main()
