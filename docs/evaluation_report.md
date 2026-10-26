# Sairaj evaluation and delivery status

Local ML work is implemented. Azure and full-product acceptance are incomplete. No deployed URL, cloud screenshot, team sign-off, or rehearsal is claimed.

| Assignment | Evidence | Status |
|---|---|---|
| Pandera data quality | evidence/data_validation.json; data/validate.py | Local ML fixtures validated; CRM schemas await team |
| 1,000 train / 150 locked test | data/generated/manifest.json | Complete; 200 extra dev rows |
| TF-IDF + Logistic Regression | evidence/tfidf_lr_metrics.json | Measured |
| Mini Transformer | ml/notebooks/mini_transformer.ipynb | Implemented and locally trained |
| HF zero-shot baseline | evidence/hf_zero_shot_metrics.json | Measured |
| DistilBERT Macro F1 ≥ 0.75 | evidence/distilbert_metrics.json | PASS on synthetic holdout |
| Fairness report | fairness_report.md | Synthetic subgroup audit; no fairness certification |
| Renewal Radar | evidence/radar_metrics.json; evidence/radar_top10.json | Locally trained and scored |
| Azure ML training/register/deploy | ml/azureml/ | Scripts ready; no Azure account/workspace configured |
| Azure /worklist provider | api/app/services/ml_service.py | Local scoring tested; cloud path tested with mocked HTTP only |
| V1/V2/V3 × 25 cases × 2 models | prompt_experiment.md | Design and runner ready; live Azure/Ollama runs pending |
| 50-query evaluation | evidence/intent_acceptance_50_metrics.json | Intent-only local smoke check; not full RAG acceptance |
| Full-product acceptance, 2 rehearsals, offline demo | team_acceptance.md | Pending team application and participants |
| Local Python test suite | evidence/test_results.xml | 11 passed, 0 failed, 0 skipped |
| Real HTTP local API check | evidence/local_api_smoke.json | Passed: DistilBERT intent and 10 local Radar entries |
| Existing .NET client tests | dotnet/Saathi.slnx | Attempted; no .NET SDK installed, so tests could not run |

Reports are generated from actual JSON metrics. Model weights are local under artifacts/ and ignored by Git; recreate them with the documented commands. Small evidence files are included in docs/evidence/ for review.

Remaining dependencies: Sachi's approved data/features; Shreya's orchestration, authorization, and policy contracts; Azure subscription/workspace and deployed GPT model; installed Ollama model; Rohan's retrieval gold set; Soham's acceptance workflow.
