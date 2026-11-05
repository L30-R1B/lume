import json
import os
import signal
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from codex_economy.store import Store
from codex_economy.engine import Engine
from codex_economy.build_analysis import analyze_build

base = Path(__file__).resolve().parents[1]
evidence = base / "evidence"
evidence.mkdir(exist_ok=True)
results = {}


def command(argv, cwd, log, timeout=180):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    (evidence / log).write_text(p.stdout + "\n" + p.stderr)
    if p.returncode:
        raise RuntimeError(log + ": " + str(p.returncode))
    return {"code": p.returncode, "log": log}


with tempfile.TemporaryDirectory(prefix="ce-framework-state-") as state:
    with Store(state) as store:
        engine = Engine(store)
        # Next: real production build and localhost HTTP request before and after a source change.
        root = base / "tests/framework-fixtures/next"
        engine.register("next", root)
        route = root / "app/api/ping/route.ts"
        original = route.read_text()
        outputs = []
        try:
            for label, body in [("before", original), ("after", original.replace("'ready'", "'updated'"))]:
                route.write_text(body)
                indexed = engine.index("next")
                built = command(["npm", "run", "build"], root, "next-" + label + "-build.log")
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                log = (evidence / ("next-" + label + "-server.log")).open("w")
                process = subprocess.Popen(
                    ["npm", "run", "start", "--", "--hostname", "127.0.0.1", "--port", str(port)],
                    cwd=root,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                try:
                    deadline = time.monotonic() + 30
                    data = None
                    while time.monotonic() < deadline:
                        try:
                            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=2) as response:
                                data = json.load(response)
                            break
                        except OSError:
                            time.sleep(0.2)
                    assert data == {"status": "ready" if label == "before" else "updated"}
                    outputs.append({"phase": label, "response": data, "build": built, "snapshot": indexed["snapshot"]})
                finally:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    log.close()
        finally:
            route.write_text(original)
        results["next"] = {"passed": True, "phases": outputs}
        # Gradle/Kotlin + declared Android resources, actual compiler and resource validation.
        root = base / "tests/framework-fixtures/gradle"
        engine.register("gradle", root)
        engine.index("gradle")
        model = analyze_build(store, "gradle", "gradle")
        assert any(m["path"] == ":shared" for m in model["modules"])
        assert any(
            d.get("project") == ":shared"
            for m in model["modules"]
            for c in m["configurations"]
            for d in c["dependencies"]
        )
        gradle = str(Path.home() / ".local/share/codex-economy/gradle/gradle-9.2.1/bin/gradle")
        resource = root / "app/src/main/res/values/strings.xml"
        original = resource.read_text()
        try:
            initial = command(
                [gradle, "--offline", "--no-daemon", "--max-workers=1", "check"], root, "gradle-before.log"
            )
            resource.write_text(original.replace("Factory", "Updated factory"))
            assert engine.status("gradle")["state"] == "stale"
            engine.index("gradle")
            final = command(
                [gradle, "--offline", "--no-daemon", "--max-workers=1", "check", "--rerun-tasks"],
                root,
                "gradle-after.log",
            )
            assert any(
                "Updated factory" in r["payload"]
                for r in store.rows("SELECT payload FROM entities WHERE kind='android_resource'")
            )
            results["kotlin_gradle_android_declarations"] = {
                "passed": True,
                "initial": initial,
                "final": final,
                "modules": len(model["modules"]),
                "apk_compilation": False,
                "limitation": "No Android SDK/API installed; actual Kotlin/JVM compilation and Android resource XML validation performed",
            }
        finally:
            resource.write_text(original)
        # Prisma official engine emits SQL, executed with SQLite before and after schema change.
        root = base / "tests/framework-fixtures/prisma"
        engine.register("prisma", root)
        engine.index("prisma")
        prisma = str(Path.home() / ".local/share/codex-economy/prisma/node_modules/.bin/prisma")
        schema = root / "schema.prisma"
        original = schema.read_text()
        try:
            outputs = []
            for phase, body in [
                ("before", original),
                ("after", original.replace("  name String", "  name String\n  active Boolean @default(true)")),
            ]:
                schema.write_text(body)
                engine.index("prisma")
                command([prisma, "validate", "--schema", "schema.prisma"], root, "prisma-" + phase + "-validate.log")
                proc = subprocess.run(
                    [prisma, "migrate", "diff", "--from-empty", "--to-schema-datamodel", "schema.prisma", "--script"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60,
                )
                con = sqlite3.connect(":memory:")
                con.executescript(proc.stdout)
                con.execute("INSERT INTO User(name) VALUES(?)", ("Factory",))
                assert con.execute("SELECT name FROM User").fetchone()[0] == "Factory"
                columns = [r[1] for r in con.execute("PRAGMA table_info(User)")]
                if phase == "after":
                    assert "active" in columns
                outputs.append({"phase": phase, "columns": columns})
                con.close()
            results["prisma_sql"] = {"passed": True, "phases": outputs}
        finally:
            schema.write_text(original)
        # Compose validates declared service topology without inferring calls or pulling images.
        root = Path(state) / "compose"
        root.mkdir()
        engine.register("compose", root)
        compose = root / "compose.yaml"
        for port in (18080, 18081):
            compose.write_text(
                'services:\n  web:\n    image: nginx:alpine\n    ports: ["127.0.0.1:'
                + str(port)
                + ':80"]\n    depends_on: [db]\n  db:\n    image: postgres:17-alpine\n    environment:\n      POSTGRES_HOST_AUTH_METHOD: trust\n'
            )
            indexed = engine.index("compose")
            proc = subprocess.run(
                ["docker", "compose", "-f", str(compose), "config", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=20,
            )
            obj = json.loads(proc.stdout)
            assert obj["services"]["web"]["ports"][0]["published"] == str(port)
        results["compose"] = {
            "passed": True,
            "ports_verified": [18080, 18081],
            "daemon_required": False,
            "container_execution_claimed": False,
        }
(evidence / "framework-validation.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results))
