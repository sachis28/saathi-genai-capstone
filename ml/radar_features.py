"""Build one Renewal Radar feature row per customer."""

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_features(customers, interactions, as_of):
    """Use only interactions on or before the reference date."""
    customer_ids = {customer["customer_id"] for customer in customers}

    if len(customer_ids) != len(customers):
        raise ValueError("Duplicate customer IDs")

    histories = {customer_id: [] for customer_id in customer_ids}
    interaction_ids = set()

    for interaction in interactions:
        interaction_id = interaction["interaction_id"]
        customer_id = interaction["customer_id"]

        if interaction_id in interaction_ids:
            raise ValueError(f"Duplicate interaction: {interaction_id}")
        interaction_ids.add(interaction_id)

        if customer_id not in histories:
            raise ValueError(f"Unknown customer: {customer_id}")

        interaction_date = date.fromisoformat(interaction["date"])
        if interaction_date <= as_of:
            histories[customer_id].append(interaction_date)

    rows = []
    for customer in customers:
        customer_id = customer["customer_id"]
        history = histories[customer_id]
        renewal_date = date.fromisoformat(customer["renewal_date"])

        rows.append({
            "customer_id": customer_id,
            "as_of_date": as_of.isoformat(),
            "days_to_renewal": (renewal_date - as_of).days,
            "interaction_count": len(history),
            "days_since_last_interaction": (
                (as_of - max(history)).days if history else None
            ),
        })

    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        required=True,
        type=date.fromisoformat,
        help="Reference date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    customers = json.loads(
        (ROOT / "data/customers.json").read_text(encoding="utf-8")
    )
    interactions = json.loads(
        (ROOT / "data/interactions.json").read_text(encoding="utf-8")
    )

    rows = build_features(customers, interactions, args.as_of)
    output = ROOT / "data/radar_features.json"
    output.write_text(
        json.dumps(rows, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Created {output.name}: {len(rows)} feature rows")
    for row in rows:
        print(
            f"{row['customer_id']}: "
            f"days_to_renewal={row['days_to_renewal']}, "
            f"interaction_count={row['interaction_count']}, "
            f"days_since_last_interaction="
            f"{row['days_since_last_interaction']}"
        )


if __name__ == "__main__":
    main()
