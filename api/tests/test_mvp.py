from fastapi.testclient import TestClient

from app.main import app
from app.services import memory

client = TestClient(app)


def test_full_mvp_flow():
    # 1. Ask a question
    chat = client.post("/chat", json={"customer_id": "C-204", "question": "What is the waiting period for pre-existing diseases?"})
    assert chat.status_code == 200
    assert len(chat.json()["citations"]) >= 1

    # 2. Create a draft
    draft = client.post("/drafts", json={"customer_id": "C-204"}).json()
    assert draft["status"] == "PENDING_APPROVAL"
    draft_id = draft["draft_id"]

    # 3. Sending before approval is blocked
    r = client.post(f"/drafts/{draft_id}/send")
    assert r.status_code == 409
    assert "BLOCKED" in r.json()["detail"]

    # 4. Approve, then send
    assert client.post(f"/drafts/{draft_id}/approve").json()["status"] == "APPROVED"
    sent = client.post(f"/drafts/{draft_id}/send")
    assert sent.status_code == 200
    assert sent.json()["status"] == "SIMULATED_SENT"


def test_send_blocked_without_consent():
    draft_id = client.post("/drafts", json={"customer_id": "C-205"}).json()["draft_id"]
    client.post(f"/drafts/{draft_id}/approve")
    r = client.post(f"/drafts/{draft_id}/send")
    assert r.status_code == 403
    assert "consent" in r.json()["detail"]


def test_cannot_approve_twice():
    draft_id = client.post("/drafts", json={"customer_id": "C-204"}).json()["draft_id"]
    client.post(f"/drafts/{draft_id}/approve")
    r = client.post(f"/drafts/{draft_id}/approve")
    assert r.status_code == 409


def test_follow_up_uses_memory():
    first = client.post("/chat", json={"customer_id": "C-204", "question": "What is the hospitalisation cover in Gold?"}).json()
    sid = first["session_id"]

    second = client.post("/chat", json={"customer_id": "C-204", "question": "and what about Platinum?", "session_id": sid}).json()
    assert "hospitalisation cover in Gold" in second["resolved_question"]
    assert "Platinum" in second["resolved_question"]

    history = client.get(f"/sessions/{sid}").json()
    assert len(history) == 2


def test_new_question_is_not_rewritten():
    memory.add_turn("s-test", "Gold cover?", "Gold cover?", "answer")
    assert memory.resolve_question("s-test", "What is the waiting period for pre-existing diseases?") \
        == "What is the waiting period for pre-existing diseases?"
        