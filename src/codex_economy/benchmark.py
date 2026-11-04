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


def benchmark(store, manifest_path, execute=False, report=False):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    frozen = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
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
            else:
                g["unknown_usage"] += 1
        for g in groups.values():
            g["tokens_per_accepted"] = g["tokens"] / g["accepted"] if g["accepted"] and not g["unknown_usage"] else None
        planned = len(manifest["tasks"]) * manifest["repetitions"] * len(manifest["arms"])
        complete = len(records) == planned and all(not g["unknown_usage"] for g in groups.values())
        pairs = []
        keyed = {(r["task"], r["repeat"], r["arm"]): r for r in records}
        for task in manifest["tasks"]:
            for rep in range(manifest["repetitions"]):
                a = keyed.get((task["id"], rep, "A"))
                b = keyed.get((task["id"], rep, "C"))
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
            "paired_A_minus_C_mean_tokens": statistics.mean(pairs) if pairs else None,
            "paired_bootstrap_95_percent": interval,
            "paired_n": len(pairs),
            "subscription_limit_consumption": "unavailable",
            "auxiliary_billing": "unavailable; see events",
            "manifest_hash": frozen,
        }
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
        job = f"{task['id']}-{rep}-{arm}"
        root = out / "workspaces" / job
        if root.exists():
            raise ValueError("Unrecorded workspace exists: inspect and move before resuming " + str(root))
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
        if arm != "A":
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
        record = {
            "task": task["id"],
            "family": task["family"],
            "repeat": rep,
            "arm": arm,
            "usage": usage,
            "accepted": run["code"] == 0 and check["code"] == 0 and unchanged,
            "run": run["run"],
            "verification": check,
            "seconds": time.monotonic() - started,
            "index_seconds": index["seconds"],
            "actions": sum(e.get("type") == "item.completed" for e in events),
            "manifest_hash": frozen,
            "original_hashes": original_hashes,
            "scope_unchanged": unchanged,
            "code": run["code"],
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
        if run["code"] != 0 and not usage:
            return {
                "state": "blocked",
                "reason": "Codex failed without usage; inspect retained stderr/events",
                "job": job,
                "resume": "ce benchmark " + str(manifest_path) + " --execute",
            }
    return benchmark(store, manifest_path, report=True)
