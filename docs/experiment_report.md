# Intent classification experiment

Owner: Sairaj. Seed: 42. All inputs are synthetic ML fixtures, not Sachi's approved CRM data. Labels are a proposed integration contract pending team review.

Dataset: 1,000 training rows, 200 development rows and 150 locked test rows. Template families are assigned before expansion. There is no normalized text or family overlap; entities and insurance vocabulary recur. CSV SHA-256 hashes are stored in data/generated/manifest.json. Test labels are versioned for audit; the hash lock detects edits but is not access control.

Model selection uses development macro F1 only. Test results are reported after selecting the checkpoint. No test-driven retuning is performed in this version. The five proposed labels are: compare_products, coverage_question, renewal_draft, customer_lookup, out_of_scope.

| Model | Test macro F1 | Best/selected dev macro F1 | Target | Result |
|---|---:|---:|---|---|
| tfidf_lr | 0.2912 | 0.6447 | Record baseline | Measured |
| mini_transformer | 0.4370 | 0.6970 | Record baseline | Measured |
| hf_zero_shot | 0.3019 | N/A | Record baseline | Measured |
| distilbert | 0.8219 | 1.0000 | ≥ 0.75 | Met on synthetic holdout |

## tfidf_lr

Confusion matrix: rows are true labels, columns are predicted labels.

| True / predicted | compare_products | coverage_question | renewal_draft | customer_lookup | out_of_scope |
|---|---:|---:|---:|---:|---:|
| compare_products | 1 | 12 | 0 | 17 | 0 |
| coverage_question | 15 | 15 | 0 | 0 | 0 |
| renewal_draft | 0 | 0 | 18 | 12 | 0 |
| customer_lookup | 0 | 9 | 0 | 18 | 3 |
| out_of_scope | 0 | 0 | 16 | 14 | 0 |

Run metadata

```json
{
  "selected_C": 0.5,
  "dev_macro_f1": 0.6447171610241617
}
```

## mini_transformer

Confusion matrix: rows are true labels, columns are predicted labels.

| True / predicted | compare_products | coverage_question | renewal_draft | customer_lookup | out_of_scope |
|---|---:|---:|---:|---:|---:|
| compare_products | 6 | 24 | 0 | 0 | 0 |
| coverage_question | 0 | 15 | 0 | 0 | 15 |
| renewal_draft | 0 | 0 | 4 | 12 | 14 |
| customer_lookup | 0 | 13 | 0 | 17 | 0 |
| out_of_scope | 0 | 0 | 0 | 0 | 30 |

Run metadata

```json
{
  "epochs": 30,
  "selection": "best dev macro F1",
  "best_dev_macro_f1": 0.697041049717106,
  "parameters": 38917
}
```

## hf_zero_shot

Confusion matrix: rows are true labels, columns are predicted labels.

| True / predicted | compare_products | coverage_question | renewal_draft | customer_lookup | out_of_scope |
|---|---:|---:|---:|---:|---:|
| compare_products | 0 | 0 | 0 | 30 | 0 |
| coverage_question | 0 | 29 | 1 | 0 | 0 |
| renewal_draft | 0 | 0 | 2 | 28 | 0 |
| customer_lookup | 0 | 0 | 0 | 30 | 0 |
| out_of_scope | 0 | 0 | 0 | 30 | 0 |

Run metadata

```json
{
  "model_id": "typeform/distilbert-base-uncased-mnli",
  "revision": "cfa538a0fddbbd978fefe8966c1aeff7ad409c90",
  "label_descriptions": {
    "compare_products": "compare insurance products",
    "coverage_question": "ask about insurance coverage or exclusions",
    "renewal_draft": "draft an insurance renewal reminder",
    "customer_lookup": "look up customer information",
    "out_of_scope": "request help unrelated to insurance"
  },
  "hypothesis_template": "The user wants to {}.",
  "fine_tuned_on_saathi": false
}
```

## distilbert

Confusion matrix: rows are true labels, columns are predicted labels.

| True / predicted | compare_products | coverage_question | renewal_draft | customer_lookup | out_of_scope |
|---|---:|---:|---:|---:|---:|
| compare_products | 30 | 0 | 0 | 0 | 0 |
| coverage_question | 0 | 30 | 0 | 0 | 0 |
| renewal_draft | 0 | 0 | 30 | 0 | 0 |
| customer_lookup | 0 | 12 | 0 | 18 | 0 |
| out_of_scope | 0 | 0 | 0 | 14 | 16 |

Run metadata

```json
{
  "model_id": "distilbert/distilbert-base-uncased",
  "revision": "12040accade4e8a0f71eabdb258fecc2e7e948be",
  "epochs": 3,
  "best_dev_macro_f1": 1.0,
  "selection": "best dev macro F1",
  "training_seconds": 330.98500000001513,
  "target_macro_f1": 0.75
}
```

## Interpretation and limitations

Low baseline and mini-Transformer results on held-out sentence families expose vocabulary memorization. These are measured failures, not reasons to adjust the locked test set. Production rollout requires independent human-authored questions, domain-reviewed labels, ambiguous/multi-intent cases, multilingual evaluation, calibrated confidence, and an abstention strategy.

Intent output is routing assistance only. It does not authorize customer access, prove grounding, or permit sending messages. The API defaults to the locally trained DistilBERT model; INTENT_PROVIDER=tfidf_lr selects the lightweight baseline with its disclosed quality limitation. No production release approval is claimed. The existing /chat answer and citations remain upstream dummy placeholders.

The protected-attribute metadata is artificial and not representative. See fairness_report.md for subgroup results and limits. The 50-question intent smoke evaluation is separate from the team's end-to-end RAG evaluation.
