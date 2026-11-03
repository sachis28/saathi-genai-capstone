from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import summary


def make_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    summary.get_llm.cache_clear()
    app = FastAPI()
    app.include_router(summary.router)
    from app.services.worklist_access import authenticate_agent, AgentPrincipal
    app.dependency_overrides[authenticate_agent] = lambda: AgentPrincipal(agent_id='A-001', allowed_products=('Health',))
    return TestClient(app)


def test_summary_returns_valid_citations(monkeypatch):
    with make_client(monkeypatch) as client:
        response = client.get("/customers/C-204/summary")

    assert response.status_code == 200
    body = response.json()
    history = summary.load_records("interactions.json")
    valid_ids = {
        row["interaction_id"]
        for row in history
        if row["customer_id"] == "C-204"
    }

    assert body["customer_id"] == "C-204"
    assert body["interaction_ids"]
    assert set(body["interaction_ids"]) <= valid_ids
    assert all(
        f"[{interaction_id}]" in body["summary"]
        for interaction_id in body["interaction_ids"]
    )


def test_unknown_customer(monkeypatch):
    with make_client(monkeypatch) as client:
        response = client.get("/customers/DOES-NOT-EXIST/summary")

    assert response.status_code == 404


def test_no_interaction_history(monkeypatch):
    with make_client(monkeypatch) as client:
        from app.models.schemas import Customer
        monkeypatch.setattr(summary, 'authorize_customer', lambda cid, aid: Customer(customer_id=cid,name='test',product='Health',tier='Gold',agent_id=aid))
        monkeypatch.setattr(summary, 'load_records', lambda filename: [])
        response = client.get("/customers/TEST-1/summary")

    assert response.status_code == 200
    assert response.json()["interaction_ids"] == []
    assert response.json()["summary"] == "No interaction history available."


def test_unknown_citation_rejected(monkeypatch):
    class InvalidCitationLLM:
        def complete(self, system, user):
            return "Unsupported response [I-9999]"

    with make_client(monkeypatch) as client:
        monkeypatch.setattr(
            summary, "get_llm", lambda: InvalidCitationLLM()
        )
        response = client.get("/customers/C-204/summary")

    assert response.status_code == 502


def test_missing_citations_rejected(monkeypatch):
    class NoCitationLLM:
        def complete(self, system, user):
            return "A response without citations."

    with make_client(monkeypatch) as client:
        monkeypatch.setattr(summary, "get_llm", lambda: NoCitationLLM())
        response = client.get("/customers/C-204/summary")

    assert response.status_code == 502
