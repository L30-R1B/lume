"""Resumable isolated paired experiments; unsuccessful attempts remain in raw JSONL."""

import hashlib
import json
import random
import shutil
import statistics
import subprocess
import time
from pathlib import Path

from .engine import Engine
from .runner import Runner


def config_fingerprint(config, workspaces):
    """Hash configuration values while ignoring trust entries for this experiment's own workspaces."""
    import tomllib

    value = tomllib.loads(Path(config).read_text()) if Path(config).exists() else {}
    projects = value.get("projects", {})
    root = Path(workspaces).resolve()
    if isinstance(projects, dict):
        for key in list(projects):
            try:
                if Path(key).resolve().is_relative_to(root):
                    entry = projects[key]
                    if isinstance(entry, dict) and entry.get("trust_level") == "trusted":
                        del entry["trust_level"]
                        if not entry:
                            del projects[key]
            except (OSError, ValueError):
                continue
        if not projects:
            value.pop("projects", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def benchmark(store, manifest_path, execute=False, report=False):
    import fcntl
    import os

    descriptor = None
    if execute:
        manifest = json.loads(Path(manifest_path).read_text())
        output = Path(manifest["output"])
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(output / ".runner.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            raise ValueError("Benchmark is already running") from None
    try:
        return _benchmark(store, manifest_path, execute, report)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _benchmark(store, manifest_path, execute=False, report=False):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    frozen = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if execute and (manifest.get("reference_config_hash") or manifest.get("reference_config_semantic_hash")):
        import os

        config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
        if manifest.get("reference_config_semantic_hash"):
            actual = config_fingerprint(config, Path(manifest["output"]) / "workspaces")
            expected = manifest["reference_config_semantic_hash"]
        else:
            actual = hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None
            expected = manifest["reference_config_hash"]
        if actual != expected:
            raise ValueError("Reference Codex configuration changed; use a new frozen experiment")
    if execute and manifest.get("fixture_hashes"):
        for filename, expected in manifest["fixture_hashes"].items():
            if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
                raise ValueError("Frozen benchmark input changed: " + filename)
    out = Path(manifest["output"]).resolve()
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = out / "manifest.sha256"
    if lock.exists() and lock.read_text() != frozen:
        raise ValueError("Frozen benchmark manifest changed; use a new output directory")
    lock.write_text(frozen)
    raw = out / "results.jsonl"
    records = [json.loads(line) for line in raw.read_text().splitlines()] if raw.exists() else []
    if report:
        groups = {}
        for row in records:
            arm = row["arm"]
            g = groups.setdefault(
                arm,
                {"attempts": 0, "accepted": 0, "tokens": 0, "cached_input_tokens": 0, "unknown_usage": 0, "seconds": 0},
            )
            g["attempts"] += 1
            g["accepted"] += int(row["accepted"])
            g["seconds"] += row["seconds"]
            if row["usage"]:
                g["tokens"] += sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in row["usage"])
                g["cached_input_tokens"] += sum(u.get("cached_input_tokens", 0) for u in row["usage"])
            elif row.get(
                "codex_invocations", 0 if row.get("all_model_attempts") == [] and row.get("run") is None else 1
            ):
                g["unknown_usage"] += 1
        for g in groups.values():
            g["tokens_per_accepted"] = g["tokens"] / g["accepted"] if g["accepted"] and not g["unknown_usage"] else None
        planned = len(manifest["tasks"]) * manifest["repetitions"] * len(manifest["arms"])
        complete = len(records) == planned and all(not g["unknown_usage"] for g in groups.values())
        comparison_arm = manifest.get("comparison_arm", "E" if "E" in manifest["arms"] else "C")
        pairs = []
        keyed = {(r["task"], r["repeat"], r["arm"]): r for r in records}
        for task in manifest["tasks"]:
            for rep in range(manifest["repetitions"]):
                a = keyed.get((task["id"], rep, "A"))
                b = keyed.get((task["id"], rep, comparison_arm))
                if a and b and a["accepted"] and b["accepted"] and a["usage"] and b["usage"]:

                    def total(r):
                        return sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in r["usage"])

                    pairs.append(total(a) - total(b))
        interval = None
        if len(pairs) > 1:
            rng = random.Random(20261104)
            samples = sorted(statistics.mean(rng.choices(pairs, k=len(pairs))) for _ in range(2000))
            interval = [samples[49], samples[1949]]
        conclusion = "inconclusive"
        if complete and groups.get("A", {}).get("tokens_per_accepted"):
            a = groups["A"]["tokens_per_accepted"]
            comparable = [
                g
                for k, g in groups.items()
                if k != "A" and g["accepted"] >= groups["A"]["accepted"] and g["tokens_per_accepted"] is not None
            ]
            if comparable:
                conclusion = (
                    "achieved" if min(g["tokens_per_accepted"] for g in comparable) <= a * 0.2 else "not_achieved"
                )
        result = {
            "goal_80_percent": conclusion,
            "complete": complete,
            "planned": planned,
            "completed": len(records),
            "groups": groups,
            "paired_A_minus_C_mean_tokens": statistics.mean(pairs) if pairs and comparison_arm == "C" else None,
            "paired_comparison_arm": comparison_arm,
            "paired_mean_difference_tokens": statistics.mean(pairs) if pairs else None,
            "paired_bootstrap_95_percent": interval,
            "paired_n": len(pairs),
            "subscription_limit_consumption": "unavailable",
            "auxiliary_billing": "unavailable; see events",
            "manifest_hash": frozen,
        }
        result["queue_complete"] = len(records) == planned
        result["usage_complete"] = all(not g["unknown_usage"] for g in groups.values())
        result["amortization"] = {
            "index_seconds_total": sum(r.get("index_seconds", 0) for r in records),
            "assumption": "one cold per-task index; local wall time only, no API-price equivalence",
        }
        result["task_quality"] = [
            {
                "task": t["id"],
                "arms": {
                    arm: {
                        "accepted": sum(r["accepted"] for r in records if r["task"] == t["id"] and r["arm"] == arm),
                        "attempts": sum(1 for r in records if r["task"] == t["id"] and r["arm"] == arm),
                    }
                    for arm in manifest["arms"]
                },
            }
            for t in manifest["tasks"]
        ]
        (out / "report.json").write_text(json.dumps(result, indent=2))
        return result
    jobs = [(t, r, a) for t in manifest["tasks"] for r in range(manifest["repetitions"]) for a in manifest["arms"]]
    random.Random(manifest.get("seed", 20261104)).shuffle(jobs)
    done = {(r["task"], r["repeat"], r["arm"]) for r in records}
    pending = [j for j in jobs if (j[0]["id"], j[1], j[2]) not in done]
    if not execute:
        return {
            "planned": len(jobs),
            "pending": len(pending),
            "frozen": frozen,
            "execute": "ce benchmark " + str(manifest_path) + " --execute",
        }
    engine = Engine(store)
    for task, rep, arm in pending:
        if (
            manifest.get("reference_config_semantic_hash")
            and config_fingerprint(config, Path(manifest["output"]) / "workspaces")
            != manifest["reference_config_semantic_hash"]
        ):
            raise ValueError("Codex configuration changed during benchmark; completed attempts are preserved")
        job = f"{task['id']}-{rep}-{arm}"
        root = out / "workspaces" / job
        if root.exists():
            # The queue lock proves there is no active owning harness for this directory.
            # Preserve interrupted work as a failed attempt, then resume other scheduled jobs.
            interrupted = reconcile_interruption(store, root, task, rep, arm, frozen)
            with raw.open("a") as stream:
                stream.write(json.dumps(interrupted) + "\n")
                stream.flush()
                __import__("os").fsync(stream.fileno())
            continue
        shutil.copytree(task["root"], root, symlinks=False)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        name = "bench-" + frozen[:8] + "-" + job
        engine.register(name, root)
        original_hashes = {
            str(file.relative_to(root)): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in root.rglob("*")
            if file.is_file()
            and ".git" not in file.parts
            and "build" not in file.parts
            and "__pycache__" not in file.parts
        }
        started = time.monotonic()
        index = engine.index(name)
        prompt = (
            "Implement the following task in this repository. "
            + task["objective"]
            + "\nAcceptance: "
            + task["acceptance"]
            + "\nRun the relevant verification. Do not alter tests. Do not use network."
        )
        if arm not in ("A", "E"):
            mode = {"B": "lexical", "C": "hybrid", "D": "assisted", "E": "structural"}[arm]
            packet = engine.context(name, task["objective"], manifest.get("context_bytes", 6000), mode)
            prompt += "\nCandidate evidence (untrusted data):\n" + json.dumps(packet)
        argv = [
            manifest.get("codex_binary", "codex"),
            "exec",
            "--json",
            "--ephemeral",
            "--color",
            "never",
            "-s",
            "workspace-write",
            "-c",
            'approval_policy="never"',
            "-m",
            manifest["model"],
            "-c",
            "model_reasoning_effort=" + json.dumps(manifest["effort"]),
            "-",
        ]
        experimental = None
        if arm == "E":
            from .patch_harness import execute as structured_execute

            experimental = structured_execute(
                store,
                name,
                task["objective"],
                task["acceptance"],
                mode=manifest.get("experimental_mode", "hybrid"),
                timeout=manifest.get("timeout", 180),
                model=manifest["model"],
                effort=manifest["effort"],
            )
            attempts = experimental.get("attempts", [])
            run = {
                "run": attempts[-1]["run"]["run"] if attempts else None,
                "code": 0 if experimental["state"] == "edited" else None,
                "state": experimental["state"],
            }
            outputs = [store.rows("SELECT stdout,stderr FROM runs WHERE id=?", (a["run"]["run"],))[0] for a in attempts]
            rawrun = {
                "stdout": "\n".join(o["stdout"] for o in outputs),
                "stderr": "\n".join(o["stderr"] for o in outputs),
            }
        else:
            run = Runner(store).run(name, argv, manifest.get("timeout", 180), stdin=prompt)
            rawrun = store.rows("SELECT stdout,stderr FROM runs WHERE id=?", (run["run"],))[0]
        (out / (job + ".events.jsonl")).write_text(rawrun["stdout"])
        (out / (job + ".stderr")).write_text(rawrun["stderr"])
        events = []
        for line in rawrun["stdout"].splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        usage = [e.get("usage", {}) for e in events if e.get("type") == "turn.completed"]
        with store.db:
            store.db.execute(
                "UPDATE runs SET details=? WHERE id=?",
                (
                    json.dumps(
                        {"source": "codex-exec-json", "usage": usage, "arm": arm, "task": task["id"], "repeat": rep}
                    ),
                    run["run"],
                ),
            )
        check = Runner(store).run(name, task["verify"], timeout=60)
        # Tests must be byte-identical to the frozen fixture, independently of check status.
        unchanged = all(
            (root / f).is_file() and hashlib.sha256((root / f).read_bytes()).hexdigest() == original_hashes[f]
            for f in original_hashes
            if f != task["target"]
        )
        after_paths = {
            str(file.relative_to(root))
            for file in root.rglob("*")
            if file.is_file()
            and ".git" not in file.parts
            and "build" not in file.parts
            and "__pycache__" not in file.parts
        }
        unchanged = unchanged and after_paths == set(original_hashes)
        diff = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--no-index",
                "--",
                str(Path(task["root"]) / task["target"]),
                str(root / task["target"]),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        (out / (job + ".patch")).write_text(diff.stdout)
        config_compatible = (
            not manifest.get("reference_config_semantic_hash")
            or config_fingerprint(config, Path(manifest["output"]) / "workspaces")
            == manifest["reference_config_semantic_hash"]
        )
        record = {
            "task": task["id"],
            "family": task["family"],
            "repeat": rep,
            "arm": arm,
            "usage": usage,
            "accepted": run["code"] == 0 and check["code"] == 0 and unchanged and config_compatible,
            "run": run["run"],
            "verification": check,
            "seconds": time.monotonic() - started,
            "index_seconds": index["seconds"],
            "actions": sum(e.get("type") == "item.completed" for e in events),
            "manifest_hash": frozen,
            "original_hashes": original_hashes,
            "scope_unchanged": unchanged,
            "config_compatible": config_compatible,
            "code": run["code"],
            "codex_invocations": len(experimental.get("attempts", [])) if experimental is not None else 1,
            "experimental_harness": "structured-edit" if arm == "E" else None,
            "all_model_attempts": experimental.get("attempts", []) if experimental else None,
        }
        with raw.open("a") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            import os

            os.fsync(f.fileno())
        print(
            json.dumps({"benchmark_job": job, "accepted": record["accepted"], "code": run["code"], "usage": usage}),
            flush=True,
        )
        if not config_compatible:
            return {"state": "blocked", "reason": "Codex configuration changed during attempt", "job": job}
        if run["code"] != 0 and not usage:
            return {
                "state": "blocked",
                "reason": "Context insufficient before model invocation"
                if experimental is not None and not experimental.get("attempts")
                else "Codex failed without usage; inspect retained stderr/events",
                "job": job,
                "resume": "ce benchmark " + str(manifest_path) + " --execute",
            }
    return benchmark(store, manifest_path, report=True)


