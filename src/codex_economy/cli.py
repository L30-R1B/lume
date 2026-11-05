import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from .engine import Engine
from .security import redact
from .store import Store


def parser():
    p = argparse.ArgumentParser(prog="ce", description="Local evidence retrieval and measured Codex execution")
    p.add_argument("--home")
    p.add_argument("--human", action="store_true", help="Pretty JSON for humans (default is compact structured JSON)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("register")
    s.add_argument("name")
    s.add_argument("root")
    sub.add_parser("projects")
    s = sub.add_parser("semantic")
    s.add_argument("project")
    s.add_argument("family", choices=["typescript", "clang", "python"])
    s = sub.add_parser("policy")
    s.add_argument("project")
    s.add_argument("--set", dest="patch", help="JSON policy patch")
    for cmd in ("index", "status", "commands", "capabilities", "map"):
        s = sub.add_parser(cmd)
        s.add_argument("project")
        if cmd == "index":
            s.add_argument("--force", action="store_true")
    for cmd in ("search", "context"):
        s = sub.add_parser(cmd)
        s.add_argument("project")
        s.add_argument("query")
        s.add_argument(
            "--mode",
            choices=["lexical", "structural", "hybrid", "full", "assisted", "hierarchical", "ast-prune", "longcodezip"],
            default="hybrid",
        )
        s.add_argument("--budget", type=int, default=6000)
        s.add_argument("--limit", type=int, default=20)
    s = sub.add_parser("read")
    s.add_argument("project")
    s.add_argument("path")
    s.add_argument("--start", type=int, default=1)
    s.add_argument("--end", type=int, default=200)
    s.add_argument("--hash")
    for cmd in ("graph", "impact"):
        s = sub.add_parser(cmd)
        s.add_argument("project")
        s.add_argument("path")
        s.add_argument("--depth", type=int, default=1)
        s.add_argument("--limit", type=int, default=30)
        s.add_argument("--direction", choices=["in", "out", "both"], default="both")
        s.add_argument("--kind")
    s = sub.add_parser("run")
    s.add_argument("project")
    s.add_argument("--timeout", type=int, default=120)
    s.add_argument("--max-bytes", type=int)
    s.add_argument("--memory-mb", type=int)
    s.add_argument("--cpu-seconds", type=int)
    s.add_argument("argv", nargs=argparse.REMAINDER)
    s = sub.add_parser("log")
    s.add_argument("run")
    s.add_argument("--stream", choices=["stdout", "stderr"], default="stdout")
    s.add_argument("--start", type=int, default=1)
    s.add_argument("--end", type=int, default=200)
    s = sub.add_parser("session")
    s.add_argument("project")
    s.add_argument("objective")
    s.add_argument("acceptance")
    s = sub.add_parser("handoff")
    s.add_argument("session")
    s.add_argument("--patch")
    s.add_argument("--state", default="active")
    s = sub.add_parser("task")
    s.add_argument("project")
    s.add_argument("objective")
    s.add_argument("acceptance")
    s.add_argument("--mode", default="hybrid")
    s.add_argument("--timeout", type=int)
    s.add_argument("--model")
    s.add_argument("--model-profile", default="default")
    s.add_argument("--effort")
    s.add_argument("--harness", choices=["exec", "app-server", "patch"], default="exec")
    s.add_argument("--observed-token-budget", type=int)
    s.add_argument("--thread")
    s.add_argument("--verify", help="JSON argv of independent acceptance check")
    sub.add_parser("doctor")
    sub.add_parser("integrity")
    sub.add_parser("mcp")
    sub.add_parser("metrics")
    s = sub.add_parser("backup")
    s.add_argument("destination")
    s.add_argument("--bundle", action="store_true")
    s = sub.add_parser("restore")
    s.add_argument("source")
    s = sub.add_parser("export")
    s.add_argument("destination")
    s = sub.add_parser("prune")
    s.add_argument("--days", type=int, default=30)
    s = sub.add_parser("integrate")
    s.add_argument("--remove", action="store_true")
    s = sub.add_parser("benchmark")
    s.add_argument("manifest")
    s.add_argument("--execute", action="store_true")
    s.add_argument("--report", action="store_true")
    for cmd in ("entities", "build-model", "setup", "refine", "experiment"):
        s = sub.add_parser(cmd)
        s.add_argument("project")
        if cmd == "entities":
            s.add_argument("--kind")
            s.add_argument("--limit", type=int, default=100)
        if cmd == "build-model":
            s.add_argument("family", choices=["gradle", "cmake"])
        if cmd == "setup":
            s.add_argument("--remove", action="store_true")
            s.add_argument("--hooks", action="store_true")
        if cmd in ("refine", "experiment"):
            s.add_argument("query")
            s.add_argument("--budget", type=int, default=6000)
        if cmd == "refine":
            s.add_argument("missing_fact")
    s = sub.add_parser("recover")
    s.add_argument("--source")
    s = sub.add_parser("batch")
    s.add_argument("project")
    s.add_argument("operations", help="JSON array or @filename")
    s = sub.add_parser("calibrate")
    s.add_argument("dataset")
    s = sub.add_parser("telemetry")
    s = sub.add_parser("accept")
    s.add_argument("session")
    s.add_argument("runs", nargs="+")
    s = sub.add_parser("continuity")
    s.add_argument("session")
    s.add_argument("--budget", type=int, default=4000)
    s = sub.add_parser("trace")
    s.add_argument("project")
    s.add_argument("script")
    s.add_argument("arguments", nargs=argparse.REMAINDER)
    s = sub.add_parser("neural")
    s.add_argument("project")
    s.add_argument("path")
    s.add_argument("--rate", type=float, default=0.5)
    s = sub.add_parser("config")
    s.add_argument("--set", dest="patch")
    s = sub.add_parser("secret")
    s.add_argument("--stdin", action="store_true")
    s.add_argument("--remove", action="store_true")
    s = sub.add_parser("delegate")
    s.add_argument("project")
    s.add_argument("tasks")
    return p


def dispatch(a):
    if a.home:
        os.environ["CE_HOME"] = a.home
    if a.cmd == "mcp":
        from .mcp_server import serve

        return serve()
    if a.cmd in ("recover", "restore"):
        from .store import recover

        destination = a.home or os.environ.get("CE_HOME", Path.home() / ".local/state/codex-economy")
        if a.source and str(a.source).endswith((".tar.gz", ".tgz")):
            from .backup import restore_bundle

            return restore_bundle(destination, a.source)
        return recover(destination, a.source)
    s = Store()
    e = Engine(s)
    if a.cmd == "trace":
        from .traces import trace

        return trace(s, a.project, a.script, a.arguments)
    if a.cmd == "neural":
        from .experiments import neural

        return neural(s, a.project, a.path, a.rate)
    if a.cmd == "config":
        from .config import load, update

        return update(s, json.loads(a.patch)) if a.patch else load(s)
    if a.cmd == "secret":
        from .config import secret

        return secret(s, sys.stdin.read(1024) if a.stdin else None, a.remove)
    if a.cmd == "delegate":
        from .delegation import delegate

        return delegate(s, a.project, json.loads(Path(a.tasks).read_text()))
    if a.cmd == "telemetry":
        from .extensions import telemetry

        raw = sys.stdin.buffer.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Hook input exceeds limit")
        return telemetry(s, json.loads(raw))
    if a.cmd == "calibrate":
        from .providers import calibrate

        return calibrate(json.loads(Path(a.dataset).read_text()))
    if a.cmd == "accept":
        from .continuity import accept

        return accept(s, a.session, a.runs)
    if a.cmd == "continuity":
        from .continuity import handoff, policy

        return {"handoff": handoff(s, a.session, a.budget), "policy": policy(s, a.session)}
    if a.cmd == "batch":
        from .runner import batch

        content = Path(a.operations[1:]).read_text() if a.operations.startswith("@") else a.operations
        return batch(s, a.project, json.loads(content))
    if a.cmd == "build-model":
        from .build_analysis import analyze_build

        return analyze_build(s, a.project, a.family)
    if a.cmd == "setup":
        from .extensions import setup

        return setup(s, a.project, a.remove, a.hooks)
    if a.cmd == "entities":
        p = s.project(a.project)
        e.require_current(a.project)
        if not 1 <= a.limit <= 1000:
            raise ValueError("Entity limit must be 1–1000")
        return s.rows(
            "SELECT * FROM entities WHERE project=? AND (? IS NULL OR kind=?) LIMIT ?",
            (p["id"], a.kind, a.kind, a.limit),
        )
    if a.cmd == "refine":
        from .retrieval import refine

        return refine(e, a.project, a.query, a.missing_fact, a.budget)
    if a.cmd == "experiment":
        from .experiments import compare

        return compare(s, a.project, a.query, a.budget)
    if a.cmd == "semantic":
        from .semantic import analyze

        return analyze(s, a.project, a.family)
    if a.cmd == "register":
        return e.register(a.name, a.root)
    if a.cmd == "projects":
        return s.rows("SELECT name,root FROM projects")
    if a.cmd == "policy":
        p = s.project(a.project)
        if a.patch:
            patch = json.loads(a.patch)
            if set(patch) - {"external", "exclude", "max_file_bytes"}:
                raise ValueError("Unknown policy field")
            pol = {**p["policy"], **patch}
            if (
                not isinstance(pol["external"], bool)
                or not isinstance(pol["exclude"], list)
                or not all(isinstance(v, str) for v in pol["exclude"])
                or not isinstance(pol["max_file_bytes"], int)
                or not 1024 <= pol["max_file_bytes"] <= 10000000
            ):
                raise ValueError("Invalid policy")
            with s.db:
                s.db.execute("UPDATE projects SET policy=? WHERE id=?", (json.dumps(pol), p["id"]))
        return s.project(a.project)["policy"]
    if a.cmd == "capabilities":
        return e.capabilities(a.project)
    if a.cmd == "map":
        return e.map(a.project)
    if a.cmd == "index":
        return e.index(a.project, a.force)
    if a.cmd == "status":
        return e.status(a.project)
    if a.cmd == "commands":
        return e.require_current(a.project)["details"]["commands"]
    if a.cmd == "search":
        return e.search(a.project, a.query, a.limit, a.mode)
    if a.cmd == "context":
        return e.context(a.project, a.query, a.budget, a.mode)
    if a.cmd == "read":
        return e.read(a.project, a.path, a.start, a.end, a.hash)
    if a.cmd in ("graph", "impact"):
        return e.graph(a.project, a.path, "in" if a.cmd == "impact" else a.direction, a.kind, a.depth, a.limit)
    if a.cmd == "run":
        from .runner import Runner

        return Runner(s).run(
            a.project,
            a.argv[1:] if a.argv[:1] == ["--"] else a.argv,
            a.timeout,
            a.max_bytes,
            memory_mb=a.memory_mb,
            cpu_seconds=a.cpu_seconds,
        )
    if a.cmd == "log":
        from .mcp_server import evidence_log

        return evidence_log(a.run, a.start, a.end, a.stream)
    if a.cmd in ("session", "handoff"):
        from .sessions import Sessions

        sessions = Sessions(s)
        if a.cmd == "session":
            return sessions.create(a.project, a.objective, a.acceptance)
        return sessions.update(a.session, json.loads(a.patch), a.state) if a.patch else sessions.get(a.session)
    if a.cmd == "task":
        from .config import load

        config = load(s)
        if a.model_profile not in config["profiles"]:
            raise ValueError("Unknown model profile")
        profile = config["profiles"][a.model_profile]
        a.timeout = a.timeout or config["task_seconds"]
        a.model = a.model or profile["model"]
        a.effort = a.effort or profile["effort"]
        a.observed_token_budget = a.observed_token_budget or config["observed_token_budget"]
        if a.harness == "patch":
            from .patch_harness import execute

            result = execute(s, a.project, a.objective, a.acceptance, a.mode, a.timeout, a.model, a.effort)
        elif a.harness == "app-server":
            from .app_server import execute

            result = execute(
                s,
                a.project,
                a.objective,
                a.acceptance,
                a.mode,
                a.timeout,
                a.model,
                a.effort,
                a.observed_token_budget,
                a.thread,
            )
        else:
            if a.observed_token_budget or a.thread:
                raise ValueError("Observed-budget interruption/thread resume require --harness app-server")
            from .orchestrator import execute

            result = execute(s, a.project, a.objective, a.acceptance, a.mode, a.timeout, a.model, a.effort)
        if a.verify:
            from .runner import Runner
            from .continuity import accept

            check = Runner(s).run(a.project, json.loads(a.verify), timeout=a.timeout)
            e.index(a.project)
            result["verification"] = check
            outcome = result.get("state", result.get("run", {}).get("state"))
            run_code = result.get("run", {}).get("code", 0)
            if check["code"] == 0 and outcome in ("edited", "cached_evidence", "completed") and run_code == 0:
                accept(s, result["session"], [check["run"]])
                result["accepted"] = True
        return result
    if a.cmd == "doctor":
        from .orchestrator import capabilities

        return {
            **capabilities(),
            **s.integrity(),
            "home": str(s.home),
            "schema": __import__("codex_economy.store", fromlist=["VERSION"]).VERSION,
        }
    if a.cmd == "integrity":
        return s.integrity()
    if a.cmd == "backup":
        if a.bundle:
            from .backup import bundle

            return bundle(s, a.destination)
        return s.backup(a.destination)
    if a.cmd == "restore":
        src = Path(a.source).resolve(strict=True)
        con = sqlite3.connect("file:" + str(src) + "?mode=ro", uri=True)
        try:
            if (
                con.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or not 1
                <= con.execute("PRAGMA user_version").fetchone()[0]
                <= __import__("codex_economy.store", fromlist=["VERSION"]).VERSION
            ):
                raise ValueError("Invalid backup")
            import time

            previous = s.backup(str(s.home / ("pre-restore-" + str(time.time_ns()) + ".sqlite")))
            con.backup(s.db)
        finally:
            con.close()
        return {"restored": str(src), "previous": previous}
    if a.cmd == "metrics":
        totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
        observed = 0
        for row in s.rows("SELECT details FROM runs"):
            details = json.loads(row["details"])
            if details.get("source") == "codex-exec-json":
                for usage in details.get("usage", []):
                    observed += 1
                    for field in totals:
                        totals[field] += usage.get(field, 0)
        return {
            "runs": s.rows("SELECT id,project,elapsed,code,state,details FROM runs"),
            "auxiliary": s.rows("SELECT created,payload FROM events WHERE kind='auxiliary'"),
            "subscription_consumption": "unavailable",
            "codex_observed_turns": observed,
            "codex_usage": totals,
            "codex_total_tokens": totals["input_tokens"] + totals["output_tokens"],
        }
    if a.cmd == "export":
        dest = Path(a.destination)
        if dest.exists():
            raise ValueError("Destination exists")
        data = {t: s.rows("SELECT * FROM " + t) for t in ("projects", "snapshots", "sessions", "runs", "events")}
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        return {"export": str(dest.resolve()), "contains_source_or_logs": True}
    if a.cmd == "prune":
        return s.prune(a.days)
    if a.cmd == "integrate":
        import shutil

        executable = (
            str(Path(sys.argv[0]).absolute())
            if Path(sys.argv[0]).name == "ce"
            else str(Path(sys.executable).with_name("ce"))
        )
        if not Path(executable).is_file():
            executable = shutil.which("ce") or sys.argv[0]
        home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        profile = home / "economy.config.toml"
        marker = "# Managed by codex-economy; profile v1\n"
        if profile.exists() and not profile.read_text().startswith(marker):
            raise ValueError("Existing unrelated economy profile; refusing overwrite")
        if a.remove:
            profile.unlink(missing_ok=True)
            return {"removed": str(profile), "base_config_preserved": True}
        text = (
            marker
            + "[mcp_servers.codex-economy]\ncommand = "
            + json.dumps(executable)
            + '\nargs = ["mcp"]\ndefault_tools_approval_mode = "approve"\n'
        )
        home.mkdir(parents=True, exist_ok=True)
        from .security import write_project

        write_project(home, "economy.config.toml", text, expected=profile.read_text() if profile.exists() else None)
        import tomllib

        tomllib.loads(text)
        return {"profile": str(profile), "use": "codex -p economy", "base_config_preserved": True}
    if a.cmd == "benchmark":
        from .benchmark import benchmark

        return benchmark(s, a.manifest, a.execute, a.report)
    raise ValueError("Unknown operation")


def main():
    a = parser().parse_args()
    try:
        result = dispatch(a)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2 if a.human else None))
        if isinstance(result, dict) and (
            result.get("code") not in (None, 0)
            or result.get("state")
            in (
                "timeout",
                "output_limit",
                "spawn_error",
                "budget_reached",
                "model_failed",
                "invalid_response",
                "insufficient_context",
                "blocked",
                "cancelled",
            )
            or result.get("success") is False
        ):
            raise SystemExit(1)
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error": type(error).__name__, "message": redact(str(error))}), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
