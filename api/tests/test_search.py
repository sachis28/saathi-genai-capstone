from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_gold_exclusion_found():
    r = client.post("/search", json={"query": "Is cosmetic surgery excluded in Gold?", "k": 3, "tier": "Gold"})
    ids = [h["clause_id"] for h in r.json()]
    assert "EXC-GOLD-07" in ids


def test_tier_filter():
    r = client.post("/search", json={"query": "hospitalisation cover", "tier": "Silver"})
    assert all(h["tier"] in ("Silver", "All") for h in r.json())


def test_chat_returns_real_citations():
    r = client.post("/chat", json={"customer_id": "C-204", "question": "What is the waiting period for pre-existing diseases?"})
    assert r.status_code == 200
    assert r.json()["citations"][0]["source_id"].startswith("POL-")