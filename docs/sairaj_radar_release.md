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

## Azure inventory and proposed workspace — 2026-11-03

Browser sign-in/MFA succeeded. The Saathi_rg inventory contains four resources: Foundry Saathii, Foundry project Saathi_foundry, saathi-ai-search and saathistorage. Azure Machine Learning inventory in the accessible Azure subscription 1, with resource group/location/type filters set to all, returned "No workspaces to display" (0 of 0). This is limited to resources visible to the signed-in account; it does not establish the absence of inaccessible resources.

Prepared workspace: saathi-radar-ml, existing Saathi_rg, Central US. Azure Review + create validation passed. Proposed dependencies are new dedicated storage, Key Vault and Application Insights; container registry is None at workspace creation. Identity is system-assigned; encryption uses Microsoft-managed keys. No compute or endpoint has been created. Supporting resource usage may incur charges. The final Create action is pending confirmation because it provisions the service identity and associated resource access. Actual Radar training/registration/deployment and live endpoint invocation still follow workspace creation and quota/configuration verification.


## Workspace creation and registration completed — 2026-11-03

After explicit approval, Azure created saathi-radar-ml in Saathi_rg, Central US. The workspace overview reports Provisioning State Succeeded and ML Studio access works. Attached dedicated resources: storage saathiradarml2632017274, Key Vault saathiradarml4708996853 and Application Insights saathiradarml7130385652, with system-assigned workspace identity.

Registered saathi-renewal-radar:1 as CUSTOM using the tested local model.joblib (1809 bytes), SHA256 3c1969fffc0e348faceecb4fd090936d4f4f97b02aeff6980cc1e393d777f13b. ML Studio reported registration success and displays version 1 plus its checksum tag. This is registration of the locally trained 1200-row synthetic model, not cloud training. The six CRM records were not used for training.

No VM, training cluster, serving instance or endpoint was provisioned. The endpoint wizard was inspected and cancelled before deployment. A deployment needs the verified scoring bundle and matching custom environment, not an arbitrary curated environment.

Central US dedicated quota shows 20 total cores available, but Standard DSv2 Family has 0 available cores. The runner's historical Standard_DS3_v2 default is therefore blocked by the observed family quota. Some alternative CPU families show 4 cores, but supported managed-endpoint SKU/capacity/reservation and compute cost still need review before choosing a replacement. No quota request or subscription upgrade was submitted.

The resource-group/workspace names are now populated in .env.example; subscription identity, endpoint name/URI, keys, compute and approved application-agent credentials are still supplied securely at runtime. Evidence: docs/evidence/radar_azure_workspace.json. Existing local test evidence remains 113 passed; no tests were rerun for this documentation/configuration-only update. This section supersedes the earlier pending-workspace-creation status above. Actual Azure endpoint invocation and /worklist cloud acceptance remain pending.


## Reviewed fixed-SKU CLI deployment package — 2026-11-03

Sairaj supplied the reviewed compute decision: Standard_D2a_v4, exactly one instance, no autoscale or quota requests. radar/deploy/ contains endpoint.yml (saathi-radar-ep, key authentication), deployment.yml (blue, registered model v1, fixed SKU/count), score.py (reuses the existing scorer), matching conda.yml, an allowlist-only prepare.py, sample-request.json and a secret-safe local .env helper. The legacy SDK runner default and .env.example now use Standard_D2a_v4, never DSv2. The API adapter accepts the requested RADAR_ENDPOINT_URL and RADAR_ENDPOINT_KEY names first, retaining legacy Azure names as fallbacks.

Azure Cloud Shell CLI verified model type custom_model and found no existing saathi-radar-ep. Extension ml 2.45.2 is current in that session. GitHub account had no existing Codespace. Automatic approval review rejected a full repository clone into Cloud Shell as unnecessarily broad; only a minimal, checksummed scoring/configuration payload plus three explicitly requested synthetic feature rows was uploaded. No unrelated repository content, credentials, training data or weights were transferred in that package. The model remains the existing registered v1.

117 focused offline tests pass, including the exact CLI scorer from an isolated directory, consent=false and -5-day inference, preferred runtime environment names, staged-file allowlist rejection and a private-mode .env write without printing a synthetic test key. The initial broad test run in this fresh worktree lacked the ignored model artifact; the exact registered artifact was copied locally and its checksum verified before rerunning successfully. Test receipt: docs/evidence/radar_managed_endpoint_tests.xml. Preparing these files does not establish a live deployment; see the subsequent cloud receipt when available. Deployment traffic, scoring URI and actual invoke output are pending the final cloud action. Do not commit credentials or merge main.

The exact request/response contract, deployment/invoke commands and post-demo deletion command are in radar/deploy/README.md. Keys are captured only into ignored local .env with RADAR_ENDPOINT_KEY, never into YAML, stdout, git or screenshots. Cloud Shell is ephemeral: Shreya must configure the orchestrator runtime securely using the credential retrieval command, rather than relying on that session persisting.
