# Cross-model prompt experiment

Design: the same 25 synthetic cases × V1/V2/V3 × Azure GPT and Ollama = 150 responses. Temperature 0; Ollama seed 42. Cloud determinism is not guaranteed.

Automated pass means expected decision, JSON shape, permitted/required citation IDs, pending approval and sent=false. It does not prove factual grounding or semantic safety. Human review must check unsupported claims, refusal quality, invented data, and draft wording.

| Provider | Prompt | Cases | Contract pass rate | Status |
|---|---|---:|---:|---|
| azure | V1 | 25 | — | Not run: service configuration required |
| azure | V2 | 25 | — | Not run: service configuration required |
| azure | V3 | 25 | — | Not run: service configuration required |
| ollama | V1 | 25 | — | Not run: service configuration required |
| ollama | V2 | 25 | — | Not run: service configuration required |
| ollama | V3 | 25 | — | Not run: service configuration required |

No mock outputs count as cross-model evidence. A local HF intent model is not a substitute for Azure GPT versus Ollama instruction adherence.

Human review worksheet

| Run / case | Supported claims only | Refusal appropriate | No invented customer data | Draft safe | Reviewer |
|---|---|---|---|---|---|
| Pending live runs | | | | | |