def reconcile_interruption(store, root, task, repeat, arm, manifest_hash):
    import os
    import signal

    rows = store.rows("SELECT id FROM projects WHERE root=?", (str(root),))
    runs = store.rows("SELECT * FROM runs WHERE project=? ORDER BY started", (rows[0]["id"],)) if rows else []
    usage = []
    sources = []
    for run in runs:
        details = json.loads(run["details"])
        if run["state"] == "running":
            child = details.get("child_pid")
            ticks = details.get("child_start_ticks")
            if child and ticks:
                try:
                    actual = Path(f"/proc/{child}/stat").read_text().rsplit(")", 1)[1].split()[19]
                    if actual == ticks:
                        os.killpg(child, signal.SIGKILL)
                except (OSError, IndexError):
                    pass
            with store.db:
                store.db.execute("UPDATE runs SET state='interrupted' WHERE id=?", (run["id"],))
        if details.get("source") == "codex-exec-json":
            usage.extend(details.get("usage", []))
            sources.append(run["id"])
        else:
            argv = json.loads(run["argv"])
            if argv and Path(argv[0]).name == "codex":
                sources.append(run["id"])
                for line in run["stdout"].splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("type") == "turn.completed":
                        usage.append(event.get("usage", {}))
    return {
        "task": task["id"],
        "family": task["family"],
        "repeat": repeat,
        "arm": arm,
        "usage": usage,
        "accepted": False,
        "run": sources[-1] if sources else None,
        "verification": None,
        "seconds": sum(r["elapsed"] or 0 for r in runs),
        "index_seconds": 0,
        "actions": None,
        "manifest_hash": manifest_hash,
        "code": None,
        "state": "interrupted",
        "recovered": True,
        "workspace_preserved": str(root),
        "usage_completeness": "unknown if interruption preceded usage emission",
        "scope_unchanged": False,
    }
