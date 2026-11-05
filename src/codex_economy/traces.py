import json
import sys
import uuid
from .engine import Engine
from .runner import Runner
from .security import digest


def trace(store, project, script, arguments=None, timeout=120):
    engine = Engine(store)
    p = store.project(project)
    snapshot = engine.require_current(project)
    engine.read(project, script, 1, 1)
    destination = store.home / ("trace-" + uuid.uuid4().hex + ".json")
    run = Runner(store).run(
        project,
        [sys.executable, "-m", "codex_economy.trace_worker", p["root"], str(destination), script, *(arguments or [])],
        timeout=timeout,
    )
    if not destination.exists():
        return {"run": run, "observed": False, "reason": "trace was interrupted before persistence"}
    data = json.loads(destination.read_text())
    details = json.loads(store.rows("SELECT details FROM runs WHERE id=?", (run["run"],))[0]["details"])
    current = engine.require_current(project)
    if details.get("source_fingerprint_after") != snapshot["fingerprint"] or current["id"] != snapshot["id"]:
        raise ValueError("Source changed during trace; evidence not imported")
    with store.db:
        for edge in data["edges"]:
            for path in (edge["source"], edge["target"]):
                engine.read(project, path, 1, 1)
            store.db.execute(
                "INSERT INTO edges(project,source,target,kind,origin,status,snapshot) VALUES(?,?,?,?,?,?,?)",
                (p["id"], edge["source"], edge["target"], "observed_call", data["origin"], "observed", snapshot["id"]),
            )
            store.db.execute(
                "INSERT OR REPLACE INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    digest(str(p["id"]) + json.dumps(edge, sort_keys=True)),
                    p["id"],
                    snapshot["id"],
                    edge["source"],
                    edge["line"],
                    edge["line"],
                    "trace",
                    edge["name"],
                    json.dumps({**edge, "run": run["run"], "fingerprint": snapshot["fingerprint"]}),
                    data["origin"],
                    "observed",
                ),
            )
    return {
        "run": run,
        "trace": str(destination),
        "observed": True,
        "edges": len(data["edges"]),
        "limit_reached": data["limit_reached"],
    }
