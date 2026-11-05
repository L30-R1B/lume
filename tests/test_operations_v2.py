import json
import os
import time
import sqlite3
import sys
from pathlib import Path
import pytest
from codex_economy.engine import Engine
from codex_economy.store import Store, SCHEMA, recover
from codex_economy.runner import Runner, batch, summarize
from codex_economy.sessions import Sessions
from codex_economy.continuity import accept, handoff
from codex_economy.extensions import setup, telemetry
from codex_economy.providers import calibrate, LSAEmbedder


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    home = tmp_path / "state"
    monkeypatch.setenv("CE_HOME", str(home))
    store = Store(home)
    engine = Engine(store)
    engine.register("project", root)
    yield root, store, engine
    store.close()


def test_v1_migration_and_corrupt_recovery(tmp_path):
    home = tmp_path / "state"
    home.mkdir()
    con = sqlite3.connect(home / "state.sqlite")
    con.executescript(SCHEMA)
    con.close()
    store = Store(home)
    assert store.db.execute("PRAGMA user_version").fetchone()[0] == 3
    with store.db:
        store.db.execute("INSERT INTO events(created,kind,payload) VALUES(1,'preserved','{}')")
    backup = tmp_path / "backup.sqlite"
    store.backup(backup)
    with pytest.raises(ValueError, match="in use"):
        recover(home, backup)
    store.close()
    (home / "state.sqlite").write_bytes(b"corrupt index")
    restored = recover(home, backup)
    assert restored["integrity"]["sqlite"] == "ok"
    with Store(home) as restarted:
        assert restarted.rows("SELECT kind FROM events")[0]["kind"] == "preserved"
    assert (Path(restored["archive"]) / "state.sqlite").read_bytes() == b"corrupt index"


def test_v2_migration_keeps_legacy_text_and_reports_missing_bytes(tmp_path):
    from codex_economy.runner import log_bytes
    from codex_economy.store import MIGRATIONS

    home = tmp_path / "state-v2"
    home.mkdir()
    with sqlite3.connect(home / "state.sqlite") as db:
        db.executescript(SCHEMA)
        for statement in MIGRATIONS[2]:
            db.execute(statement)
        db.execute(
            "INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("old", None, "[]", 1, 0, 0, "completed", "old text", "", "{}"),
        )
    with Store(home) as store:
        assert store.db.execute("PRAGMA user_version").fetchone()[0] == 3
        assert store.rows("SELECT stdout FROM runs WHERE id='old'")[0]["stdout"] == "old text"
        with pytest.raises(ValueError, match="saved before schema 3"):
            log_bytes(store, "old")


def test_benchmark_config_hash_ignores_only_own_workspace_trust(tmp_path):
    from codex_economy.benchmark import config_fingerprint

    config = tmp_path / "config.toml"
    workspaces = tmp_path / "workspaces"
    project = workspaces / "fixture"
    config.write_text('model = "gpt-6.1-sol"\n')
    before = config_fingerprint(config, workspaces)
    config.write_text('model = "gpt-6.1-sol"\n[projects.' + json.dumps(str(project)) + ']\ntrust_level = "trusted"\n')
    assert config_fingerprint(config, workspaces) == before
    config.write_text(config.read_text() + 'sandbox_mode = "danger-full-access"\n')
    assert config_fingerprint(config, workspaces) != before
    config.write_text('model = "other-model"\n')
    assert config_fingerprint(config, workspaces) != before


def test_project_root_swap_rejected(env, tmp_path):
    root, store, engine = env
    root.rename(tmp_path / "original")
    root.symlink_to(tmp_path / "original", target_is_directory=True)
    with pytest.raises(ValueError):
        engine.read("project", "file.py")


