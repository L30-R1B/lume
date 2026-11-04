"""Predeclared gates for this 600-file synthetic workload: cold <10s; incremental p95 <2s;
lexical p95 <1s; process max RSS <512MiB. Gates are local, not universal SLAs."""
import json
import platform
import resource
import statistics
import tempfile
import time
from pathlib import Path
from codex_economy.store import Store
from codex_economy.engine import Engine

with tempfile.TemporaryDirectory() as directory:
    base=Path(directory);store=Store(base/'state');engine=Engine(store)
    cold=[];incremental=[];search=[]
    for project in range(3):
        root=base/str(project);root.mkdir()
        for i in range(200): (root/f'module_{i}.py').write_text(f'def function_{i}(x):\n    if x < 0:\n        raise ValueError("negative")\n    return x + {i}\n')
        name=f'project-{project}';engine.register(name,root)
        t=time.perf_counter();engine.index(name);cold.append(time.perf_counter()-t)
        for repeat in range(10):
            (root/'module_0.py').write_text(f'def function_0(x):\n    return x + {repeat}\n')
            t=time.perf_counter();engine.index(name);incremental.append(time.perf_counter()-t)
            t=time.perf_counter();engine.search(name,'function_123',mode='lexical');search.append(time.perf_counter()-t)
    def metrics(samples):
        return {'n':len(samples),'p50':statistics.median(samples),'p95':sorted(samples)[min(len(samples)-1,int(len(samples)*.95))],'max':max(samples),'samples':samples}
    result={'hardware':platform.uname()._asdict(),'workload':{'projects':3,'files':600,'bytes':sum(f.stat().st_size for f in base.glob('*/module*'))},'cold_seconds':metrics(cold),'incremental_seconds':metrics(incremental),'lexical_seconds':metrics(search),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'db_bytes':(store.home/'state.sqlite').stat().st_size,'gates':{'cold_max_seconds':10,'incremental_p95_seconds':2,'lexical_p95_seconds':1,'rss_kib':524288}}
    result['passed']=max(cold)<10 and metrics(incremental)['p95']<2 and metrics(search)['p95']<1 and result['max_rss_kib']<524288
    print(json.dumps(result,indent=2))
