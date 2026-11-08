"""Plan comparison tests: detecting "Silver vs Gold" questions and returning a cited table."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import comparison_tiers, is_comparison

client = TestClient(app)


def test_comparison_detection():
    assert is_comparison("Compare Silver and Gold for C-204")
    assert is_comparison("Silver vs Gold?")
    assert is_comparison("How does Gold compare?")
    assert not is_comparison("What is the hospitalisation cover in Gold?")
    assert not is_comparison("and what about Platinum?")
    assert comparison_tiers("Compare with Gold", "Silver") == ["Silver", "Gold"]


def test_chat_returns_a_cited_comparison_table():
    body = client.post("/chat", json={"customer_id": "C-204", "question": "Compare Silver and Gold"}).json()
    table = body["comparison"]
    assert table["tiers"] == ["Silver", "Gold"]
    assert table["rows"]
    for row in table["rows"]:
        for tier, cell in row["cells"].items():
            if cell:
                assert cell["source_id"].endswith(tier.upper())   # each cell comes from its own tier's policy
    cited = {(c["source_id"], c["clause_id"]) for c in body["citations"]}
    cells = {(c["source_id"], c["clause_id"]) for r in table["rows"] for c in r["cells"].values() if c}
    assert cells == cited


def test_follow_up_is_not_turned_into_a_comparison():
    first = client.post("/chat", json={"customer_id": "C-204", "question": "What is the hospitalisation cover in Gold?"}).json()
    r = client.post("/chat", json={"customer_id": "C-204", "question": "and what about Platinum?",
                                   "session_id": first["session_id"]}).json()
    assert r["comparison"] is None


def test_compare_endpoint_rejects_a_single_tier():
    assert client.post("/compare?customer_id=C-204&tiers=Gold").status_code == 422
