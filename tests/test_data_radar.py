import json
from collections import Counter
from datetime import date
from pathlib import Path

from data.schemas import CustomerRecord, InteractionRecord
from ml.radar_features import build_features

ROOT = Path(__file__).resolve().parents[1]


def load(filename):
    return json.loads(
        (ROOT / "data" / filename).read_text(encoding="utf-8")
    )


def test_customer_data():
    customers = [
        CustomerRecord.model_validate(row)
        for row in load("customers.json")
    ]
    by_id = {c.customer_id: c for c in customers}

    assert len(customers) == len(by_id) == 6
    assert set(by_id) == {
        "C-204", "C-311", "C-118", "C-450", "C-205", "C-999"
    }
    assert by_id["C-204"].product == "Health"
    assert by_id["C-204"].tier == "Silver"
    assert by_id["C-204"].consent is True
    assert by_id["C-205"].consent is False


def test_interaction_data():
    interactions = [
        InteractionRecord.model_validate(row)
        for row in load("interactions.json")
    ]
    customer_ids = {c["customer_id"] for c in load("customers.json")}

    assert len(interactions) == 18
    assert len({i.interaction_id for i in interactions}) == 18
    assert all(i.customer_id in customer_ids for i in interactions)

    counts = Counter(i.customer_id for i in interactions)
    assert all(counts[cid] == 3 for cid in customer_ids)


def test_demo_features():
    rows = build_features(
        load("customers.json"),
        load("interactions.json"),
        date(2026, 10, 28),
    )
    expected = {
        "C-204": 15, "C-311": 7, "C-118": 60,
        "C-450": -5, "C-205": 20, "C-999": 90,
    }

    assert len(rows) == 6
    assert {r["customer_id"] for r in rows} == set(expected)
    for row in rows:
        assert row["days_to_renewal"] == expected[row["customer_id"]]
        assert row["interaction_count"] == 3
        assert row["days_since_last_interaction"] >= 0

    assert rows == load("radar_features.json")


def test_no_history():
    rows = build_features(
        [{"customer_id": "TEST-1", "renewal_date": "2026-10-28"}],
        [],
        date(2026, 10, 28),
    )
    assert rows[0]["days_to_renewal"] == 0
    assert rows[0]["interaction_count"] == 0
    assert rows[0]["days_since_last_interaction"] is None


def test_future_interaction_excluded():
    rows = build_features(
        [{"customer_id": "TEST-1", "renewal_date": "2026-10-29"}],
        [{
            "interaction_id": "TEST-I1",
            "customer_id": "TEST-1",
            "date": "2026-10-29",
        }],
        date(2026, 10, 28),
    )
    assert rows[0]["interaction_count"] == 0
    assert rows[0]["days_since_last_interaction"] is None