def test_contracts_next_android_compose_and_docs(env):
    root, store, engine = env
    (root / "app/api/ping").mkdir(parents=True)
    (root / "app/api/ping/route.ts").write_text("export async function GET() { return Response.json({ok:true}); }")
    (root / "res/values").mkdir(parents=True)
    (root / "res/values/strings.xml").write_text('<resources><string name="title">Factory</string></resources>')
    (root / "AndroidManifest.xml").write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="factory"><application><activity android:name=".MainActivity" android:exported="false"/></application></manifest>'
    )
    (root / "compose.yaml").write_text(
        'services:\n  web:\n    image: nginx\n    ports: ["127.0.0.1:8080:80"]\n    depends_on: [db]\n  db:\n    image: postgres\n'
    )
    (root / "database.md").write_text("# Database schema\nUse transactions for migrations.\n")
    engine.index("project")
    rows = store.rows("SELECT kind,name,payload FROM entities")
    assert any(r["kind"] == "next_route" and r["name"] == "/api/ping" for r in rows)
    assert any(r["kind"] == "android_activity" and r["name"] == ".MainActivity" for r in rows)
    assert any(r["kind"] == "compose_service" and "8080" in r["payload"] for r in rows)
    assert engine.capabilities("project")["framework_relations"]
    context = engine.context("project", "database migration", 6000)
    assert any(e["path"] == "database.md" for e in context["evidence"])
    (root / "res/values/strings.xml").write_text('<resources><string name="title">Updated</string></resources>')
    engine.index("project")
    assert any(
        "Updated" in r["payload"] for r in store.rows("SELECT payload FROM entities WHERE kind='android_resource'")
    )


def test_invalid_contract_and_xml_entity_are_explicit(env):
    root, store, engine = env
    (root / "AndroidManifest.xml").write_text(
        '<!DOCTYPE doc [<!ENTITY x SYSTEM "file:///etc/passwd">]><manifest>&x;</manifest>'
    )
    result = engine.index("project")
    assert result["state"] == "partial" and result["warnings"]
    assert not store.rows("SELECT * FROM entities WHERE kind='android_manifest'")


def test_pipe_backpressure_closed_stdio_timeout_and_limits(env):
    root, store, engine = env
    runner = Runner(store)
    text = "x" * 200000
    result = runner.run(
        "project", [sys.executable, "-c", 'import sys; print("y"*200000); print(len(sys.stdin.read()))'], stdin=text
    )
    assert result["code"] == 0
    assert "200000" in store.rows("SELECT stdout FROM runs WHERE id=?", (result["run"],))[0]["stdout"]
    closed = runner.run(
        "project", [sys.executable, "-c", "import os,time;os.close(1);os.close(2);time.sleep(4)"], timeout=0.2
    )
    assert closed["state"] == "timeout"
    limited = runner.run("project", [sys.executable, "-c", "x=bytearray(1024*1024*128)"], memory_mb=40)
    assert limited["code"] != 0
    cpu = runner.run("project", [sys.executable, "-c", "while True: pass"], cpu_seconds=1, timeout=5)
    assert cpu["code"] != 0


def test_batch_dependencies_failures_and_cycles(env):
    root, store, engine = env
    ops = [
        {"id": "one", "argv": [sys.executable, "-c", 'from pathlib import Path;Path("one").write_text("ok")']},
        {"id": "fail", "argv": [sys.executable, "-c", "raise SystemExit(3)"]},
        {
            "id": "dependent",
            "needs": ["one"],
            "argv": [sys.executable, "-c", 'from pathlib import Path;assert Path("one").read_text()=="ok"'],
        },
        {"id": "skipped", "needs": ["fail"], "argv": [sys.executable, "-c", 'raise Exception("must not execute")']},
    ]
    result = batch(store, "project", ops)
    assert result["results"]["dependent"]["code"] == 0
    assert result["results"]["skipped"]["state"] == "dependency_failed"
    with pytest.raises(ValueError, match="cycle"):
        batch(store, "project", [{"id": "a", "needs": ["a"], "argv": ["true"]}])


