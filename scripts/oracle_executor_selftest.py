#!/usr/bin/env python3
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'apps'/'oracle-executor'/'iaffice_executor.py'

with tempfile.TemporaryDirectory(prefix='iaffice-executor-test-') as td:
    env=os.environ.copy()
    env['IAFFICE_EXECUTOR_ROOT']=td
    env['IAFFICE_EXECUTOR_SIGNING_KEY']='self-test-secret'
    proc=subprocess.run(
        [sys.executable,str(target),'--self-test'],
        cwd=ROOT,env=env,capture_output=True,text=True,timeout=30
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr,file=sys.stderr)
        raise SystemExit(proc.returncode)
    data=json.loads(proc.stdout)
    assert data['ok'] is True
    assert data['arbitraryShell'] is False
    artifacts=data['artifacts']
    assert len(artifacts)>=2
    assert all(a['digest'].startswith('sha256:') for a in artifacts)
    assert all(a['ref'].startswith('executor://ORACLE_FREE_EXECUTOR/') for a in artifacts)
    html_path=Path(td)/'artifacts'/'self-test-run'/'index.html'
    assert html_path.exists()
    html=html_path.read_text(encoding='utf-8')
    assert 'private evidence-backed demo' in html
    assert 'not production' in html
    print(json.dumps({'ok':True,'executor':'ORACLE_FREE_EXECUTOR','artifacts':len(artifacts),'private':True,'production':False}))
