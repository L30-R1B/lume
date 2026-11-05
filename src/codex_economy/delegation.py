"""Opt-in independent Codex jobs, isolated worktrees, with per-worker and aggregate usage."""

import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from .config import load
from .engine import Engine
from .store import Store


def delegate(store, project, tasks):
    config = load(store)
    if not config["delegation"]["enabled"]:
        raise ValueError("Delegation is off; enable explicitly in ce config")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= config["delegation"]["max_agents"]:
        raise ValueError("Independent task count exceeds configured delegation limit")
    p = store.project(project)
    dirty = subprocess.run(
        ["git", "-C", p["root"], "status", "--porcelain"], capture_output=True, text=True, timeout=10, check=True
    )
    if dirty.stdout:
        raise ValueError("Delegation requires a clean committed snapshot; preserve edits before creating worktrees")
    prepared = []
    group = uuid.uuid4().hex[:12]
    for i, task in enumerate(tasks):
        if (
            not isinstance(task, dict)
            or not task.get("objective")
            or not task.get("acceptance")
            or not task.get("independent", False)
        ):
            raise ValueError("Each delegated job must declare objective, acceptance and independence")
        root = store.home / "worktrees" / group / str(i)
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", p["root"], "worktree", "add", "--detach", str(root), "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        name = "delegate-" + group + "-" + str(i)
        Engine(store).register(name, root)
        prepared.append((name, task))

    def execute_one(item):
        from .app_server import execute

        name, task = item
        with Store(store.home) as local:
            return execute(
                local,
                name,
                task["objective"],
                task["acceptance"],
                timeout=config["task_seconds"],
                budget=config["observed_token_budget"],
            )

    with ThreadPoolExecutor(max_workers=len(prepared)) as pool:
        results = list(pool.map(execute_one, prepared))
    usage = sum(r["usage"]["total"]["totalTokens"] for r in results if r.get("usage"))
    summary = {
        "group": group,
        "workers": results,
        "observed_total_tokens": usage,
        "accepted": False,
        "merge_automatic": False,
        "worktrees_preserved": True,
        "reason": "independent checks and integration required before acceptance",
    }
    store.event("delegation", summary)
    return summary
