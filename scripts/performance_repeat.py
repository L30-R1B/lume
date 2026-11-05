"""Repeat unchanged predeclared gates; preserve every run and machine load context."""

import json
import os
import subprocess
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
reports = []
for i in range(3):
    before = {"loadavg": Path("/proc/loadavg").read_text().strip(), "meminfo": Path("/proc/meminfo").read_text()}
    p = subprocess.run(
        [sys.executable, str(base / "scripts/performance.py")], capture_output=True, text=True, timeout=120, check=True
    )
    report = json.loads(p.stdout)
    report["environment_before"] = before
    report["environment_after_loadavg"] = Path("/proc/loadavg").read_text().strip()
    reports.append(report)
    (base / "evidence" / f"performance-final-{i + 1}.json").write_text(json.dumps(report, indent=2))
result = {
    "runs": reports,
    "all_gates_passed": all(r["passed"] for r in reports),
    "prior_failed_run_preserved": "evidence/performance-v2.json",
    "cold_index_definition": "fresh database, no extraction cache; OS page cache not forcibly cleared",
    "logical_cpus": os.cpu_count(),
}
(base / "evidence/performance-final.json").write_text(json.dumps(result, indent=2))
print(
    json.dumps(
        {
            "all_gates_passed": result["all_gates_passed"],
            "lexical_p95_seconds": [r["lexical_seconds"]["p95"] for r in reports],
        }
    )
)
