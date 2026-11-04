import hashlib
import json
import subprocess
from pathlib import Path
from codex_economy.store import Store
from codex_economy.engine import Engine
from codex_economy.runner import Runner
from codex_economy.sessions import Sessions
from codex_economy.orchestrator import execute
base=Path(__file__).resolve().parents[1]
root=base/'evidence/e2e-workspace'
root.mkdir(exist_ok=True)
(root/'fee.py').write_text('def shipping_fee(total):\n    return 10\n')
(root/'check.py').write_text('from fee import shipping_fee\nassert shipping_fee(99) == 10\nassert shipping_fee(100) == 0\nassert shipping_fee(150) == 0\n')
protected=hashlib.sha256((root/'check.py').read_bytes()).hexdigest()
subprocess.run(['git','init','-q',str(root)],check=True)
s=Store();e=Engine(s);e.register('e2e-shipping',root)
result=execute(s,'e2e-shipping','Fix shipping_fee in fee.py: orders with total >=100 have free shipping, lower totals cost 10. Only change fee.py.','python3 check.py passes and check.py is unchanged.',mode='lexical',timeout=180)
check=Runner(s).run('e2e-shipping',['python3','check.py'])
accepted=result['run']['code']==0 and check['code']==0 and hashlib.sha256((root/'check.py').read_bytes()).hexdigest()==protected
updated=e.index('e2e-shipping')
session=Sessions(s).update(result['session'],{'checks':[check], 'affected_files':['fee.py'],'snapshot':updated['snapshot'],'next_step':'complete' if accepted else 'investigate verification'},'accepted' if accepted else 'failed')
report={'accepted':accepted,'task':result,'verification':check,'snapshot':updated,'session':session,'source':(root/'fee.py').read_text(),'protected_test_unchanged':hashlib.sha256((root/'check.py').read_bytes()).hexdigest()==protected}
(base/'evidence/e2e-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'accepted':accepted,'report':str(base/'evidence/e2e-report.json')}))
