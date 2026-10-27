from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_customer_found():
    r = client.get("/customers/C-204")
    assert r.status_code == 200
    assert r.json()["tier"] == "Silver"


def test_customer_not_found():
    r = client.get("/customers/C-999")
    assert r.status_code == 404


def test_chat():
    r = client.post("/chat", json={"customer_id": "C-204", "question": "What is covered?"})
    assert r.status_code == 200
    assert r.json()["session_id"]