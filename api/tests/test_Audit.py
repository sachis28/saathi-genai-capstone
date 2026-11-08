"""Audit log tests: events are hash-chained, editing or deleting a line is detected,
and PII is redacted before it is written."""
import json

import pytest

from app.services import audit


@pytest.fixture(autouse=True)
def temp_log(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit_log.jsonl")


def test_empty_log_is_valid():
    assert audit.verify_chain() == (True, None, 0)


def test_chain_links_events():
    a = audit.log_event("chat", customer_id="C-204")
    b = audit.log_event("draft_created", customer_id="C-204")
    assert a["prev_hash"] == audit.GENESIS
    assert b["prev_hash"] == a["hash"]
    assert audit.verify_chain() == (True, None, 2)


def test_tampering_is_detected():
    audit.log_event("chat", customer_id="C-204")
    audit.log_event("draft_approved", draft_id="d1")
    audit.log_event("draft_sent", draft_id="d1")

    lines = audit.AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[1])
    row["data"]["draft_id"] = "HACKED"
    lines[1] = json.dumps(row)
    audit.AUDIT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, broken_at, total = audit.verify_chain()
    assert valid is False
    assert broken_at == 2
    assert total == 3


def test_deleted_event_is_detected():
    for name in ("a", "b", "c"):
        audit.log_event(name)
    lines = audit.AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    audit.AUDIT_FILE.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    assert audit.verify_chain()[0] is False


def test_pii_is_redacted_in_log():
    entry = audit.log_event("chat", note="call 9876543210")
    assert "9876543210" not in entry["data"]["note"]
    assert "[PHONE]" in entry["data"]["note"]
