"""50-query end-to-end RAG evaluation for Saathi (the v2 plan's Day 45 evaluation).

It runs whatever the environment selects (RETRIEVER=local|azure, LLM_PROVIDER=mock|azure), so the
same script produces the offline numbers and the Azure numbers:

    python rag/evaluate_rag.py            # writes docs/evidence/rag_eval_<llm>-<retriever>.json + docs/rag_evaluation_report.md
    python rag/evaluate_rag.py --check    # also fails if the targets below are missed (used in CI)

The 50 queries:
- 40 answerable questions from rag/corpus/retrieval_gold_set.jsonl, each with expected clause IDs;
- 5 in-domain questions the documents do NOT answer (the right answer is a refusal);
- 5 off-topic questions (the right answer is the polite redirect).

Metrics:
- Retrieval: Recall@5 and MRR, with the same product/tier filter the gold set names.
- Answers, through POST /chat as the agent would ask:
  - citation hit rate: the answer cites at least one expected clause;
  - answered rate: the answer is not "could not find";
  - unanswerable refusal rate;
  - off-topic redirect rate;
  - p50/p95 latency.
With LLM_PROVIDER=mock, the mock model always quotes the top clauses, so the unanswerable refusal
rate only means something with a real LLM. The report says so instead of hiding it.
"""
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Let this script import the API package (api/app) the same way the server does.
sys.path[:0] = [str(ROOT), str(ROOT / "api")]

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.services.answer import NOT_FOUND  # noqa: E402
from app.services.customers import load_customers  # noqa: E402
from app.services.retriever import get_retriever  # noqa: E402
from app.services.topic_guard import OFF_TOPIC_MSG  # noqa: E402

GOLD = ROOT / "rag" / "corpus" / "retrieval_gold_set.jsonl"
# CI fails (--check) if Recall@5 drops below 0.85 or any off-topic question is not redirected.
TARGETS = {"recall_at_5": 0.85, "off_topic_redirect_rate": 1.0}

# In-domain questions the policy library cannot answer: the right reply is a refusal.
UNANSWERABLE = [
    ("Does Health Platinum include a free gym membership?", "Health", "Platinum"),
    ("Is there a loyalty discount for paying three years of premium upfront?", "Health", "Silver"),
    ("Does Health Gold cover laser eye surgery done abroad?", "Health", "Gold"),
    ("Can the premium for Health Silver be paid in cryptocurrency?", "Health", "Silver"),
    ("Does Motor Gold include a free annual car wash?", "Motor", "Gold"),
]
# Questions that have nothing to do with insurance: the right reply is the polite redirect.
OFF_TOPIC = ["Tell me a joke", "What is the weather in Pune today?", "Write a poem about the sea",
             "Book a flight to Delhi", "Who won the cricket match yesterday?"]


def customer_for(product: str, tier: str) -> str:
    """A customer with that plan, so /chat filters retrieval the way it would for a real agent."""
    if product == "All":
        return "C-204"
    for c in load_customers().values():
        if c.product == product and c.tier == tier:
            return c.customer_id
    return "C-204"


# Ask one question through the real /chat endpoint (in-process test client) and time it.
def ask(client: TestClient, question: str, customer_id: str):
    start = time.perf_counter()
    body = client.post("/chat", json={"customer_id": customer_id, "question": question}).json()
    return body, (time.perf_counter() - start) * 1000


