# Saathi GenAI Capstone

An insurance-agent assistant project.

## Current status

This README documents the synthetic data, initial Renewal Radar features
and standalone customer-summary tests implemented on feat/sachi-data.

Full-application integration and cloud setup instructions remain pending.
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
Premium, claims, sentiment and outcome labels remain pending.

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
The router is not yet registered in the main application.

The existing mock returns the first two matching interaction lines.
It does not perform full-history AI summarization.

Valid citation IDs do not prove factual grounding.
Customer authorization, stronger safety checks and real-provider
evaluation remain pending.

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

- The main API still uses its existing dummy customer lookup.
- Generated files are not automatically connected to that lookup.
- The existing missing-customer test uses C-999.
  When the generated dataset is integrated, use a genuinely absent ID
  for that test.
- Agree on the final Radar feature contract, training dataset size
  and outcome-label rules before extending the dataset.
- Azure AI Language sentiment integration remains pending.
- Full-app startup, cloud configuration and end-to-end evaluation
  instructions must be added after verification.

## Credentials

Never commit API keys, tokens or passwords.
The current .gitignore excludes .env and .venv/.
The mock summary tests do not require cloud credentials.
