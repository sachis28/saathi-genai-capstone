# Fairness evaluation

Scope: synthetic English intent fixtures with artificial demographic metadata. These results cannot establish fairness for real customers or multilingual inputs.

Protected attributes are excluded from predictive features. Metadata-only demographic changes cannot influence a text-only model; that is an architectural property, not proof of unbiased language behavior.

| Model | Attribute | Group | n | Accuracy | Macro F1 | Bootstrap accuracy 95% interval |
|---|---|---|---:|---:|---:|---|
| distilbert | age_band | 18-39 | 50 | 0.780 | 0.770 | 0.660–0.900 |
| distilbert | age_band | 40-59 | 50 | 0.820 | 0.814 | 0.700–0.920 |
| distilbert | age_band | 60+ | 50 | 0.880 | 0.879 | 0.780–0.960 |
| distilbert | gender | man | 45 | 0.800 | 0.792 | 0.689–0.911 |
| distilbert | gender | nonbinary | 45 | 0.867 | 0.863 | 0.756–0.956 |
| distilbert | gender | woman | 60 | 0.817 | 0.812 | 0.717–0.900 |
| distilbert | region | rural | 60 | 0.767 | 0.756 | 0.650–0.867 |
| distilbert | region | urban | 90 | 0.867 | 0.864 | 0.789–0.933 |
| hf_zero_shot | age_band | 18-39 | 50 | 0.400 | 0.280 | 0.260–0.520 |
| hf_zero_shot | age_band | 40-59 | 50 | 0.400 | 0.304 | 0.280–0.540 |
| hf_zero_shot | age_band | 60+ | 50 | 0.420 | 0.318 | 0.280–0.580 |
| hf_zero_shot | gender | man | 45 | 0.400 | 0.280 | 0.267–0.533 |
| hf_zero_shot | gender | nonbinary | 45 | 0.422 | 0.322 | 0.267–0.578 |
| hf_zero_shot | gender | woman | 60 | 0.400 | 0.301 | 0.283–0.533 |
| hf_zero_shot | region | rural | 60 | 0.433 | 0.340 | 0.317–0.567 |
| hf_zero_shot | region | urban | 90 | 0.389 | 0.274 | 0.289–0.489 |
| mini_transformer | age_band | 18-39 | 50 | 0.440 | 0.384 | 0.300–0.580 |
| mini_transformer | age_band | 40-59 | 50 | 0.460 | 0.430 | 0.320–0.600 |
| mini_transformer | age_band | 60+ | 50 | 0.540 | 0.480 | 0.400–0.680 |
| mini_transformer | gender | man | 45 | 0.511 | 0.446 | 0.356–0.644 |
| mini_transformer | gender | nonbinary | 45 | 0.533 | 0.478 | 0.399–0.689 |
| mini_transformer | gender | woman | 60 | 0.417 | 0.383 | 0.300–0.550 |
| mini_transformer | region | rural | 60 | 0.467 | 0.449 | 0.350–0.600 |
| mini_transformer | region | urban | 90 | 0.489 | 0.423 | 0.389–0.589 |
| tfidf_lr | age_band | 18-39 | 50 | 0.340 | 0.300 | 0.220–0.480 |
| tfidf_lr | age_band | 40-59 | 50 | 0.280 | 0.235 | 0.160–0.400 |
| tfidf_lr | age_band | 60+ | 50 | 0.420 | 0.329 | 0.280–0.560 |
| tfidf_lr | gender | man | 45 | 0.400 | 0.352 | 0.244–0.556 |
| tfidf_lr | gender | nonbinary | 45 | 0.378 | 0.302 | 0.244–0.511 |
| tfidf_lr | gender | woman | 60 | 0.283 | 0.240 | 0.167–0.400 |
| tfidf_lr | region | rural | 60 | 0.300 | 0.254 | 0.183–0.433 |
| tfidf_lr | region | urban | 90 | 0.378 | 0.318 | 0.278–0.478 |

Intervals use 1,000 bootstrap resamples (seed 42); they do not correct for multiple comparisons or correlated templates. Small or intersecting groups need more independent examples.

TF-IDF surface probes: 7/7 preserved the baseline intent. This covers one question only.

Before release: collect consented representative English/Marathi/Hindi questions, review labels with domain experts, evaluate subgroup recall and intersectional errors, define acceptable gaps with the team, and repeat on real data. No fairness pass threshold was specified in the execution plan.

Renewal Radar excludes age, gender and region, but proxy bias is still possible. Synthetic outcomes are unsuitable for real eligibility, premium, or customer prioritization decisions.
