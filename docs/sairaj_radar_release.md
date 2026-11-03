# Sairaj Radar and integration checkpoint

PR #10 remains a draft on sairaj. No main push/merge or main.py edit. This checkpoint starts from 238899d and incorporates the tested summary contract from PR #11 at fbb7b3b.

## Task status

| Task | Current evidence |
| --- | --- |
| Consent does not filter Radar scoring/worklist visibility | Already implemented before this checkpoint; tests retain C-205 with consent=false. Only outbound send checks approval and current consent. |
| Signed renewal days | C-450 stays -5 and eligible IN_GRACE. Central eligibility supports ACTIVE/IN_GRACE; lapse beyond 30 days and explicit cancellation are excluded before API inference. |
| Policy metadata | Derived centrally by policy_metadata in customers.py from renewal_date and explicit cancelled. Sachi should not hand-fill calculated statuses in the generator or feed them to the predictive features. Customer API metadata retains policy_status, renewal_eligible and eligibility_reason. |
| Summary overlap | PR #11's exact SYSTEM_PROMPT, interaction_prompt, strict summary_grounding.py and recorded live output contract win. The protected router retains authenticate_agent, authorize_customer and product checks. Summary tests are adapted only to use explicit test-only identities. Do not replace the protected router wholesale with the standalone unauthenticated version. |
| Model and deployment bundle | Rebuilt real local Radar on the locked 1200-row training fixture, never six CRM fixtures. The actual staged Azure init/run entry point scores all six inference rows, including C-205 and C-450. This is an offline deployment-bundle test, not a live Azure deployment. |
| Cloud training input | Exact dataset SHA required and 1200-row guard; altered data and six-row inputs are rejected. |
| Runtime versions | conda.yml and requirements-local.txt match the tested serialization runtime: sklearn 1.8.0, pandas 2.2.3, numpy 2.3.5, joblib 1.5.3, pandera 0.35.0. Preflight blocks a mismatch before registration/deployment. The repository's broader requirements-lock.txt is a different historical environment snapshot; use the dedicated Radar pins for this artifact. |
| Live smoke test | Uses real configured server-agent authentication plus CRM ownership/product/eligibility gate before Azure. Receipt counts every submitted eligible row, including no-consent rows. Empty authorized input is not reported as a live success. |

## Measured checks

113 tests passed with one TestClient deprecation warning:

```bash
SAATHI_AS_OF_DATE=2026-10-28 LLM_PROVIDER=mock PYTHONPATH=.:api python -m pytest api/tests/test_sachi_followup.py api/tests/test_worklist_access.py api/tests/test_chat_ml_integration.py api/tests/test_summary.py api/tests/test_Audit.py tests/test_radar_contract_v2.py tests/test_data_radar.py tests/test_radar_contract.py tests/test_azureml_radar.py -q
```

Evidence: docs/evidence/radar_deployment_tests.xml and radar_azure_preflight.json. Previous live Foundry prompt evidence for all 18 interactions is preserved separately in sachi_summary_azure_playground.json. Summary replay tests are offline and use no credits. Existing protected worklist tests use explicit test-only scopes, not claimed production approval.

## Reproducible local build and Azure handover

Use a Python 3.12 environment. Install the API dependencies, the dedicated ml/azureml/requirements-local.txt, and Azure SDK tooling separately for actual deployment. The cloud deployment code uses Azure ML SDK v2 (azure-ai-ml and azure-identity) and the scoring init/run contract documented at https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-managed-online-endpoints .

```bash
python -m data.validate
python -m ml.radar
python -m ml.azureml.preflight
# Nonmutating configuration check; does not import Azure SDK or provision resources:
python -m ml.azureml.deploy
```

Configure the existing subscription, resource group, Azure ML workspace, endpoint name and training compute securely. Foundry gpt-4.1-mini access is distinct from an Azure ML workspace and a deployed Radar scoring URI. No workspace/endpoint/compute target has yet been verified in the browser for this checkpoint. Current local cloud configuration is missing, so deploy prints NOT DEPLOYED rather than claiming success.

After the actual Azure ML target, permissions, quota, and proposed resource/cost settings are reviewed, use one of:

```bash
# Register locally trained model and deploy:
python -m ml.azureml.deploy --execute
# Or submit cloud training, register its output and deploy:
python -m ml.azureml.deploy --execute --train-in-azure
```

The current runner uses deployment blue and routes 100% traffic to it. Review the selected endpoint before execution; do not run it against a shared existing endpoint without reviewing its traffic. Deployment creates one Standard_DS3_v2 instance by default unless AZURE_ML_INSTANCE_TYPE is set. No Azure resources were provisioned by the offline checks.

## Separate real runtime checks

Shreya must provide the actual approved agent/product credential-store configuration (SAATHI_AGENT_CREDENTIALS_FILE); existing customer ownership remains in CRM. Configure an existing approved token as SAATHI_LIVE_AGENT_TOKEN securely, never in git or chat. Reported approval alone is not the mapping or credential configuration. Do not generate grants from model output.

Once Radar is deployed and AZURE_ML_ENDPOINT/AZURE_ML_KEY are securely configured:

```bash
ML_PROVIDER=azure SAATHI_AS_OF_DATE=2026-10-28 PYTHONPATH=.:api python -m ml.azureml.smoke_test
```

For a separate actual Azure OpenAI adapter check, securely configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini, plus the existing agent credentials above:

```bash
PYTHONPATH=.:api python scripts/verify_summary_azure.py --run-live
```

This mounts the protected summary router without overrides, verifies real agent authentication, calls the actual Azure adapter, and requires all three C-204 IDs. Ordinary tests remain LLM_PROVIDER=mock. Neither runtime command has been reported as passing; no runtime credentials or product grants were fabricated.
