"""One-shot background job. Raw results survive interruption; no automatic retry of failed attempts."""
import json
import time
import sys
from pathlib import Path
from codex_economy.store import Store
from codex_economy.benchmark import benchmark
base=Path(__file__).resolve().parents[1]
manifest=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else base/'evidence/confirmation-manifest.json'
status=base/'evidence/confirmation-worker-status.json'
try:
    status.write_text(json.dumps({'state':'running','started':time.time(),'manifest':str(manifest)},indent=2))
    result=benchmark(Store(),str(manifest),execute=True)
    report=benchmark(Store(),str(manifest),report=True)
    status.write_text(json.dumps({'state':'completed' if report['complete'] else 'blocked','finished':time.time(),'result':result,'report':report,'scope_complete':False},indent=2))
except BaseException as error:
    status.write_text(json.dumps({'state':'interrupted','exception':type(error).__name__,'message':str(error),'timestamp':time.time(),'scope_complete':False},indent=2))
    raise
