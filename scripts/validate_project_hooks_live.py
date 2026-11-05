"""Try project-layer hook discovery using a vetted disposable fixture and official one-off trust flag."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
ce = str(Path.home() / ".local/bin/ce")
with tempfile.TemporaryDirectory(prefix="ce-project-hooks-") as temporary:
    temporary = Path(temporary)
    project = temporary / "project"
    state = temporary / "state"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    env = dict(os.environ, CE_HOME=str(state))

    def call(args):
        return subprocess.run(args, capture_output=True, text=True, check=True, env=env, timeout=30)

    call([ce, "register", "fixture", str(project)])
    call([ce, "setup", "fixture", "--hooks"])
    assert (project / ".codex/config.toml").is_file(), "setup did not create its project discovery layer"
    trust = "projects." + json.dumps(str(project)) + '.trust_level="trusted"'
    command = [
        "codex",
        "--enable",
        "hooks",
        "--dangerously-bypass-hook-trust",
        "-c",
        trust,
        "exec",
        "--json",
        "--ephemeral",
        "--skip-git-repo-check",
        "-s",
        "workspace-write",
        "-C",
        str(project),
        "Reply OK.",
    ]
    process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=150, check=False)
    (base / "evidence/hooks-project-latest.jsonl").write_text(process.stdout)
    (base / "evidence/hooks-project-latest.stderr").write_text(process.stderr)
    import sqlite3

    with sqlite3.connect(state / "state.sqlite") as db:
        events = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE kind='hook' ORDER BY id")]
    report = {
        "passed": process.returncode == 0 and any(e.get("hook_event_name") == "PostModelRequest" for e in events),
        "code": process.returncode,
        "events": events,
        "fixture_trust": "official one-off bypass for vetted disposable hooks",
        "configured_command": json.loads((project / ".codex/hooks.json").read_text())["hooks"]["PostModelRequest"][0][
            "hooks"
        ][0]["command"],
    }
    (base / "evidence/hooks-project-latest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    if not report["passed"]:
        raise SystemExit(1)
