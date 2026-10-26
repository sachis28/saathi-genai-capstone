# Saathi GenAI capstone

Insurance Agent Copilot. The upstream repository supplies a FastAPI skeleton and .NET client. This branch adds Sairaj's ML workstream: data validation, intent classifiers, a mini Transformer, Renewal Radar, fairness analysis, evaluation evidence and cloud experiment runners.

Start with [Sairaj's delivery status](docs/evaluation_report.md) and [measured experiments](docs/experiment_report.md). All generated customer and intent data is synthetic. The existing chat answer/citations are still placeholders; this branch does not implement Shreya's full RAG, authorization or messaging flow.

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

Run from the repository root so `ml` and `data` are importable. `/chat` now uses trained DistilBERT by default for its intent field; its answer and citations remain upstream dummy values. Set `INTENT_PROVIDER=tfidf_lr` to use the lightweight baseline instead. Inference loads local weights only and never downloads a model automatically. A missing trained model returns 503. `GET /worklist?limit=10` scores the synthetic Radar fixtures, filters rows without consent, and returns descending risk scores with the largest standardized logistic feature contribution. The customer IDs in those fixtures are synthetic ML demo IDs, not yet linked to the CRM placeholder.

Set `ML_PROVIDER=azure` plus AZURE_ML_ENDPOINT and AZURE_ML_KEY to use the managed endpoint through the same worklist service. Consent filtering happens before cloud inference; outcome labels and demographic metadata are removed. The adapter validates returned customer IDs, duplicates, row counts, finite scores, and HTTPS. These controls do not replace the team's customer authorization or messaging policy engine.

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
