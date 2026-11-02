# Radar contract alignment

The Radar model now consumes Sachi's annual INR premium and signed renewal-day contract. This is verified synthetic scoring compatibility; policy eligibility and customer/product authorization remain application integration requirements.

## Input and provenance

The six-column payload is customer_id, days_to_renewal, interaction_count_90d, sentiment_score, annual_premium_inr, consent. Annual premium is positive finite annual base INR, excluding taxes and fees; no silent rescaling or aliasing from premium is performed. Negative renewal days are preserved. Missing sentiment is rejected, not replaced with zero. Upstream sentiment is the mean of positive minus negative confidence across the reference day and previous 89 days, excluding future interactions.

The unchanged test export comes from sachis28/saathi-genai-capstone, feat/sachi-data commit 180f69a855bd9ba645abbdf441d3ce97d12b1f11, data/radar_input.json. It is stored as tests/fixtures/sachi_radar_input.json; its reference date is 2026-10-28. This change does not merge or modify Sachi's branch.

## Training and compatibility

Only the separate 1,200-row synthetic Radar fixture was regenerated, with days sampled from -90 through 365 and the existing noisy synthetic nonrenewal rule. All locked intent CSVs and their manifest hashes are unchanged. The six CRM demo customers were not used for training. This fixture tests implementation behavior; its generated outcomes are not an approved business target or evidence of real-world overdue risk quality. Feature coverage beyond the synthetic training ranges is not validated.

Existing serialized models with the old feature list are rejected with an explicit retraining message. Both local and Azure training use the same FEATURES order. Azure scoring imports the same score_rows function. Model weights are reproducible local artifacts under artifacts/radar/model.joblib and are not committed.

## Verification

Seventeen new Radar contract tests passed, including signed overdue days, consent filtering, exact feature naming, invalid/missing sentiment, finite positive premiums, duplicate IDs, rejection of old estimators, unchanged locked intent files, local adapter scoring, a mocked Azure HTTP adapter and parity with the Azure scoring entry point executed locally. These are separate from Sachi's previously reported 17 tests.

The six-row export produced five finite scores in [0,1]. C-450 remained at -5 days and was scored; C-205 was excluded because consent was false. Evidence is in docs/evidence/radar_crm_v2.json and radar_v2_tests.xml. Synthetic training metrics for this version are in radar_v2_metrics.json; earlier radar_metrics.json and radar_top10.json are historical v1 evidence.

The full existing ML suite was not run in this environment because PyTorch and the previous intent model artifacts were absent. No live Azure endpoint was created or invoked. Local Azure entry-point parity is not evidence of a deployed endpoint.

## Reproduce

Install repository requirements, then run from the repository root:

```bash
python -m data.generate_ml --radar-only
python -m data.validate
python -m ml.radar
PYTHONPATH=.:api python -m pytest tests/test_radar_contract_v2.py -q
python -m ml.score_crm --input tests/fixtures/sachi_radar_input.json --as-of 2026-10-28 --output artifacts/radar_crm_v2.json
```

The as-of value records the export's reference date; the six-column payload cannot independently prove that date. Verify upstream provenance when replacing the input.

## Remaining integration

Shreya and Sachi must supply policy eligibility/status and customer/product authorization before these scores become an application worklist. Consent alone is not authorization and never permits a send. No eligibility values have been invented for the demo customers. Confirm the actual renewal target, acquire representative customer/time-separated data, and evaluate before using the model beyond a synthetic demo. Deploy and test the compatible artifact on Azure when workspace access is configured.