def test_acceptance_is_bound_to_real_current_checks(env):
    root, store, engine = env
    (root / "check.py").write_text("assert 2+2==4\n")
    indexed = engine.index("project")
    sid = Sessions(store).create("project", "arithmetic", "check.py passes")["session"]
    with pytest.raises(ValueError):
        Sessions(store).update(sid, {"checks": [{"run": "fake"}]}, "accepted")
    run = Runner(store).run("project", [sys.executable, "check.py"])
    result = accept(store, sid, [run["run"]])
    assert result["state"] == "accepted"
    assert handoff(store, sid)["state"] == "accepted"
    (root / "check.py").write_text("assert 2+2==5\n")
    engine.index("project")
    with pytest.raises(ValueError, match="current source"):
        accept(store, sid, [run["run"]])
    assert indexed["state"] == "ready"


def test_cache_validity_expiry_and_extensions(env, monkeypatch):
    root, store, engine = env
    store.cache_put("inference", "key", "model-v1", {"rank": [1]}, ttl=1)
    assert store.cache_get("inference", "key", "model-v2") is None
    assert store.cache_get("inference", "key", "model-v1") == {"rank": [1]}
    with store.db:
        store.db.execute("UPDATE cache SET expires=0 WHERE key='key'")
    assert store.cache_get("inference", "key", "model-v1") is None
    setup(store, "project")
    setup(store, "project")
    skill = root / ".agents/skills/codex-economy/SKILL.md"
    assert skill.exists()
    setup(store, "project", remove=True)
    assert not skill.exists()
    (root / ".agents").rename(root / "saved-agents")
    (root / ".agents").symlink_to(root / "saved-agents")
    with pytest.raises(OSError):
        setup(store, "project")
    telemetry(
        store,
        {
            "hook_event_name": "PostModelRequest",
            "token_usage": {"input_tokens": 7},
            "prompt": "SECRET",
            "authorization": "Bearer hidden",
        },
    )
    event = json.loads(store.rows("SELECT payload FROM events WHERE kind='hook'")[0]["payload"])
    assert event["token_usage"]["input_tokens"] == 7 and "prompt" not in event and "authorization" not in event


def test_log_structure_duplicates_and_calibration():
    result = summarize("error causal\n" + "repeat\n" * 1000)
    assert result["repeated"][0]["count"] == 1000
    assert summarize('{"status":"failed","errors":["cause"]}')["structured"]["status"] == "failed"
    labeled = [
        {"split": "calibration", "probability": probability, "label": label}
        for probability, label in [(0.1, 0), (0.3, 0), (0.7, 1), (0.8, 1)]
    ]
    calibration = calibrate(labeled)
    assert calibration["f1"] == 1 and not calibration["guarantee"]
    labeled[0]["split"] = "evaluation"
    with pytest.raises(ValueError):
        calibrate(labeled)
    assert len(LSAEmbedder().encode(["database transaction", "factory machine", "transaction database"])) == 3


def test_structured_edit_hashes_ambiguity_permissions_and_rollback(env):
    from codex_economy.patch_harness import apply_edits
    from codex_economy.security import digest

    root, store, engine = env
    path = root / "execute.py"
    source = "#!/usr/bin/env python3\nprint(1)\n"
    path.write_text(source)
    path.chmod(0o755)
    edit = {"path": "execute.py", "hash": digest(source), "old": "print(1)", "new": "print(2)"}
    with pytest.raises(ValueError, match="not present"):
        apply_edits(store, "project", [edit], set())
    result = apply_edits(store, "project", [edit], {"execute.py"})
    assert result["files"] == ["execute.py"] and path.stat().st_mode & 0o777 == 0o755
    with pytest.raises(ValueError, match="obsolete"):
        apply_edits(store, "project", [edit], {"execute.py"})
    source = path.read_text()
    edit.update({"hash": digest(source), "old": "missing"})
    with pytest.raises(ValueError, match="ambiguous"):
        apply_edits(store, "project", [edit], {"execute.py"})
    assert path.read_text() == source


