"""Offline deployment-bundle test. Does not provision resources or call Azure."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from importlib.metadata import version

from ml.azureml.deploy import SOURCE_FILES, stage_source
from ml.common import ARTIFACTS, ROOT, sha256, write_json


def check(model_dir=None):
    model_dir = Path(model_dir or ARTIFACTS / 'radar').resolve()
    if not (model_dir / 'model.joblib').is_file():
        raise FileNotFoundError('Run python -m ml.radar before deployment preflight')
    # Check pickle/runtime compatibility against the actual deploy environment pins.
    config = (ROOT / 'ml/azureml/conda.yml').read_text()
    versions = {pkg:version(pkg) for pkg in ('scikit-learn','pandas','numpy','joblib','pandera')}
    for pkg, value in versions.items():
        pin = f'{pkg}[pandas]=={value}' if pkg == 'pandera' else f'{pkg}=={value}'
        if pin not in config:
            raise RuntimeError(f'Deployment runtime pin does not match local training runtime: {pkg}')
    manifest = json.loads((ROOT / 'data/generated/manifest.json').read_text())
    training_sha = sha256(ROOT / 'data/generated/radar.csv')
    if training_sha != manifest['files']['radar.csv']:
        raise RuntimeError('Locked Radar training dataset hash mismatch')
    rows = json.loads((ROOT / 'data/radar_input.json').read_text())
    with tempfile.TemporaryDirectory(prefix='saathi-bundle-check-') as folder:
        stage_source(folder)
        actual = sorted(str(p.relative_to(folder)) for p in Path(folder).rglob('*') if p.is_file())
        if actual != sorted(SOURCE_FILES):
            raise RuntimeError('Unexpected deployment source bundle files')
        env = os.environ.copy()
        env['PYTHONPATH'] = folder
        env['AZUREML_MODEL_DIR'] = str(model_dir)
        # Exercise the exact staged entry point from outside the repository.
        proc = subprocess.run([sys.executable,'-c',
            'import json,sys; from ml.azureml.score import init,run; init(); print(json.dumps(run(sys.stdin.read())))'],
            cwd=folder,env=env,input=json.dumps({'data':rows}),text=True,capture_output=True,check=True)
        scores = json.loads(proc.stdout)
    if {r['customer_id'] for r in scores} != {r['customer_id'] for r in rows}:
        raise RuntimeError('Scoring bundle dropped or added CRM inference IDs')
    result = {'status':'passed','scope':'offline staged Azure scoring entry point, not deployed Azure',
        'model_sha256':sha256(model_dir / 'model.joblib'),'training_data_sha256':training_sha,'runtime_versions':versions,
        'source_files':list(SOURCE_FILES),'inference_n':len(rows),'scores':scores,
        'negative_days_ids':[r['customer_id'] for r in rows if r['days_to_renewal'] < 0],
        'no_consent_ids':[r['customer_id'] for r in rows if not r['consent']],
        'note':'Endpoint scoring is technical only. Authenticated CRM ownership/product/eligibility gate runs before cloud submission.'}
    write_json(ARTIFACTS / 'azure_preflight.json',result)
    return result


if __name__ == '__main__':
    result = check()
    print(json.dumps({k:result[k] for k in ('status','scope','inference_n','negative_days_ids','no_consent_ids')},indent=2))
