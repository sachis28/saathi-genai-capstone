"""Stage only the scoring source allowlist. No .env, model weights or CRM export."""
from pathlib import Path
import shutil

SOURCE_FILES = (
    'ml/__init__.py', 'ml/common.py', 'ml/radar.py',
    'ml/azureml/__init__.py', 'ml/azureml/score.py',
    'data/__init__.py', 'data/validate.py',
)


def prepare(destination=None):
    folder=Path(__file__).resolve().parent
    root=folder.parents[1]
    destination=Path(destination or folder/'code')
    destination.mkdir(parents=True,exist_ok=True)
    # Refuse stale extras rather than uploading unknown files or deleting user data.
    allowed=set(SOURCE_FILES)|{'score.py'}
    extras={str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}-allowed
    if extras:
        raise ValueError('Unexpected files in staging directory; use a fresh directory')
    for relative in SOURCE_FILES:
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/relative,target)
    shutil.copy2(folder/'score.py',destination/'score.py')
    print(f'Staged {len(allowed)} allowlisted source files')
    return destination


if __name__=='__main__':
    prepare()
