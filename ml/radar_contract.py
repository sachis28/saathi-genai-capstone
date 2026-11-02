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


def customer_sentiment_90d(customers, sentiment_records, as_of):
    """Agreed mean of positive-minus-negative scores over 90 days."""
    import math

    # Reuse customer-ID, duplicate-ID and date validation.
    interaction_counts_90d(customers, sentiment_records, as_of)

    values = {row["customer_id"]: [] for row in customers}
    start = as_of - timedelta(days=89)

    for row in sentiment_records:
        scores = row["confidence_scores"]
        if set(scores) != {"positive", "neutral", "negative"}:
            raise ValueError("Invalid confidence fields")

        for value in scores.values():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError("Invalid confidence score")

        if abs(sum(scores.values()) - 1) >= 0.02:
            raise ValueError("Confidence scores must sum approximately to one")

        occurred = date.fromisoformat(row["date"])
        if start <= occurred <= as_of:
            values[row["customer_id"]].append(
                scores["positive"] - scores["negative"]
            )

    return {
        customer_id: sum(scores) / len(scores) if scores else None
        for customer_id, scores in values.items()
    }
