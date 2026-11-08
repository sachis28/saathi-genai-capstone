"""Radar input contract tests: interaction windows, duplicates, unknown customers and sentiment averages."""
from datetime import date, timedelta

import pytest

from ml.radar_contract import interaction_counts_90d

AS_OF = date(2026, 10, 28)
CUSTOMERS = [{"customer_id": "C-204"}, {"customer_id": "C-205"}]


def interaction(identifier, days_ago, customer_id="C-204"):
    return {
        "interaction_id": identifier,
        "customer_id": customer_id,
        "date": (AS_OF - timedelta(days=days_ago)).isoformat(),
    }


def test_window_boundaries():
    history = [
        interaction("I-1", 0),
        interaction("I-2", 89),
        interaction("I-3", 90),
        interaction("I-4", -1),
    ]
    assert interaction_counts_90d(CUSTOMERS, history, AS_OF) == {
        "C-204": 2,
        "C-205": 0,
    }


def test_unknown_customer_rejected():
    with pytest.raises(ValueError, match="Unknown customer"):
        interaction_counts_90d(
            CUSTOMERS, [interaction("I-1", 1, "UNKNOWN")], AS_OF
        )


def test_duplicate_interaction_rejected():
    row = interaction("I-1", 1)
    with pytest.raises(ValueError, match="Duplicate interaction"):
        interaction_counts_90d(CUSTOMERS, [row, row], AS_OF)


from ml.radar_contract import customer_sentiment_90d


def sentiment_record(identifier, days_ago, positive, neutral, negative):
    row = interaction(identifier, days_ago)
    row["confidence_scores"] = {
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
    }
    return row


def test_sentiment_mean():
    records = [
        sentiment_record("I-1", 0, 0.8, 0.1, 0.1),
        sentiment_record("I-2", 89, 0.1, 0.2, 0.7),
    ]
    result = customer_sentiment_90d(CUSTOMERS, records, AS_OF)
    assert result["C-204"] == pytest.approx(0.05)
    assert result["C-205"] is None


def test_sentiment_excludes_old_and_future():
    records = [
        sentiment_record("I-1", 90, 1.0, 0.0, 0.0),
        sentiment_record("I-2", -1, 0.0, 0.0, 1.0),
    ]
    result = customer_sentiment_90d(CUSTOMERS, records, AS_OF)
    assert result == {"C-204": None, "C-205": None}


def test_sentiment_empty_history():
    assert customer_sentiment_90d(CUSTOMERS, [], AS_OF) == {
        "C-204": None,
        "C-205": None,
    }


def test_sentiment_invalid_confidence():
    records = [sentiment_record("I-1", 0, float("nan"), 0.0, 0.0)]
    with pytest.raises(ValueError, match="Invalid confidence score"):
        customer_sentiment_90d(CUSTOMERS, records, AS_OF)
