import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from app.services.safety import redact

AUDIT_FILE = Path(os.getenv("AUDIT_FILE", Path(__file__).resolve().parents[3] / "data" / "audit_log.jsonl"))
GENESIS = "0" * 64

_lock = threading.Lock()


def _hash(prev_hash: str, body: dict) -> str:
    payload = prev_hash + json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_events() -> List[dict]:
    if not AUDIT_FILE.exists():
        return []
    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def log_event(event_type: str, **fields) -> dict:
    """Append one event. Each event stores the hash of the previous one."""
    with _lock:
        events = read_events()
        prev_hash = events[-1]["hash"] if events else GENESIS
        body = {
            "seq": len(events) + 1,
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "data": {k: redact(str(v)) for k, v in fields.items()},
        }
        entry = {**body, "prev_hash": prev_hash, "hash": _hash(prev_hash, body)}
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


def verify_chain() -> Tuple[bool, Optional[int], int]:
    """Returns (is_valid, first_broken_seq_or_None, total_events)."""
    events = read_events()
    prev_hash = GENESIS
    for i, e in enumerate(events, start=1):
        body = {k: e[k] for k in ("seq", "time", "event", "data")}
        if e.get("prev_hash") != prev_hash or e.get("hash") != _hash(prev_hash, body) or e.get("seq") != i:
            return False, e.get("seq", i), len(events)
        prev_hash = e["hash"]
    return True, None, len(events)
