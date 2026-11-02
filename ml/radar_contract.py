"""Helpers for preparing CRM data for the agreed Radar interface."""

from datetime import date, timedelta


def interaction_counts_90d(customers, interactions, as_of):
    """Count interactions within [as_of - 89 days, as_of]."""
    ids = [row["customer_id"] for row in customers]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate customer IDs")

    counts = dict.fromkeys(ids, 0)
    start = as_of - timedelta(days=89)
    seen = set()

    for row in interactions:
        customer_id = row["customer_id"]
        interaction_id = row["interaction_id"]

        if customer_id not in counts:
            raise ValueError(f"Unknown customer: {customer_id}")
        if interaction_id in seen:
            raise ValueError(f"Duplicate interaction: {interaction_id}")
        seen.add(interaction_id)

        occurred = date.fromisoformat(row["date"])
        if start <= occurred <= as_of:
            counts[customer_id] += 1

    return counts
