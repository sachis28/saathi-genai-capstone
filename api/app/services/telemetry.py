"""Per-request telemetry and the /metrics summary (v2 plan 6.4; Trust Scorecard numbers).

Kept in memory (last 5,000 requests per replica): no PII, only route, status, latency and the
outcome of each chat turn. App Insights can scrape /metrics or replace this later.
"""
import os
import time
from collections import Counter, deque
from typing import Deque, Dict, List

# deque(maxlen=...) keeps only the latest 5,000 rows, so memory stays bounded.
MAX_ROWS = 5000
_requests: Deque[Dict] = deque(maxlen=MAX_ROWS)
_chats: Deque[Dict] = deque(maxlen=MAX_ROWS)
STARTED = time.time()


def record_request(route: str, status: int, latency_ms: float) -> None:
    _requests.append({"route": route, "status": status, "latency_ms": latency_ms})


def record_chat(outcome: str, citations: int, intent: str = "") -> None:
    """outcome: answer | not_found | blocked | off_topic | record | comparison"""
    _chats.append({"outcome": outcome, "citations": citations, "intent": intent})


# Percentile helper, e.g. p=0.95 gives the p95 latency.
def _pct(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return round(values[min(len(values) - 1, int(round(p * (len(values) - 1))))], 1)


# Builds the /metrics response from the rows collected so far.
def summary() -> Dict:
    by_route: Dict[str, List[float]] = {}
    for r in _requests:
        by_route.setdefault(r["route"], []).append(r["latency_ms"])
    outcomes = Counter(c["outcome"] for c in _chats)
    total = len(_chats)
    # Turns that went through retrieval (the ones where a citation is expected).
    rag_answers = outcomes["answer"] + outcomes["not_found"] + outcomes["comparison"]
    cited = sum(1 for c in _chats if c["outcome"] in ("answer", "comparison") and c["citations"] > 0)
    errors = sum(1 for r in _requests if r["status"] >= 500)
    return {
        "since_seconds": round(time.time() - STARTED),
        "provider": {"llm": os.getenv("LLM_PROVIDER", "mock"), "retriever": os.getenv("RETRIEVER", "local")},
        "requests": len(_requests),
        "error_rate": round(errors / len(_requests), 4) if _requests else 0.0,
        "latency_ms": {route: {"count": len(v), "p50": _pct(v, 0.5), "p95": _pct(v, 0.95)}
                       for route, v in sorted(by_route.items())},
        "chat": {
            "turns": total,
            "outcomes": dict(outcomes),
            "block_rate": round(outcomes["blocked"] / total, 4) if total else 0.0,
            "off_topic_rate": round(outcomes["off_topic"] / total, 4) if total else 0.0,
            "citation_rate": round(cited / rag_answers, 4) if rag_answers else 0.0,
            "not_found_rate": round(outcomes["not_found"] / rag_answers, 4) if rag_answers else 0.0,
        },
    }


# Clear everything (used by tests).
def reset() -> None:
    _requests.clear()
    _chats.clear()
