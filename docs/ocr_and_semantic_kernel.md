# OCR ingestion and the Semantic Kernel agent

## OCR: scanned endorsements become searchable clauses

**What OCR is.** Optical Character Recognition reads the printed words out of an image, such as a scan, a photo or an image-only PDF. Without it, a scanned endorsement is just pixels, and search can't find anything in it.

**Pipeline** (`rag/azure/ocr_pipeline.py`):

```
rag/corpus/scanned/*.png  ->  Blob container saathi-scans (metadata: source_id, clause_id, product, tier, version)
   ->  AI Search data source  saathi-ocr-blob
   ->  skillset saathi-ocr-skillset:  OCR skill -> Merge skill -> Azure OpenAI embedding skill
   ->  indexer saathi-ocr-indexer  ->  the MAIN index (AZURE_SEARCH_INDEX_NAME)
```

The scanned clauses land in the same index the app already searches, with the same citation fields, so the grounding shield treats them like any typed clause.

**The two sample scans exist only as images.** Nothing in the typed corpus covers either topic, so a cited answer proves the text came through OCR.

| Scan | Ask Saathi (customer with that plan) | Expected citation |
|---|---|---|
| `endorsement_health_gold_air_ambulance.png` | Is air ambulance covered for Health Gold? (customer C-311 or C-450) | `SCAN-HEALTH-GOLD-END-17#CL-AIR-01` |
| `endorsement_motor_gold_key_replacement.png` | Is car key replacement covered for Motor Gold? (any Motor Gold customer) | `SCAN-MOTOR-GOLD-END-22#CL-KEY-01` |

**Run it** (from a Codespace with `.env` filled in; no Azure CLI needed):

```
python rag/azure/ocr_pipeline.py all
```

This uploads the scans, creates or updates the data source, skillset and indexer, runs the indexer, then prints the OCR text found in the index. Evidence for the demo: the portal pages for **AI Search → Indexers → saathi-ocr-indexer** (run history) and **Skillsets → saathi-ocr-skillset**, plus Search explorer with `search=air ambulance`.

The free tier covers 20 OCR images per indexer per day. Beyond that, set `AZURE_AI_SERVICES_KEY` to a multi-service Azure AI services key.

## Semantic Kernel orchestrator

`api/app/agent/agent.py` runs the agent on **Semantic Kernel**:

- The five MCP tools are registered as the SK plugin `saathi` (`SaathiPlugin`), one `@kernel_function` per tool. SK generates each tool's JSON schema from the function signature.
- With `LLM_PROVIDER=azure`, SK's `OpenAIChatCompletion` service calls the Foundry deployment with `FunctionChoiceBehavior.Auto`, and SK runs the tool-calling loop.
- With `LLM_PROVIDER=mock`, a fixed plan runs through `kernel.invoke()`, so offline runs and tests use the same plugin and the same rules.
- **Rules stay in code:**
  - An SK auto-function-invocation filter stops the loop after 3 tool calls or on any tool not in the allowlist.
  - The plugin forces every `customer_id` to the selected customer.
  - The final answer still goes through `generate_answer`, which applies the grounding shield and citations.
- `POST /agent/chat` returns `"orchestrator": "semantic-kernel"` and a per-tool trace, which is the trace to show in demo act 8.
