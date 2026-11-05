"""Exercise opt-in delegation against two real Codex workers on an isolated fixture."""

import json
import subprocess
import sys
import time
from pathlib import Path

from codex_economy.config import update
from codex_economy.delegation import delegate
from codex_economy.engine import Engine
from codex_economy.store import Store

base = Path(__file__).resolve().parents[1]
root = base / "evidence/delegation-live-workspace"
root.mkdir(exist_ok=False)
project = root / "project"
project.mkdir()
(project / "alpha.py").write_text("def double(x):\n    return x\n")
(project / "beta.py").write_text("def triple(x):\n    return x\n")
for args in (
    ["git", "init", "-q"],
    ["git", "add", "alpha.py", "beta.py"],
    ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"],
):
    subprocess.run(args, cwd=project, check=True)
home = root / "state"
started = time.monotonic()
try:
    with Store(home) as store:
        Engine(store).register("independent", project)
        update(
            store, {"delegation": {"enabled": True, "max_agents": 2}, "task_seconds": 180, "auxiliary": {"mode": "off"}}
        )
        result = delegate(
            store,
            "independent",
            [
                {
                    "objective": "Fix only alpha.py: double(x) must return twice x. Do not change beta.py.",
                    "acceptance": "double(9) == 18 and double(-2) == -4",
                    "independent": True,
                },
                {
                    "objective": "Fix only beta.py: triple(x) must return three times x. Do not change alpha.py.",
                    "acceptance": "triple(9) == 27 and triple(-2) == -6",
                    "independent": True,
                },
            ],
        )
        checks = []
        for i, worker in enumerate(result["workers"]):
            name = "delegate-" + result["group"] + "-" + str(i)
            checkout = Path(store.project(name)["root"])
            expression = (
                "from alpha import double; assert double(9)==18 and double(-2)==-4"
                if i == 0
                else "from beta import triple; assert triple(9)==27 and triple(-2)==-6"
            )
            check = subprocess.run(
                [sys.executable, "-c", expression],
                cwd=checkout,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            diff = subprocess.run(
                ["git", "diff", "--name-only"], cwd=checkout, capture_output=True, text=True, check=True
            ).stdout.splitlines()
            checks.append(
                {
                    "worker": i,
                    "state": worker["state"],
                    "check_code": check.returncode,
                    "changed_files": diff,
                    "expected_only": diff == [("alpha.py" if i == 0 else "beta.py")],
                    "checkout": str(checkout),
                }
            )
        original_clean = not subprocess.run(
            ["git", "status", "--porcelain"], cwd=project, capture_output=True, text=True, check=True
        ).stdout
        report = {
            "passed": len(checks) == 2
            and all(c["state"] == "completed" and c["check_code"] == 0 and c["expected_only"] for c in checks)
            and original_clean
            and not result["accepted"],
            "checks": checks,
            "original_clean": original_clean,
            "delegation": result,
            "seconds": time.monotonic() - started,
        }
        (base / "evidence/delegation-live.json").write_text(json.dumps(report, indent=2))
        print(
            json.dumps(
                {
                    "passed": report["passed"],
                    "checks": checks,
                    "observed_total_tokens": result["observed_total_tokens"],
                    "seconds": report["seconds"],
                }
            )
        )
        if not report["passed"]:
            raise SystemExit(1)
except BaseException as error:
    (base / "evidence/delegation-live-error.json").write_text(
        json.dumps({"error": str(error), "type": type(error).__name__, "seconds": time.monotonic() - started}, indent=2)
    )
    raise
