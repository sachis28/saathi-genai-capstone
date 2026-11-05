"""Save endpoint credentials only in the ignored repository-root .env; never print keys."""
from pathlib import Path
import os
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    repository=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True)
    if repository.returncode==0:
        subprocess.run(['git','check-ignore','-q','.env'],cwd=ROOT,check=True)
    elif not (ROOT/'.gitignore').is_file() or '.env' not in (ROOT/'.gitignore').read_text().splitlines():
        raise SystemExit('The local .env must be explicitly ignored before saving credentials')
    common=['-n','saathi-radar-ep','-g','Saathi_rg','-w','saathi-radar-ml']
    def value(command):
        result=subprocess.run(command,text=True,capture_output=True)
        if result.returncode:
            raise SystemExit('Azure credential lookup failed; key and provider output withheld')
        return result.stdout.strip()
    uri=value(['az','ml','online-endpoint','show',*common,'--query','scoring_uri','-o','tsv'])
    key=value(['az','ml','online-endpoint','get-credentials',*common,'--query','primaryKey','-o','tsv'])
    if not uri.startswith('https://') or not key or any(c in key for c in '\n\r'):
        raise SystemExit('Unexpected endpoint configuration; no values printed')
    path=ROOT/'.env'
    # Refuse symlink destinations and preserve unrelated existing configuration.
    if path.is_symlink():
        raise SystemExit('Refusing a symlink .env destination')
    existing=path.read_text().splitlines() if path.exists() else []
    names=('RADAR_ENDPOINT_URL','RADAR_ENDPOINT_KEY','ML_PROVIDER')
    lines=[line for line in existing if not any(line.startswith(n+'=') for n in names)]
    lines.extend(['RADAR_ENDPOINT_URL='+uri,'RADAR_ENDPOINT_KEY='+key,'ML_PROVIDER=azure'])
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'w') as handle:
        handle.write('\n'.join(lines)+'\n')
    print('Saved runtime URL/key/provider to ignored local .env (permissions 600); no key printed')


if __name__=='__main__':
    main()