def test_versioned_config_secret_privacy_and_delegation_off(env, monkeypatch):
    from codex_economy.config import load, update, secret
    from codex_economy.delegation import delegate

    root, store, engine = env
    config = load(store)
    assert not config["delegation"]["enabled"]
    with pytest.raises(ValueError):
        update(store, {"unexpected": True})
    update(store, {"context_bytes": 4096, "auxiliary": {"mode": "off"}})
    assert load(store)["context_bytes"] == 4096
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    value = "controlled-unit-test-secret-123"
    status = secret(store, value)
    assert status["available"] and value not in str(status)
    assert (store.home / "typesafe.key").stat().st_mode & 0o777 == 0o600
    secret(store, remove=True)
    assert not secret(store)["available"]
    with pytest.raises(ValueError, match="off"):
        delegate(store, "project", [])


def test_full_packet_budget_no_match_and_graph_refinement(env):
    root, store, engine = env
    (root / "a.py").write_text("from b import dependency\ndef function():\n return dependency()\n")
    (root / "b.py").write_text("def dependency():\n return 42\n")
    engine.index("project")
    for budget in (128, 512, 2000, 6000):
        packet = engine.context("project", "function", budget, "hybrid")
        assert len(json.dumps(packet, ensure_ascii=False).encode()) <= budget
        if budget >= 2000:
            assert packet["evidence"]
        for evidence in packet["evidence"]:
            assert evidence["source"] in (root / evidence["path"]).read_text()
    result = engine.context("project", "zzzzzzzzzzzzzzzzzz", 2000, "hybrid")
    assert result["insufficient"]
    from codex_economy.retrieval import refine

    refinement = refine(engine, "project", "function", "dependency implementation", 6000)
    assert refinement["new_evidence"]


def test_branches_linked_worktrees_and_snapshot_invalidation(env, tmp_path):
    import subprocess

    root, store, engine = env

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)

    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@localhost")
    (root / "value.py").write_text("VALUE=1\n")
    git("add", "value.py")
    git("commit", "-qm", "one")
    engine.index("project")
    git("checkout", "-qb", "second")
    (root / "value.py").write_text("VALUE=2\n")
    git("commit", "-qam", "two")
    assert engine.status("project")["state"] == "stale"
    engine.index("project")
    linked = tmp_path / "linked"
    git("worktree", "add", "--detach", str(linked), "HEAD~1")
    engine.register("linked", linked)
    engine.index("linked")
    assert "VALUE=1" in engine.read("linked", "value.py")["source"]
    assert "VALUE=2" in engine.read("project", "value.py")["source"]
    git("checkout", "-q", "HEAD~1")
    assert engine.status("project")["state"] == "stale"


