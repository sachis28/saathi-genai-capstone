# Saathi GenAI capstone

Insurance Agent Copilot. The upstream repository supplies a FastAPI skeleton and .NET client. This branch adds Sairaj's ML workstream: data validation, intent classifiers, a mini Transformer, Renewal Radar, fairness analysis, evaluation evidence and cloud experiment runners.

Start with [Sairaj's delivery status](docs/evaluation_report.md) and [measured experiments](docs/experiment_report.md). All generated customer and intent data is synthetic. This branch integrates main's cited-answer, conversation-memory, injection-check, draft-approval and audit flows with Sairaj's intent classifier. Customer/product authorization and final acceptance remain pending.

## Local setup

Use Python 3.12. From the repository folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ml.run_local --include-hf
```

The full run downloads two public Hugging Face models and trains DistilBERT on CPU; allow time and disk space. Omit `--include-hf` for the smaller offline path after dependencies are installed, and set `INTENT_PROVIDER=tfidf_lr` to serve that lightweight model. The smaller path does not download models or call cloud services. Generated CSV fixtures are already checked in; the runner validates their hashes and never regenerates a locked dataset automatically. `requirements-lock.txt` records the measured Windows/Python 3.12 environment; use `requirements.txt` for portable installation.

In this prepared checkout, the installed interpreter is `..\.venv\Scripts\python.exe`, and the trained models are already in the local ignored `artifacts/` folder. The documented `.venv` setup above is for a fresh clone.

```powershell
# Run independent stages if needed:
python -m data.validate
python -m ml.train_intent
python -m ml.mini_transformer
python -m ml.hf_models zero-shot
python -m ml.hf_models distilbert --epochs 3
python -m ml.radar
python -m ml.fairness
python -m ml.evaluate_50
python -m ml.prompt_experiment
python -m ml.reports
python -m pytest -q
```

Run these with the installed virtual environment interpreter or activate that environment first. `data.generate_ml --force` intentionally changes/recreates the dataset and must not be used to improve test results. Independent future model iterations should use a new versioned holdout.

## API integration

```powershell
python -m uvicorn app.main:app --app-dir api
```

Run from the repository root so `ml` and `data` are importable. `/chat` now uses trained DistilBERT by default for its intent field; its answer and citations now come from main's retrieval and grounded-answer pipeline. Set `INTENT_PROVIDER=tfidf_lr` to use the lightweight baseline instead. Inference loads local weights only and never downloads a model automatically. A missing trained model returns 503. `GET /worklist?limit=10` requires Bearer authentication and scores only CRM-linked rows that pass ownership, approved product access and centrally calculated renewal eligibility checks. See docs/worklist_access.md for configuration; the API does not fall back to training fixtures.

Set `ML_PROVIDER=azure` plus AZURE_ML_ENDPOINT and AZURE_ML_KEY to use the managed endpoint through the same worklist service. Consent does not filter scoring/worklist visibility; it is checked before outbound send. outcome labels and demographic metadata are removed. The adapter validates returned customer IDs, duplicates, row counts, finite scores, and HTTPS. These controls do not replace the team's customer authorization or messaging policy engine.

Proposed intent labels: `compare_products`, `coverage_question`, `renewal_draft`, `customer_lookup`, `out_of_scope`. The old API used a dummy `policy_question` string. Agree on the final mapping with Shreya before orchestrator integration. TF-IDF confidence is uncalibrated; no low-confidence abstention or production release approval is claimed.

## Evidence and handoff

- [Experiment report](docs/experiment_report.md): macro F1, model selection and confusion matrices.
- [Fairness report](docs/fairness_report.md): subgroup sizes, bootstrap intervals and limitations.
- [Prompt experiment](docs/prompt_experiment.md): V1/V2/V3, 25 fixed cases, both providers and honest pending status.
- [Azure setup](docs/azure_setup.md): Azure training/register/deploy and a real endpoint test.
- [Team acceptance](docs/team_acceptance.md): remaining shared evaluation and rehearsal gates.
- [Integration notes](docs/ml_integration.md): contracts for Sachi, Shreya, Rohan and Soham.
- `docs/evidence/`: small measured artifacts saved for review. Full model weights stay in ignored `artifacts/` and can be regenerated.

The 50-query intent smoke set is not the required end-to-end RAG evaluation. No cloud deployment, live cross-model adherence result, screenshot, team acceptance signature or rehearsal has been fabricated.

## Sources used for implementation

[Pandera dataframe schemas](https://pandera.readthedocs.io/en/latest/dataframe_schemas.html), [Hugging Face sequence classification](https://huggingface.co/docs/transformers/tasks/sequence_classification), [Azure managed endpoints](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-online-endpoints?view=azureml-api-2&tabs=python), [Ollama chat API](https://docs.ollama.com/api/chat).


## Integrated chat and Radar

Chat resolves conversation context, runs the trained intent classifier after the injection check, and preserves retrieved citations, conversation history and audit events. The predicted intent is recorded in both the response and audit log. Missing trained intent artifacts return HTTP 503. The worklist remains a synthetic ML demonstration, now gated by explicit CRM eligibility and authenticated customer/product access. Central metadata now follows the agreed grace-period rules. Approved product grants and deployed identity integration remain pending.

Install both ML and API dependencies from the repository root:

```bash
python -m pip install -r requirements.txt -r api/requirements.txt
PYTHONPATH=.:api python -m pytest api/tests/test_chat_ml_integration.py -q
```

The endpoint integration tests mock classifier and retrieval dependencies; they do not measure DistilBERT accuracy or live retrieval quality.

## CRM data and summary walkthrough

An insurance-agent assistant project.

## Current status

This README documents the synthetic data, initial Renewal Radar features
and standalone customer-summary tests implemented on feat/sachi-data.

Local integration is documented in docs/sachi_followup_handover.md; cloud verification remains pending credentials.
This is not a production-ready release.

## Requirements

The local checks were run using Python 3.14.2.

For the components documented below, install:

```bash
python3 -m pip install pydantic fastapi httpx pytest
```

These are minimal dependencies for this walkthrough, not the complete
application dependency set. The broader API dependencies are listed in
api/requirements.txt.

## 1. Generate synthetic data

Run from the repository root:

```bash
python3 data/generate.py
```

Outputs:

- data/customers.json: six synthetic customers.
- data/interactions.json: 18 synthetic interactions.

The generator uses seed 42 and a fixed reference date of 2026-10-28.
All customer names and interaction messages are synthetic.

Demo customer IDs:

C-204, C-311, C-118, C-450, C-205 and C-999.

### Verify reproducibility

```bash
sha256sum data/customers.json data/interactions.json > /tmp/saathi-data.sha256
python3 data/generate.py
sha256sum -c /tmp/saathi-data.sha256
```

Both files should report OK.

## 2. Generate initial Renewal Radar features

```bash
python3 ml/radar_features.py --as-of 2026-10-28
```

Output: data/radar_features.json, with one row per customer.

Calculated features:

- days_to_renewal
- interaction_count
- days_since_last_interaction

Each row also includes customer_id and as_of_date.

Negative days_to_renewal means the renewal date has passed.
Interactions after the reference date are excluded.
Customers without eligible history have recency null.

These are feature inputs, not predictions or risk scores.
These initial features are distinct from the combined Radar v2 input contract; see docs/radar_contract_v2.md for premium and sentiment details.

## 3. Run standalone summary tests

From the repository root:

```bash
PYTHONPATH=api LLM_PROVIDER=mock python3 -m pytest api/tests/test_summary.py -q
```

The five tests cover:

- Summary response with valid interaction citations.
- Unknown customer returning 404.
- Customer without interaction history.
- Rejection of unknown citation IDs.
- Rejection of responses without citations.

Five tests passed in the local run. A TestClient deprecation warning
was reported without failing the tests.

### Summary endpoint status

The router defines GET /customers/{customer_id}/summary.

Tests mount the router on a separate test application.
The router is registered in the main application; the standalone tests still mount it separately.

The summary now processes the full interaction history in batches of two, checks customer ownership/product access, and validates exact interaction text with customer-specific citations. This is conservative extractive grounding, not a general semantic entailment claim. Live Azure validation remains pending credentials.

## Project files for these components

- data/schemas.py: customer and interaction schemas.
- data/generate.py: reproducible synthetic-data generator.
- data/customers.json: generated customers.
- data/interactions.json: generated interaction history.
- ml/radar_features.py: initial feature builder.
- data/radar_features.json: generated feature rows.
- api/app/routers/summary.py: standalone summary router.
- api/tests/test_summary.py: five summary tests.
- docs/data_dictionary.md: field definitions and feature semantics.
- docs/demo_scenarios.md: synthetic demo scenarios.
- docs/architecture_decisions.md: draft decisions and test-based case studies.

## Integration notes

- The main API loads the generated CRM customer data through load_customers().
- C-999 is a real demo ID (the cancellation case); unknown-customer tests use absent IDs.
- Agree on the final Radar feature contract, training dataset size
  and outcome-label rules before extending the dataset.
- Saved sentiment extraction and aggregation are documented in the Radar handover; representative-data model validation remains pending.
- Full-app startup, cloud configuration and end-to-end evaluation
  instructions must be added after verification.

## Credentials

Never commit API keys, tokens or passwords.
The current .gitignore excludes .env and .venv/.
The mock summary tests do not require cloud credentials.


## Protected CRM Radar worklist

`GET /worklist` now requires a Bearer-authenticated agent and filters CRM-linked features by customer ownership, product access and centrally calculated renewal eligibility before local or Azure scoring. It no longer scores the generated training fixture through the API. Missing credentials return 401; absent CRM-linked input returns 503; missing renewal-date metadata withholds the customer. Derived statuses follow the agreed 30-day-grace rule; the two explicit synthetic fixture changes are documented in docs/data_dictionary.md. See [worklist access contract and setup](docs/worklist_access.md). Other application endpoints still need their own authorization integration.


## Agreed Sachi follow-up integration

Central statuses now use ACTIVE, IN_GRACE, LAPSED and CANCELLED. No-consent customers remain visible in renewal risk/worklists; approval plus send-time consent still gate simulated sending. See [the current handover](docs/sachi_followup_handover.md) and [data dictionary](docs/data_dictionary.md). The following commands reproduce the existing completed export pipeline and measured technical Radar evidence without training on the six customers:

```bash
python -m data.validate
python -m ml.radar
PYTHONPATH=.:api python -m ml.verify_sachi --as-of 2026-10-28
SAATHI_AS_OF_DATE=2026-10-28 PYTHONPATH=.:api python -m pytest api/tests/test_sachi_followup.py api/tests/test_worklist_access.py api/tests/test_chat_ml_integration.py api/tests/test_summary.py api/tests/test_Audit.py tests/test_radar_contract_v2.py tests/test_data_radar.py tests/test_radar_contract.py -q
```

The real protected deployment still requires Shreya's approved product mapping and credentials. Automated endpoint tests use explicit test-only scoped identities. No live Azure result is claimed.

Current Sairaj integration/deployment checkpoint: [Radar release handover](docs/sairaj_radar_release.md). It records 113 passing offline tests, PR #11 summary precedence with authorization preserved, the exact staged scoring-bundle test, and separate real Azure deployment/smoke commands. Live Azure ML deployment remains pending verified workspace configuration and approved runtime access.