def run() -> dict:
    client = TestClient(main.app)
    retriever = get_retriever()
    gold = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, latencies = [], []

    recalls, rrs, cite_hits, answered = [], [], [], []
    # Part 1: 40 answerable questions. Measure retrieval alone, then the full /chat answer.
    for g in gold:
        product = None if g["product"] == "All" else g["product"]
        tier = None if g["tier"] == "All" else g["tier"]
        expected = set(g["expected_clause_ids"])
        retrieved = [h.clause_id for h in retriever.search(g["query"], k=5, product=product, tier=tier)]
        # Recall@5: share of expected clauses found in the top 5. rr: 1 / rank of the first correct one.
        recall = len(expected & set(retrieved)) / len(expected)
        rr = next((1 / (i + 1) for i, c in enumerate(retrieved) if c in expected), 0.0)
        body, ms = ask(client, g["query"], customer_for(g["product"], g["tier"]))
        cited = [c["clause_id"] for c in body["citations"]]
        # Citation hit: did the final answer cite at least one of the expected clauses?
        hit = bool(expected & set(cited))
        recalls.append(recall); rrs.append(rr); cite_hits.append(hit); latencies.append(ms)
        answered.append(body["answer"] != NOT_FOUND)
        rows.append({"type": "answerable", "query": g["query"], "expected": sorted(expected), "retrieved": retrieved,
                     "recall_at_5": recall, "rr": round(rr, 3), "cited": cited, "citation_hit": hit,
                     "answer": body["answer"][:300]})

    # Part 2: unanswerable questions should be refused, not answered with a guess.
    refusals = []
    for q, product, tier in UNANSWERABLE:
        body, ms = ask(client, q, customer_for(product, tier))
        ok = body["answer"] in (NOT_FOUND, OFF_TOPIC_MSG)
        refusals.append(ok); latencies.append(ms)
        rows.append({"type": "unanswerable", "query": q, "refused": ok, "answer": body["answer"][:300]})

    # Part 3: off-topic questions should get the redirect (or the injection block).
    redirects = []
    for q in OFF_TOPIC:
        body, ms = ask(client, q, "C-204")
        ok = body["answer"] in (OFF_TOPIC_MSG, main.BLOCKED_MSG)
        redirects.append(ok); latencies.append(ms)
        rows.append({"type": "off_topic", "query": q, "redirected": ok, "answer": body["answer"][:200]})

    mode = f"{os.getenv('LLM_PROVIDER', 'mock')}-{os.getenv('RETRIEVER', 'local')}"
    lat = sorted(latencies)
    metrics = {
        "mode": mode, "queries": len(rows),
        "recall_at_5": round(statistics.mean(recalls), 4), "mrr": round(statistics.mean(rrs), 4),
        "citation_hit_rate": round(sum(cite_hits) / len(cite_hits), 4),
        "answered_rate": round(sum(answered) / len(answered), 4),
        "unanswerable_refusal_rate": round(sum(refusals) / len(refusals), 4),
        "off_topic_redirect_rate": round(sum(redirects) / len(redirects), 4),
        "latency_ms_p50": round(lat[len(lat) // 2], 1), "latency_ms_p95": round(lat[int(len(lat) * 0.95) - 1], 1),
    }
    return {"metrics": metrics, "rows": rows}


# Save the raw per-query results as evidence, and update the Markdown report section for this mode.
def write(result: dict) -> None:
    m = result["metrics"]
    evidence = ROOT / "docs" / "evidence" / f"rag_eval_{m['mode']}.json"
    evidence.write_text(json.dumps(result, indent=1), encoding="utf-8")

    mock = m["mode"].startswith("mock")
    lines = [
        f"## Run: {m['mode']}  ({time.strftime('%Y-%m-%d %H:%M')})", "",
        "| Metric | Value | Target |", "|---|---:|---|",
        f"| Recall@5 (40 answerable) | {m['recall_at_5']:.2f} | ≥ 0.85 |",
        f"| MRR | {m['mrr']:.2f} | – |",
        f"| Citation hit rate (answer cites an expected clause) | {m['citation_hit_rate']:.2f} | ≥ 0.80 |",
        f"| Answered rate (not 'could not find') | {m['answered_rate']:.2f} | – |",
        f"| Unanswerable refusal rate (5) | {m['unanswerable_refusal_rate']:.2f} | 1.00{' (needs a real LLM; the mock always quotes the top clauses)' if mock else ''} |",
        f"| Off-topic redirect rate (5) | {m['off_topic_redirect_rate']:.2f} | 1.00 |",
        f"| Latency p50 / p95 (ms) | {m['latency_ms_p50']} / {m['latency_ms_p95']} | – |", "",
        "Misses:", "",
    ]
    misses = [r for r in result["rows"] if (r["type"] == "answerable" and (r["recall_at_5"] < 1 or not r["citation_hit"]))
              or (r["type"] == "unanswerable" and not r["refused"]) or (r["type"] == "off_topic" and not r["redirected"])]
    lines += [f"- [{r['type']}] {r['query']}" + (f" (expected {', '.join(r['expected'])}; retrieved {', '.join(r['retrieved'])}; cited {', '.join(r['cited']) or 'none'})" if r["type"] == "answerable" else "")
              for r in misses] or ["- none"]
    lines += ["", f"Full per-query results: `docs/evidence/{evidence.name}`", ""]

    report = ROOT / "docs" / "rag_evaluation_report.md"
    header = ("# RAG evaluation report (50 queries)\n\n"
              "Produced by `python rag/evaluate_rag.py`. Each run replaces the section for its mode "
              "(LLM provider and retriever). Numbers are measured, not edited; misses are listed.\n\n")
    sections = {}
    if report.exists():
        for part in report.read_text(encoding="utf-8").split("## Run: ")[1:]:
            sections[part.split()[0]] = "## Run: " + part.rstrip() + "\n\n"
    sections[m["mode"]] = "\n".join(lines) + "\n"
    report.write_text(header + "".join(sections[k] for k in sorted(sections)), encoding="utf-8")
    print(json.dumps(m, indent=1))
    print(f"Wrote {report.relative_to(ROOT)} and {evidence.relative_to(ROOT)}")


if __name__ == "__main__":
    result = run()
    write(result)
    if "--check" in sys.argv:
        missed = {k: (result["metrics"][k], v) for k, v in TARGETS.items() if result["metrics"][k] < v}
        if missed:
            sys.exit(f"Missed evaluation targets: {missed}")
