# Sachi follow-up handover

Work targets Sairaj's branch sairaj and draft PR #10, based on b77776b9af96ec2bf7228dfaba698e94cac65463. Sachi's completed data/sentiment/premium/export files were imported from 180f69a855bd9ba645abbdf441d3ce97d12b1f11. The current commit containing this document is the review checkpoint; subsequent browser uploads use separate commits by folder. No main.py edit, main-branch push or PR merge was performed by this run.

## What changed

Central customer loading now preserves CRM identity, ownership, product, consent, renewal date and annual premium. Central policy_metadata and authorize_customer live in api/app/services/customers.py. Worklist and summary reuse that service. The worklist uses ownership plus approved product scopes and central eligibility before real model inference. Consent no longer removes customers from risk scoring/visibility; the existing send endpoint still requires human approval and current consent.

Summaries use the existing get_llm().complete(system,user) adapter, enforce ownership/product access, process all history in two-record batches, and reject unsupported/uncited output with an interaction-specific exact-text validator. Injection-like input is rejected before calling the LLM. This is conservative extractive summarization, not arbitrary abstractive entailment. The summary router was already registered; registration was verified without modifying main.py.

## Fixture mapping and measured technical scores

Reference date: 2026-10-28. Scores below are from an actual rebuilt compatible local scikit-learn model trained on the separate 1,200-row synthetic fixture, never on these six CRM customers. Original CRM ownership is unchanged. These scores do not by themselves prove approved product access.

| Customer | Owner | Days | Central status | Risk score / exclusion | Consent |
| --- | --- | --- | --- | --- | --- |
| C-204 | A-001 | 15 | ACTIVE | 0.46706545389510457 | true |
| C-311 | A-002 | 7 | ACTIVE | 0.6765719909027277 | true |
| C-118 | A-003 | -31 | LAPSED | Excluded: LAPSED_BEYOND_GRACE | true |
| C-450 | A-001 | -5 | IN_GRACE | 0.7177242351185431 | true |
| C-205 | A-002 | 20 | ACTIVE | 0.4881732656263521 | false |
| C-999 | A-003 | 90 | CANCELLED | Excluded: CANCELLED | true |

Only C-118's synthetic renewal_date changes (2026-12-27 to 2026-09-27) and C-999 receives an explicit cancelled=true flag. Calculated statuses are not written into the generator. Premiums, interaction text/dates, saved sentiment and all locked intent splits are unchanged. The regenerated initial-feature/export files reflect C-118=-31; C-450=-5 remains untouched.

In controlled protected-endpoint tests, A-001 sees only C-204/C-450, A-002 sees only C-311/C-205, and A-003 sees no eligible candidates. Those tests use explicitly test-only identity/product scopes. No actual Shreya-approved access mapping, production grant or credential has been invented or installed.

## Commands and actual results

Run from the repository root with installed requirements and an activated Python environment:

```bash
python -m data.validate
python -m ml.radar
PYTHONPATH=.:api python -m ml.verify_sachi --as-of 2026-10-28 --output artifacts/sachi_integration.json
SAATHI_AS_OF_DATE=2026-10-28 PYTHONPATH=.:api python -m pytest api/tests/test_sachi_followup.py api/tests/test_worklist_access.py api/tests/test_chat_ml_integration.py api/tests/test_summary.py api/tests/test_Audit.py tests/test_radar_contract_v2.py tests/test_data_radar.py tests/test_radar_contract.py -q
```

Actual outcome: 87 passed, one TestClient deprecation warning. Data validation and model rebuild passed. Scoring evidence is docs/evidence/sachi_followup_radar.json; test evidence is docs/evidence/sachi_followup_tests.xml. Model weights remain reproducible ignored artifacts/radar/model.joblib.

The integrated TestClient flow exercised protected real Radar -> full-history mock summary -> mock-classifier/retrieval chat -> draft -> blocked unapproved send -> approval -> SIMULATED_SENT for C-204, and send-time 403 for C-205. Summary tests also exercise unknown customer 404, another agent 403, disallowed product 403, unauthenticated 401, empty history, valid ownership, all three citations, wrong IDs, unsupported claims, uncited text and prompt-injection input/output.

## Mock versus live and remaining dependencies

- Real local model scoring and central ownership/status/eligibility checks ran. Test-only principal scopes were used for protected endpoint integration; approved deployment access is still pending.
- Summary used LLM_PROVIDER=mock. Chat classifier/retrieval were controlled endpoint-test doubles. No production DistilBERT accuracy, live retrieval quality, .NET/browser UI acceptance or shared 50-query RAG evaluation is claimed.
- Azure summary was not run because AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT were absent. The requested real deployment is gpt-4.1-mini. Azure model deployment/live scoring also remains pending access.
- The reported feat/shreya-rohan-corpus branch was absent from the current branch inventory. Inspected feat/shreya-integrate-sachi (043ebb8) and main had the older customer loader, so central helpers are implemented here for Shreya's review. Rohan's corpus was not recreated.
- Shreya must supply the approved product-access mapping and server-side authentication configuration. Ordinary CI must keep mock LLMs; live Azure checks must remain separate.
- main.py was deliberately untouched. Authentication/authorization on chat, drafts, sessions and audit still needs Shreya's integration; current approval/consent send tests do not establish those access controls. This prevents claiming full end-to-end security acceptance.
- No Azure/OpenAI/Language/ML credentials, real tokens, production grants or unredacted service responses were created or committed. Existing test tokens are explicitly synthetic test-only strings. Synthetic fixtures/model outcomes are not production readiness evidence.

## Exact changed files

- .env.example
- README.md
- api/app/models/schemas.py
- api/app/routers/summary.py
- api/app/services/customers.py
- api/app/services/ml_service.py
- api/app/services/summary_grounding.py
- api/app/services/worklist_access.py
- api/tests/test_chat_ml_integration.py
- api/tests/test_sachi_followup.py
- api/tests/test_summary.py
- api/tests/test_worklist_access.py
- data/customer_sentiment.json
- data/customers.json
- data/generate.py
- data/radar_features.json
- data/radar_input.json
- data/schemas.py
- docs/architecture_decisions.md
- docs/data_dictionary.md
- docs/evaluation_report.md
- docs/evidence/sachi_followup_radar.json
- docs/evidence/sachi_followup_runtime.json
- docs/evidence/sachi_followup_tests.xml
- docs/ml_integration.md
- docs/radar_contract_v2.md
- docs/sachi_followup_handover.md
- docs/worklist_access.md
- ml/export_radar.py
- ml/radar.py
- ml/radar_contract.py
- ml/score_crm.py
- ml/sentiment_features.py
- ml/verify_sachi.py
- tests/test_data_radar.py
- tests/test_ml.py
- tests/test_radar_contract_v2.py