def test_cancelled_index_rolls_back_and_can_restart(tmp_path):
    import subprocess

    script = """
import time
from codex_economy.store import Store
from codex_economy.engine import Engine
from codex_economy import adapters
from pathlib import Path
store=Store();engine=Engine(store);engine.register('cancel',Path.cwd());engine.index('cancel')
original=adapters.extract
def slow(path,source):
 Path('started.marker').write_text('started')
 time.sleep(30)
 return original(path,source)
adapters.extract=slow
engine.index('cancel',force=True)
"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "source.py").write_text("def source():\n return 1\n")
    home = tmp_path / "state"
    env = {**os.environ, "CE_HOME": str(home)}
    process = subprocess.Popen(
        [sys.executable, "-c", script], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        deadline = time.monotonic() + 10
        while not (root / "started.marker").exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert (root / "started.marker").exists()
        import signal

        process.send_signal(signal.SIGINT)
        process.communicate(timeout=5)
        with Store(home) as store:
            assert store.integrity()["sqlite"] == "ok"
            assert store.rows("SELECT count(*) AS n FROM snapshots")[0]["n"] == 1
            (root / "started.marker").unlink()
            assert Engine(store).index("cancel")["state"] == "ready"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_bundle_restore_configuration_checksum_and_traversal(env, tmp_path):
    from codex_economy.backup import bundle, restore_bundle
    from codex_economy.config import update, load
    import tarfile
    import io

    root, store, engine = env
    update(store, {"context_bytes": 4096})
    file = tmp_path / "backup.tgz"
    bundle(store, file)
    destination = tmp_path / "restored"
    result = restore_bundle(destination, file)
    assert result["configuration_restored"]
    with Store(destination) as restored:
        assert load(restored)["context_bytes"] == 4096
    malicious = tmp_path / "malicious.tgz"
    with tarfile.open(malicious, "w:gz") as archive:
        member = tarfile.TarInfo("../outside")
        member.size = 3
        archive.addfile(member, io.BytesIO(b"bad"))
    with pytest.raises(ValueError, match="member"):
        restore_bundle(tmp_path / "rejected", malicious)
    assert not (tmp_path / "outside").exists()


def test_observed_python_trace_is_real_and_snapshot_bound(env):
    from codex_economy.traces import trace

    root, store, engine = env
    (root / "library.py").write_text("def twice(n):\n return n*2\n")
    (root / "main.py").write_text("from library import twice\nassert twice(21)==42\n")
    engine.index("project")
    observed = trace(store, "project", "main.py")
    assert observed["run"]["code"] == 0 and observed["observed"]
    assert any(
        r["source"] == "main.py" and r["target"] == "library.py"
        for r in store.rows("SELECT source,target FROM edges WHERE status='observed'")
    )
    assert engine.capabilities("project")["dynamic_graph"]
    (root / "library.py").write_text("def twice(n):\n return n*3\n")
    engine.index("project")
    assert not engine.capabilities("project")["dynamic_graph"]


def test_jev_mixed_batch_cache_http_failures_and_concurrency(env, monkeypatch):
    import urllib.request
    import urllib.error
    import fcntl
    from codex_economy.providers import Jev

    root, store, engine = env
    monkeypatch.setenv("CE_JEV_ALLOW_PAID", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "controlled-fake-key")
    monkeypatch.setenv("CE_JEV_MODEL", "jev-controlled-version")
    questions = {
        "action": {"type": "choice", "instructions": "Which action?", "criteria": {"read": "read", "test": "test"}},
        "relevance": {"type": "score", "instructions": "relevance", "criteria": ["none", "direct"]},
        "repeat": {"type": "noul", "instructions": "repeated?"},
    }
    valid = {
        "model": "jev-controlled-version",
        "answers": {
            "action": {"type": "choice", "choice": "read", "confidence": 1, "probabilities": {"read": 1, "test": 0}},
            "relevance": {"type": "score", "score": 1, "confidence": 1, "probabilities": {"0": 0, "1": 1}},
            "repeat": {"type": "noul", "noul": 0.1},
        },
        "usage": {"input_tokens": 12, "output_tokens": 3},
    }
    calls = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, n):
            return json.dumps(valid).encode()

    def request(*args, **kwargs):
        calls.append(1)
        return Reply()

    monkeypatch.setattr(urllib.request, "urlopen", request)
    provider = Jev(store)
    assert provider.ask("unit state", questions, True)["mode"] == "jev"
    cached = provider.ask("unit state", questions, True)
    assert cached["mode"] == "jev-cache" and cached["requests"] == 0 and len(calls) == 1
    assert "controlled-fake-key" not in str(store.rows("SELECT payload FROM events"))

    def http_error(*args, **kwargs):
        raise urllib.error.HTTPError("https://api.typesafe.ai/v1/systemone", 429, "limited", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", http_error)
    assert provider.ask("different state", questions, True)["error"] == "rate_limit"
    descriptors = []
    try:
        for i in range(2):
            fd = os.open(store.home / f".jev-slot-{i}", os.O_RDWR | os.O_CREAT, 0o600)
            descriptors.append(fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert provider.ask("new input", questions, True)["error"] == "concurrency_limit"
    finally:
        for fd in descriptors:
            os.close(fd)


def test_verified_task_cache_reuses_evidence_but_requires_new_checks(env):
    from codex_economy.continuity import accept, cached_result

    root, store, engine = env
    (root / "test_script.py").write_text("assert 3*3==9\n")
    engine.index("project")
    sid = Sessions(store).create("project", "verify multiplication", "test passes")["session"]
    run = Runner(store).run("project", [sys.executable, "test_script.py"])
    accept(store, sid, [run["run"]])
    result = cached_result(store, "project", "verify multiplication", "test passes")
    assert result["cache_hit"] and result["codex_requests"] == 0 and not result["accepted"]
    with pytest.raises(ValueError):
        Sessions(store).update(result["session"], {"checks": [{"run": run["run"]}]}, "accepted")
    (root / "test_script.py").write_text("assert 3*3==10\n")
    engine.index("project")
    assert cached_result(store, "project", "verify multiplication", "test passes") is None


def test_benchmark_reconciles_interrupted_workspace_without_erasing(env, tmp_path):
    from codex_economy.benchmark import benchmark

    root, store, engine = env
    source = tmp_path / "template"
    source.mkdir()
    (source / "code.py").write_text("value=1\n")
    output = tmp_path / "benchmark"
    workspace = output / "workspaces/task-0-A"
    workspace.mkdir(parents=True)
    (workspace / "kept.py").write_text("interrupted work")
    manifest = {
        "output": str(output),
        "tasks": [
            {
                "id": "task",
                "family": "python",
                "root": str(source),
                "objective": "change value",
                "acceptance": "check",
                "verify": ["true"],
                "protected": [],
                "target": "code.py",
            }
        ],
        "repetitions": 1,
        "arms": ["A"],
        "model": "unused-controlled-test",
        "effort": "low",
    }
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps(manifest))
    report = benchmark(store, file, execute=True)
    assert not report["groups"]["A"]["accepted"] and not report["usage_complete"]
    assert (workspace / "kept.py").read_text() == "interrupted work"
    assert json.loads((output / "results.jsonl").read_text())["recovered"]
    assert benchmark(store, file)["pending"] == 0


def test_extension_removal_rejects_symlinked_parent(env, tmp_path):
    root, store, engine = env
    setup(store, "project")
    (root / ".agents").rename(root / "moved")
    (root / ".agents").symlink_to(root / "moved", target_is_directory=True)
    with pytest.raises(OSError):
        setup(store, "project", remove=True)
    assert (root / "moved/skills/codex-economy/SKILL.md").is_file()


def test_blocked_session_cannot_be_accepted(env):
    root, store, engine = env
    (root / "check.py").write_text("assert True\n")
    engine.index("project")
    sid = Sessions(store).create("project", "objective", "acceptance")["session"]
    run = Runner(store).run("project", [sys.executable, "check.py"])
    Sessions(store).update(sid, {"failures": [{"state": "budget_reached"}]}, "blocked")
    with pytest.raises(ValueError, match="resume successfully"):
        accept(store, sid, [run["run"]])


def test_paid_jev_disabled_by_default_even_with_key(env, monkeypatch):
    from codex_economy.providers import Jev

    _, store, _ = env
    monkeypatch.setenv("TYPESAFE_API_KEY", "fake-controlled-key")
    monkeypatch.delenv("CE_JEV_ALLOW_PAID", raising=False)
    result = Jev(store).ask("synthetic", {"q": {"type": "noul", "instructions": "Does it match?"}}, True)
    assert result == {"mode": "local-fallback", "error": "paid_inference_not_authorized", "requests": 0}


def test_project_extension_idempotent_hooks_remain_removable(env):
    root, store, _ = env
    setup(store, "project", hooks=True)
    assert (root / ".codex/config.toml").read_text() == "# codex-economy project hook discovery layer\n"
    setup(store, "project")
    assert (root / ".codex/hooks.json").exists()
    setup(store, "project", remove=True)
    assert not (root / ".codex/hooks.json").exists()
    assert not (root / ".codex/config.toml").exists()


def test_project_extension_preserves_existing_config(env):
    root, store, _engine = env
    config = root / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text("model = 'existing'\n")
    setup(store, "project", hooks=True)
    setup(store, "project", remove=True)
    assert config.read_text() == "model = 'existing'\n"
