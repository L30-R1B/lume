import json
import os
import subprocess
import tempfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='ce-install-') as folder:
    root=Path(folder)
    env={**os.environ,'CE_PREFIX':str(root/'prefix'),'CE_BIN':str(root/'bin'),'CE_HOME':str(root/'state')}
    log=[]
    def run(argv):
        p=subprocess.run(argv,env=env,cwd='/tmp',capture_output=True,text=True,check=False,timeout=180)
        log.append({'argv':argv,'code':p.returncode,'stdout':p.stdout[-3000:],'stderr':p.stderr[-1000:]})
        if p.returncode: raise RuntimeError(json.dumps(log))
    run([str(base/'scripts/install.sh')])
    run([str(root/'bin/ce'),'register','fixture',str(base/'tests/semantic-fixture')])
    run([str(root/'bin/ce'),'index','fixture'])
    run([str(root/'bin/ce'),'search','fixture','twice','--mode','lexical'])
    run([str(base/'scripts/install.sh')])
    # Avoid removing the user's real profile: exercise removal when no ce executable is linked.
    # Profile lifecycle is validated separately by snapshotting its exact managed bytes.
    (root/'bin/ce').unlink()
    run([str(base/'scripts/uninstall.sh')])
    assert (root/'state/state.sqlite').exists()
    assert (base/'tests/semantic-fixture/main.ts').exists()
    assert not (root/'prefix/runtime').exists()
    print(json.dumps({'passed':True,'steps':log,'scope':'clean install, update, operation outside checkout, runtime removal, state/project preservation; profile removal separate'},indent=2))
