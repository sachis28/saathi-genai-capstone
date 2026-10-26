# ML integration handoff

Sairaj owns this package. It is compatible with the current repository skeleton, but the rest of the product is still under development. Do not treat a successful intent classification as customer authorization.

## Sachi

The supplied fixtures are temporary synthetic ML-owned data, not a replacement for your CRM generator. `data/validate.py` defines Pandera schemas for these fixtures. Bring your approved schemas and generated fixtures into the validation step once available; actual CRM relationship, consent-history and product-version checks remain pending that contract.

Radar input rows require `customer_id` (unique string), `days_to_renewal` (integer 0–365), `interaction_count_90d` (integer 0–10000), `sentiment_score` (float −1 to 1), `premium` (positive float) and `consent` (boolean). In training, `nonrenewed` is a historical binary outcome and `age_band` is audit-only metadata. Inference strips both before cloud submission. Map Azure AI Language's sentiment output to a documented numeric scale before using it; random synthetic sentiment is only a fixture. Training features must be available at prediction time: never include future interactions or renewal outcomes.

The current renewal label is a noisy synthetic function. Real Radar evaluation needs customer/time-separated historical outcomes, calibration, useful ranking metrics and representative fairness checks. The present holdout is a reproducible stratified synthetic row split, not proof of real-world usefulness.

## Shreya

`api/app/services/ml_service.py` exposes `classify_intent(text)` and async `renewal_worklist(frame=None)`. The API calls the former off the event loop. Worklist uses ML_PROVIDER=local|azure and validates Azure responses. The local path performs small batch Pandas/scikit-learn work directly; move larger batches to a background worker before scaling.

The five intent labels are provisional and are listed in README.md. The old API's `policy_question` was a dummy value; agree on whether to map it to `coverage_question`. Model confidence is not calibrated. Choose a threshold and ambiguity behavior on new representative development data before a production route is enabled. The API defaults to locally trained DistilBERT; INTENT_PROVIDER=tfidf_lr selects the lightweight baseline, with its measured quality limitation disclosed. Inference never downloads remote weights.

Authorization must filter the candidate frame before calling Radar. Current `/worklist` is explicitly synthetic, uses generated IDs outside the placeholder CRM, and has no product authorization layer. Consent merely filters demo ranking rows and never permits a send. `/chat` continues to return the upstream placeholder answer and citations; RAG, policy and customer checks remain yours.

## Rohan and Soham

`tests/fixtures/intent_acceptance_50.json` checks intent routing only. It has no retrieval gold answers and is not the Day 45 full-product evaluation. Bring Rohan's 50 retrieval queries/gold clauses into the shared evaluation, then measure Recall@5/MRR, citation correctness, groundedness, authorization, draft approval and simulated-send behavior against the actual application.

`tests/test_ml.py` covers data leakage, invalid schema inputs, training-only vocabulary, Transformer padding, Radar consent and target exclusion, Azure scoring parity and response validation, prompt grading, and local API integration. HTTP fakes are labeled integration tests, not cloud evidence. The acceptance sheet and rehearsals remain pending the complete application and team participants.
