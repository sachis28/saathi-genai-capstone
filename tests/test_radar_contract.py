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
