"""Clean isolated release install/update/rollback/uninstall; no user configuration mutations."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
report = []
with tempfile.TemporaryDirectory(prefix="ce-release-validation-") as directory:
    root = Path(directory)
    prefix = root / "prefix"
    binpath = root / "bin"
    state = root / "state"
    project = root / "project"
    project.mkdir()
    (project / "module.py").write_text("def answer():\n return 42\n")
    env = {**os.environ, "CE_PREFIX": str(prefix), "CE_BIN": str(binpath), "CE_HOME": str(state)}

    def execute(argv, cwd="/tmp", timeout=240):
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
        report.append({"argv": argv, "code": p.returncode, "stdout": p.stdout[-1600:], "stderr": p.stderr[-1200:]})
        if p.returncode:
            raise RuntimeError(json.dumps(report[-1]))
        return p.stdout

    execute([str(base / "scripts/install.sh")], timeout=300)
    ce = str(binpath / "ce")
    release1 = os.readlink(prefix / "runtime")
    execute([ce, "register", "fixture", str(project)])
    execute([ce, "index", "fixture"])
    result = json.loads(execute([ce, "context", "fixture", "answer"]))
    assert "return 42" in str(result)
    execute([ce, "setup", "fixture"])
    execute([ce, "setup", "fixture", "--remove"])
    execute([str(base / "scripts/install.sh")], timeout=300)
    release2 = os.readlink(prefix / "runtime")
    execute([str(base / "scripts/rollback.sh")])
    assert os.readlink(prefix / "runtime") == release1
    execute([ce, "integrity"])
    # Exercise runtime removal separately, preserving the real user's economy profile.
    (binpath / "ce").unlink()
    execute([str(base / "scripts/uninstall.sh")])
    assert (state / "state.sqlite").exists() and (project / "module.py").exists()
    assert not (prefix / "runtime").exists()
    print(
        json.dumps(
            {
                "passed": True,
                "first_release": release1,
                "second_release": release2,
                "state_preserved": True,
                "project_preserved": True,
                "operations": report,
            },
            indent=2,
        )
    )
