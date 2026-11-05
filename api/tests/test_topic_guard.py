from fastapi.testclient import TestClient

from app.main import app
from app.services import memory
from app.services.topic_guard import OFF_TOPIC_MSG, is_on_topic

client = TestClient(app)


def test_off_topic_inputs():
    for q in ["dumb?", "hi", "tell me a joke", "What is the weather in Pune?", "order a pizza"]:
        assert not is_on_topic(q), q


def test_policy_questions_stay_on_topic():
    for q in ["room rent", "What is covered?", "Platinum?", "Can I add my spouse?", "What is the copay?",
              "What is the waiting period for pre-existing diseases?", "Is the deductible waived?"]:
        assert is_on_topic(q), q


def test_short_off_topic_input_is_not_merged_into_previous_question():
    assert not memory.is_follow_up("dumb?")
    assert memory.is_follow_up("Platinum?")
    assert memory.is_follow_up("and what about Platinum?")


def test_chat_redirects_off_topic_after_a_real_question():
    first = client.post("/chat", json={"customer_id": "C-204", "question": "What is the hospitalisation cover in Gold?"}).json()
    r = client.post("/chat", json={"customer_id": "C-204", "question": "dumb?", "session_id": first["session_id"]}).json()
    assert r["answer"] == OFF_TOPIC_MSG
    assert r["citations"] == []
    assert r["intent"] == "out_of_scope"


def test_customer_details_question_is_not_treated_as_off_topic():
    r = client.post("/chat", json={"customer_id": "C-204", "question": "what is this customers details"}).json()
    assert r["answer"].startswith("From the customer record")
    assert "C-204" in r["answer"]
