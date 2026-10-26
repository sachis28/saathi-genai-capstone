"""Register and deploy an already trained model in an existing Azure ML workspace."""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

from ml.common import ARTIFACTS, ROOT, write_json


def main(execute=False, train_in_azure=False):
    required = ["AZURE_SUBSCRIPTION_ID","AZURE_RESOURCE_GROUP","AZURE_ML_WORKSPACE","AZURE_ML_ENDPOINT_NAME"]
    if train_in_azure:
        required.append("AZURE_ML_COMPUTE")
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print("NOT DEPLOYED. Configure: "+", ".join(missing))
        return 2
    if not execute:
        print("Configuration present. Use --execute to register and deploy to the existing workspace.")
        return 0
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import CodeConfiguration, Environment, ManagedOnlineDeployment, ManagedOnlineEndpoint, Model
    from azure.identity import DefaultAzureCredential
    model_path = ARTIFACTS / "radar" / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError("Run python -m ml.radar first")
    client = MLClient(DefaultAzureCredential(),os.environ[required[0]],os.environ[required[1]],os.environ[required[2]])
    endpoint_name = os.environ[required[3]]
    # Stage an explicit allowlist of source files: never upload .env, .git, local data or unrelated project files.
    with tempfile.TemporaryDirectory(prefix="saathi-azure-") as folder:
        stage = Path(folder)
        for relative in ["ml/__init__.py","ml/common.py","ml/radar.py","ml/azureml/__init__.py","ml/azureml/score.py","ml/azureml/train_job.py","data/__init__.py","data/validate.py"]:
            target = stage / relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT / relative,target)
        environment = Environment(name="saathi-radar-env",image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04:latest",
            conda_file=str(ROOT / "ml/azureml/conda.yml"))
        model_uri = str(model_path)
        training_job = None
        if train_in_azure:
            from azure.ai.ml import command, Input, Output
            job = command(code=folder,
                command="python -m ml.azureml.train_job --data ${{inputs.data}} --output ${{outputs.model}}",
                inputs={"data":Input(type="uri_file",path=str(ROOT / "data/generated/radar.csv"))},
                outputs={"model":Output(type="uri_folder")},environment=environment,
                compute=os.environ["AZURE_ML_COMPUTE"],experiment_name="saathi-renewal-radar")
            submitted = client.jobs.create_or_update(job)
            training_job = submitted.name
            client.jobs.stream(training_job)
            completed = client.jobs.get(training_job)
            if completed.status!="Completed":
                raise RuntimeError("Azure training did not complete successfully")
            model_uri = f"azureml://jobs/{training_job}/outputs/model"
        registered = client.models.create_or_update(Model(name="saathi-renewal-radar",path=model_uri,type="custom_model",
            description="Synthetic demo model; not validated for real customer decisions"))
        try:
            client.online_endpoints.get(endpoint_name)
        except Exception as error:
            from azure.core.exceptions import ResourceNotFoundError
            if not isinstance(error,ResourceNotFoundError):
                raise
            client.online_endpoints.begin_create_or_update(ManagedOnlineEndpoint(name=endpoint_name,auth_mode="key")).result()
        deployment = ManagedOnlineDeployment(name="blue",endpoint_name=endpoint_name,model=registered,environment=environment,
            code_configuration=CodeConfiguration(code=folder,scoring_script="ml/azureml/score.py"),
            instance_type=os.getenv("AZURE_ML_INSTANCE_TYPE","Standard_DS3_v2"),instance_count=1)
        client.online_deployments.begin_create_or_update(deployment).result()
    endpoint = client.online_endpoints.get(endpoint_name)
    endpoint.traffic = {"blue":100}
    client.online_endpoints.begin_create_or_update(endpoint).result()
    write_json(ARTIFACTS / "azure_deployment.json",{"status":"deployed","endpoint_name":endpoint_name,
        "scoring_uri":endpoint.scoring_uri,"registered_model":registered.id,"training_job":training_job,"test_call":"not yet run"})
    print("Deployed: "+endpoint.scoring_uri)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--train-in-azure",action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(args.execute,args.train_in_azure))
