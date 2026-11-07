# Saathi test plan

All automated suites run in CI on every pull request. CI runs with `LLM_PROVIDER=mock` and `RETRIEVER=local`, so results are deterministic and free. Azure runs use the same scripts with Azure env vars set.

| Suite | Where | What it proves | Gate |
|---|---|---|---|
| API contract and data | `api/tests/test_mvp.py`, `test_health.py`, `test_search.py`, `test_corpus.py` | Endpoints, schemas, demo customers, corpus loading | pytest green |
| Classifier and ML | `tests/test_ml.py`, `tests/test_radar_*.py`, `tests/test_data_radar.py` | Intent model, Renewal Radar contract, Pandera data checks | pytest green |
| Safety | `api/tests/test_safety.py`, `test_topic_guard.py` | Grounding shield, poisoned clauses, PII redaction, off-topic redirect | pytest green |
| Red-Team Arena | `tests/redteam/attacks.yaml` + `test_redteam.py` | 68 attacks in 9 categories, plus 12 normal questions that must not be blocked | block rate ≥ 95%, 0 unsafe sends, 0 false positives |
| Conversation and customer context | `test_mvp.py`, `test_customer_context.py`, `test_compare.py` | Follow-up memory, record answers, tier filter, Silver vs Gold table | pytest green |
| Agent / MCP / Semantic Kernel | `api/tests/test_agent.py` | 5 MCP tools with JSON schemas, SK plugin, 3-call limit, customer scoping, approval still required | pytest green |
| Audit | `api/tests/test_Audit.py` | Hash chain and tamper detection | pytest green |
| Identity | `api/tests/test_worklist_access.py` | Bearer-token agent auth on `/worklist` | pytest green |
| Azure adapters | `api/tests/test_azure_retriever.py`, `test_ocr_pipeline.py` | AI Search query shape and filters, OCR skillset and indexer definitions (offline) | pytest green |
| Telemetry | `api/tests/test_metrics.py` | `/metrics` latency, block, citation and not-found rates | pytest green |
| .NET client and UI | `dotnet/Saathi.Tests` | Factory Method, mock client, draft flow | `dotnet test` green |
| RAG evaluation (50 queries) | `rag/evaluate_rag.py` | Recall@5, MRR, citation hit rate, refusals, off-topic redirects, latency | Recall@5 ≥ 0.85, off-topic redirect = 1.0 (CI step) |
| Container | CI `docker` job | API image builds and answers `/health` | job green |
| Live deployment | `scripts/smoke_live.py`, workflow "Live smoke test" | AT-00 to AT-08 against the Azure URL | all checks pass |

## Acceptance tests

| ID | Scenario | Automated by |
|---|---|---|
| AT-01 | Load customer C-204 | `test_mvp.py`, `smoke_live.py` |
| AT-02 | Policy question returns an answer with source and clause citations; follow-up "and what about Platinum?" keeps context | `test_mvp.py`, `smoke_live.py` |
| AT-03 | "Compare Silver and Gold" returns a table where every cell is cited | `test_compare.py`, `smoke_live.py` |
| AT-04 | Prompt injection is blocked | `test_safety.py`, `test_redteam.py`, `smoke_live.py` |
| AT-05 | Draft → Send blocked → Approve → SIMULATED_SENT | `test_mvp.py`, `smoke_live.py` |
| AT-06 | No-consent customer (C-205) cannot be sent a message | `test_mvp.py`, `smoke_live.py` |
| AT-07 | Audit chain verifies; a tampered row is detected | `test_Audit.py`, `smoke_live.py` |
| AT-08 | `/metrics` reports block and citation rates | `test_metrics.py`, `smoke_live.py` |

Sign-off is recorded in `docs/acceptance_sheet.md`.
