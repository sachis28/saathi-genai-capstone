# Team acceptance and rehearsal worksheet

Owner for ML evidence: Sairaj. Overall acceptance is shared with the team. Nothing in this sheet is signed off yet.

| Gate | Evidence needed | Current state |
|---|---|---|
| Intent data checks | Pandera checks and fixed train/dev/test hashes | Locally measured in docs/evidence/ |
| Intent quality | DistilBERT macro F1 ≥ 0.75, confusion matrix, independent error review | See experiment_report.md; synthetic data only |
| Fairness | Subgroup metrics, errors, limitations | Synthetic audit; representative data needed |
| Renewal Radar | Top 10 with feature contribution explanations | Local synthetic demo available |
| Azure ML | Training job, registered model, online endpoint URL and real invocation | Pending Azure workspace and account |
| Prompt adherence | 150 real responses and human grading | Pending Azure GPT and Ollama services |
| 50-query RAG evaluation | Rohan's gold queries, Recall@5/MRR, citations and grounding results | Pending retrieval implementation; intent smoke set is not a substitute |
| End-to-end acceptance | C-204 question → cited answer → draft → approval → simulated_sent | Pending team implementation; current chat answer is a placeholder |
| Offline fallback | Local app and models run with network disconnected | Local models are available; full app demonstration pending |
| Rehearsal 1 | Date, participants, observed failures and fixes | Not performed |
| Rehearsal 2 | Date, participants, final timed demo and acceptance owner | Not performed |

Suggested ML presentation sequence: show the locked split manifest; compare actual F1 and confusion matrices; explain attention and padding in the executed notebook; explain fairness limits; show the local Radar top 10; show the Azure endpoint only after a real deployment and smoke test; show the model-by-prompt table only after live runs.

Acceptance owner: __________  Date: __________  Decision: __________
