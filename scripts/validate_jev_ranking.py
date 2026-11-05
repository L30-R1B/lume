import json
import tempfile
from pathlib import Path
from codex_economy.store import Store
from codex_economy.engine import Engine

base = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="ce-jev-evidence-") as folder:
    root = Path(folder) / "project"
    root.mkdir()
    (root / "logic.py").write_text("def calculate_tax(amount):\n    return amount * 0.2\n")
    for i in range(7):
        (root / f"notes-{i}.md").write_text(
            f"# Tax module {i}\nTax configuration is described here, but the actual calculate_tax implementation is elsewhere.\n"
        )
    with Store() as store:
        engine = Engine(store)
        engine.register("jev-ranking-" + root.parent.name, root)
        name = "jev-ranking-" + root.parent.name
        p = store.project(name)
        p["policy"]["external"] = True
        with store.db:
            store.db.execute("UPDATE projects SET policy=? WHERE id=?", (json.dumps(p["policy"]), p["id"]))
        engine.index(name)
        before = store.rows("SELECT coalesce(max(id),0) AS last FROM events")[0]["last"]
        result = engine.context(name, "Find the calculate_tax implementation", 6000, "assisted")
        events = [
            json.loads(r["payload"])
            for r in store.rows("SELECT payload FROM events WHERE kind='auxiliary' AND id>?", (before,))
        ]
        report = {
            "passed": result.get("effective_mode", {}).get("mode") in ("jev", "jev-cache")
            and bool(result["evidence"])
            and result["evidence"][0]["path"] == "logic.py",
            "context": result,
            "real_calls": events,
            "external_policy_explicitly_enabled_for_public_synthetic_fixture": True,
        }
        (base / "evidence/jev-ranking-real.json").write_text(json.dumps(report, indent=2))
        print(json.dumps({"passed": report["passed"], "mode": result.get("effective_mode")}))
        if not report["passed"]:
            raise SystemExit(1)
