"""Generate reproducible synthetic demo data for Saathi."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

from schemas import CustomerRecord, InteractionRecord

SEED = 42
REFERENCE_DATE = date(2026, 10, 28)
DATA_DIR = Path(__file__).resolve().parent


def write_json(filename, records):
    payload = [record.model_dump(mode="json") for record in records]
    output = DATA_DIR / filename
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Created {output.name}: {len(records)} records")


def main():
    rng = random.Random(SEED)

    # Proposed demo scenarios. All customer names and messages are synthetic.
    scenarios = [
        {
            "id": "C-204", "tier": "Silver", "consent": True,
            "city": "Pune", "days": 15,
            "messages": [
                "Please explain the coverage under my Silver policy.",
                "Please share the documents needed for renewal.",
                "I would like help renewing my policy.",
            ],
        },
        {
            "id": "C-311", "tier": "Gold", "consent": True,
            "city": "Mumbai", "days": 7,
            "messages": [
                "My policy renewal is approaching.",
                "Please explain the renewal process.",
                "I have not received the renewal details yet.",
            ],
        },
        {
            "id": "C-118", "tier": "Silver", "consent": True,
            "city": "Nagpur", "days": 60,
            "messages": [
                "Please explain the available policy tiers.",
                "I would like to understand upgrade options.",
                "Thank you for explaining the options.",
            ],
        },
        {
            "id": "C-450", "tier": "Gold", "consent": True,
            "city": "Nashik", "days": -5,
            "messages": [
                "I missed my renewal date.",
                "Please explain what I should do next.",
                "Please arrange a follow-up with my agent.",
            ],
        },
        {
            "id": "C-205", "tier": "Gold", "consent": False,
            "city": "Pune", "days": 20,
            "messages": [
                "Please explain my current policy.",
                "I do not consent to outbound messages.",
                "Please keep my communication preference unchanged.",
            ],
        },
        {
            "id": "C-999", "tier": "Silver", "consent": True,
            "city": "Mumbai", "days": 90,
            "messages": [
                "I would like an overview of my policy.",
                "Please explain how to contact my agent.",
                "Thank you for the information.",
            ],
        },
    ]

    customers = []
    interactions = []

    for number, scenario in enumerate(scenarios, start=1):
        customer = CustomerRecord(
            customer_id=scenario["id"],
            name=f"Synthetic Customer {number:02d}",
            product="Health",
            tier=scenario["tier"],
            city=scenario["city"],
            segment="Retail",
            consent=scenario["consent"],
            agent_id=f"A-{((number - 1) % 3) + 1:03d}",
            renewal_date=REFERENCE_DATE + timedelta(days=scenario["days"]),
        )
        customers.append(customer)

        # Sort offsets so each customer's history is chronological.
        offsets = sorted(rng.sample(range(1, 31), 3), reverse=True)

        for offset, message in zip(offsets, scenario["messages"]):
            interactions.append(
                InteractionRecord(
                    interaction_id=f"I-{len(interactions) + 1:04d}",
                    customer_id=customer.customer_id,
                    date=REFERENCE_DATE - timedelta(days=offset),
                    channel=rng.choice(["phone", "email", "chat"]),
                    text=message,
                )
            )

    customer_ids = {customer.customer_id for customer in customers}
    interaction_ids = {
        interaction.interaction_id for interaction in interactions
    }

    assert len(customer_ids) == len(customers), "Duplicate customer IDs"
    assert len(interaction_ids) == len(interactions), "Duplicate interaction IDs"
    assert all(
        interaction.customer_id in customer_ids
        for interaction in interactions
    ), "Interaction references an unknown customer"

    write_json("customers.json", customers)
    write_json("interactions.json", interactions)


if __name__ == "__main__":
    main()
