"""Export agreed customer-level sentiment features."""

import argparse
import json
from datetime import date
from pathlib import Path

from ml.radar_contract import customer_sentiment_90d

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    def load(filename):
        return json.loads(
            (ROOT / "data" / filename).read_text(encoding="utf-8")
        )

    customers = load("customers.json")
    interactions = load("interactions.json")
    sentiment = load("interaction_sentiment.json")

    original = {row["interaction_id"]: row for row in interactions}
    if len(original) != len(interactions):
        raise ValueError("Duplicate source interaction IDs")

    sentiment_ids = [row["interaction_id"] for row in sentiment]
    if len(sentiment_ids) != len(set(sentiment_ids)):
        raise ValueError("Duplicate sentiment interaction IDs")
    if set(sentiment_ids) != set(original):
        raise ValueError("Sentiment coverage does not match interactions")

    for row in sentiment:
        source = original[row["interaction_id"]]
        if (
            row["customer_id"] != source["customer_id"]
            or row["date"] != source["date"]
        ):
            raise ValueError("Sentiment customer/date mismatch")

    scores = customer_sentiment_90d(customers, sentiment, args.as_of)
    rows = [
        {
            "customer_id": customer["customer_id"],
            "as_of_date": args.as_of.isoformat(),
            "sentiment_score": scores[customer["customer_id"]],
        }
        for customer in customers
    ]

    output = ROOT / "data/customer_sentiment.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(rows, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)

    print(f"Created {output.name}: {len(rows)} customer rows")
    for row in rows:
        print(row["customer_id"], row["sentiment_score"])


if __name__ == "__main__":
    main()
