import json
import tempfile
from pathlib import Path
from codex_economy.store import Store
from codex_economy.engine import Engine
from codex_economy.semantic import analyze

with tempfile.TemporaryDirectory(prefix="ce-python-semantic-") as folder:
    root = Path(folder) / "project"
    root.mkdir()
    (root / "library.py").write_text("def twice(n):\n return n*2\n")
    (root / "main.py").write_text("from library import twice\nresult = twice(21)\n")
    with Store(Path(folder) / "state") as store:
        engine = Engine(store)
        engine.register("python", root)
        engine.index("python")
        result = analyze(store, "python", "python")
        assert any(
            f["source"] == "main.py" and f["target"] == "library.py" and f["name"] == "twice" for f in result["facts"]
        )
        print(json.dumps({"passed": True, "result": result}, indent=2))
