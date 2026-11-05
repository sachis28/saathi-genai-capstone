# Saathi Radar managed endpoint

Model v1 is custom_model. These files reuse the validated scorer in ml/azureml/score.py; no new predictor, consent filter or threshold is introduced. Workspace/resource/model registration already exist. This deployment is fixed at Standard_D2a_v4, one instance, no autoscale, endpoint saathi-radar-ep, deployment blue. Do not use DSv2 or create training compute.

## Prepare and deploy

From the repository root on sairaj:

```bash
python radar/deploy/prepare.py
az configure --defaults group=Saathi_rg workspace=saathi-radar-ml location=centralus
az ml model show --name saathi-renewal-radar --version 1 --query '{type:type,path:path}' -o json
az ml online-endpoint create -f radar/deploy/endpoint.yml
az ml online-deployment create -f radar/deploy/deployment.yml --all-traffic
az ml online-endpoint invoke -n saathi-radar-ep --request-file radar/deploy/sample-request.json -o json
az ml online-endpoint show -n saathi-radar-ep --query '{scoring_uri:scoring_uri,traffic:traffic,provisioning_state:provisioning_state}' -o json
az ml online-deployment show -n blue -e saathi-radar-ep --query '{instance_type:instance_type,instance_count:instance_count,provisioning_state:provisioning_state}' -o json
```

The generated code/ folder is ignored and contains only allowlisted Python source, never .env, CRM records or weights. Registered model azureml:saathi-renewal-radar:1 supplies weights. The conda file pins the tested model-training runtime plus Azure's inference server. The CLI command can create the serving environment/container registry needed for the deployment. It does not retrain or register a replacement model.

## Runtime URL and secret

```bash
python radar/deploy/save-local-env.py
```

This captures the scoring URI and primary key without printing the key, and writes RADAR_ENDPOINT_URL, RADAR_ENDPOINT_KEY and ML_PROVIDER=azure to ignored repository-root .env with permissions 600. Never commit that file, capture key output in screenshots, or put keys in YAML. In ephemeral Cloud Shell the .env disappears with the session; Shreya must obtain/configure credentials securely in the orchestrator runtime. The API adapter prefers RADAR_ENDPOINT_URL/KEY and supports AZURE_ML_ENDPOINT/KEY as legacy fallbacks. Preserve the existing authentication/customer/product/eligibility gate before calling it.

Human credential retrieval command (do not paste its secret output into chat or git):

```bash
az ml online-endpoint get-credentials -n saathi-radar-ep -g Saathi_rg -w saathi-radar-ml
```

## Request contract

Content-Type: application/json. Nonempty data array, one unique customer_id per row. Example: sample-request.json uses actual checked-in synthetic C-204, C-450 and C-205 rows as of 2026-10-28. No training occurs on them.

| Field | JSON type | Values |
| --- | --- | --- |
| customer_id | string | Unique within request; echoed unchanged. |
| days_to_renewal | integer | Signed; C-450 stays -5. No clipping or overdue exclusion in scorer. |
| interaction_count_90d | integer | 0 through 10000 inclusive. |
| sentiment_score | number | Finite decimal, -1 through 1 inclusive. |
| annual_premium_inr | number | Positive finite annual INR amount; coerced to float. |
| consent | boolean | true or false; never a scoring/visibility filter or predictor. |

Use only these six fields. Missing/extra feature columns, invalid types/ranges or duplicate IDs are rejected. Do not submit policy metadata, agent grants, age bands or outcome labels. Policy status/renewal eligibility are derived centrally before worklist submission, separately from consent-based sending.

## Response contract

A JSON array sorted by risk_score descending and then customer_id. One row per submitted ID, including C-205 (consent=false). Each row contains:

| Field | JSON type | Values |
| --- | --- | --- |
| customer_id | string | Submitted ID. |
| risk_score | number | Finite 0 through 1; synthetic nonrenewal probability. |
| main_risk_factor | string | One of days_to_renewal, interaction_count_90d, sentiment_score, annual_premium_inr. |
| explanation_type | string | largest standardized logistic feature contribution; not causal |
| synthetic | boolean | true |

There is no high/low label or threshold. Scores are from synthetic training and do not establish real-customer accuracy or eligibility. Local sample predictions are not evidence of a live deployment; only the actual invoke receipt establishes that.

## Stop credit usage after testing and demo

A deployed instance consumes credits even while idle. After the demo/testing is complete:

```bash
az ml online-deployment delete -n blue -e saathi-radar-ep -g Saathi_rg -w saathi-radar-ml --yes
```

This deletes the serving deployment; the registered model/workspace remain. Verify deletion and absence of serving deployments. Keep PR #10 draft and do not merge main.
