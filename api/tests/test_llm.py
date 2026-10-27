from fastapi.testclient import TestClient

from app.main import app
from app.services.llm import MockLLM

client = TestClient(app)


def test_chat_answer_has_citation_tag():
    r = client.post("/chat", json={"customer_id": "C-204", "question": "What is the waiting period for pre-existing diseases?"})
    body = r.json()
    assert r.status_code == 200
    assert "[POL-" in body["answer"]
    assert len(body["citations"]) >= 1


def test_mock_llm_no_context_returns_not_found():
    out = MockLLM().complete("system", "CONTEXT:\n\nQUESTION: hi")
    assert "could not find" in out


def test_fake_citations_are_dropped():
    from app.services import answer as ans

    class FakeLLM:
        def complete(self, system, user):
            return "Made up fact [FAKE-DOC#CL-999]"

    original = ans.get_llm
    ans.get_llm = lambda: FakeLLM()
    try:
        r = client.post("/chat", json={"customer_id": "C-204", "question": "room rent"})
        assert r.json()["citations"] == []
        assert "could not find" in r.json()["answer"]
    finally:
        ans.get_llm = original


def test_draft_is_pending_approval():
    r = client.post("/drafts", json={"customer_id": "C-204"})
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "PENDING_APPROVAL"
    assert body["citations"][0]["clause_id"] == "CL-REN-01"