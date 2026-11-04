import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from codex_economy.engine import Engine
from codex_economy.providers import Jev, LocalReranker
from codex_economy.runner import Runner
from codex_economy.store import Store


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    home = tmp_path / "state"
    monkeypatch.setenv("CE_HOME", str(home))
    store = Store()
    engine = Engine(store)
    engine.register("test", root)
    return root, store, engine


def test_incremental_delete_rename_stale_and_exact_read(env):
    root, s, e = env
    (root / "a.py").write_text("def alpha(x):\n    return x + 1\n")
    first = e.index("test")
    assert first["changed"] == 1
    assert e.index("test")["changed"] == 0
    hit = e.context("test", "alpha")
    assert "return x + 1" in hit["evidence"][0]["source"]
    h = hit["evidence"][0]["hash"]
    (root / "a.py").write_text("def beta(x):\n    return x - 1\n")
    assert e.status("test")["state"] == "stale"
    with pytest.raises(ValueError, match="Hash"):
        e.read("test", "a.py", expected_hash=h)
    with pytest.raises(ValueError, match="stale"):
        e.search("test", "alpha")
    e.index("test")
    (root / "a.py").rename(root / "b.py")
    e.index("test")
    assert e.search("test", "beta")["candidates"][0]["path"] == "b.py"
    (root / "b.py").unlink()
    assert e.index("test")["deleted"] == 1
    assert not e.search("test", "beta")["candidates"]
    assert s.integrity()["sqlite"] == "ok"


def test_boundaries_binary_invalid_utf8_symlinks(env, tmp_path):
    root, s, e = env
    (root / ".env").write_text("SECRET=x")
    (root / "binary").write_bytes(b"x\0y")
    (root / "invalid").write_bytes(b"\xff")
    (root / "outside").symlink_to("/etc/passwd")
    (root / "directory").symlink_to("/etc")
    (root / "ok.py").write_text("x=1")
    result = e.index("test")
    assert result["state"] == "partial"
    for path in ("../passwd", "/etc/passwd", ".env", "outside", "directory/passwd"):
        with pytest.raises((ValueError, OSError)):
            e.read("test", path)
    assert s.rows("SELECT path FROM files") == [{"path": "ok.py"}]


def test_adapters_and_budgets(env):
    root, s, e = env
    examples = {
        "a.py": "def hello():\n return 1\n",
        "a.ts": "export function hello(x: number): number { return x+1; }",
        "a.js": "function hello(x) { return x; }",
        "a.kt": "class Greeting { fun hello(): Int { return 1 } }",
        "a.cpp": "int hello() {return 1;}",
        "a.prisma": "model User {\n id Int @id\n}\n",
        "a.sql": "CREATE TABLE users (id INTEGER PRIMARY KEY);",
        "compose.yaml": "services:\n  web:\n    image: nginx\n    depends_on: [db]\n  db:\n    image: postgres\n",
    }
    for name, source in examples.items():
        (root / name).write_text(source)
    result = e.index("test")
    assert result["files"] == 8
    syms = s.rows("SELECT name,status FROM symbols")
    for name in ("hello", "Greeting", "User", "users", "web"):
        assert any(r["name"] == name for r in syms)
    assert any(r["status"] == "inferred" for r in syms)
    packet = e.context("test", "hello", budget=128)
    assert packet["insufficient"] and packet["omissions"]
    assert e.search("test", "hello", mode="hybrid")["candidates"]
    assert len(e.graph("test", "compose.yaml", limit=1)["edges"]) <= 1


def test_rollback_on_extractor_failure(env, monkeypatch):
    root, s, e = env
    (root / "a.py").write_text("x=1")
    e.index("test")
    (root / "b.py").write_text("x=2")
    from codex_economy import adapters

    def fail(*args):
        raise RuntimeError("interruption")

    monkeypatch.setattr(adapters, "extract", fail)
    with pytest.raises(RuntimeError):
        e.index("test", force=True)
    assert len(s.rows("SELECT * FROM files")) == 1
    assert s.integrity()["sqlite"] == "ok"


def test_concurrent_writers_and_backup(env, tmp_path):
    root, s, _e = env
    (root / "x.py").write_text("def hello():\n return 1\n")

    def index(_):
        return Engine(Store(s.home)).index("test")

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(index, range(4)))
    assert all(r["state"] == "ready" for r in results)
    backup = tmp_path / "backup.sqlite"
    s.backup(backup)
    import sqlite3

    restored = sqlite3.connect(backup)
    assert restored.execute("SELECT count(*) FROM files").fetchone()[0] == 1
    restored.close()


def test_runner_causal_error_log_timeout_arguments(env):
    root, s, _e = env
    code = 'import sys; print("first causal ERROR"); print("repeat\\n"*3000); print("終わり"); sys.exit(7)'
    result = Runner(s).run("test", [sys.executable, "-c", code])
    assert result["code"] == 7 and "causal ERROR" in result["stdout"]["text"]
    log = s.rows("SELECT stdout FROM runs WHERE id=?", (result["run"],))[0]["stdout"]
    assert "終わり" in log and log.count("repeat") == 3000
    timed = Runner(s).run("test", [sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.1)
    assert timed["state"] == "timeout"
    safe = Runner(s).run("test", [sys.executable, "-c", "import sys; print(sys.argv[1])", "$(touch PWNED); hi"])
    assert safe["code"] == 0 and not (root / "PWNED").exists()
    redacted = Runner(s).run("test", [sys.executable, "-c", 'print("password=hunter2")'])
    assert "hunter2" not in str(redacted)


def test_jev_mock_and_local(env, monkeypatch):
    _root, s, _e = env
    j = Jev(s)
    assert j.ask("a", {}, False)["error"] == "external_context_denied"
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert j.ask("a", {}, True)["error"] == "credential_unavailable"
    monkeypatch.setenv("TYPESAFE_API_KEY", "fake-controlled-test-key")
    import urllib.request

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, n):
            return json.dumps(
                {"model": "fake", "answers": {"q": {"type": "noul", "noul": 0.7}}, "usage": {"input_tokens": 10}}
            ).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert j.ask("a", {"q": {"type": "noul", "instructions": "test"}}, True)["mode"] == "jev"
    assert j.ask("a", {"other": {"type": "noul"}}, True)["error"] == "invalid_response"

    def timeout(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(urllib.request, "urlopen", timeout)
    assert j.ask("a", {"q": {"type": "noul"}}, True)["error"] == "timeout"
    ranked = LocalReranker().rank(
        "authentication", [{"path": "a", "source": "authentication credentials"}, {"path": "b", "source": "bananas"}]
    )
    assert ranked[0]["path"] == "a"


def test_mcp_real_stdio(env):
    root, s, e = env
    (root / "a.py").write_text("def answer():\n return 42\n")
    e.index("test")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def client():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "codex_economy.cli", "mcp"], env={**os.environ, "CE_HOME": str(s.home)}
        )
        async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
            await session.initialize()
            catalog = await session.list_tools()
            assert len(catalog.tools) == 6
            result = await session.call_tool(
                "evidence_search", {"project": "test", "query": "answer", "mode": "lexical"}
            )
            assert not result.isError and "return 42" in str(result)

    asyncio.run(client())


def test_rename_preserves_identity_and_line_shift(env):
    root, s, e = env
    (root / "a.py").write_text("def alpha():\n return 1\n")
    e.index("test")
    original = s.rows("SELECT id FROM symbols")[0]["id"]
    fid = s.rows("SELECT id FROM files")[0]["id"]
    (root / "a.py").rename(root / "b.py")
    e.index("test")
    assert s.rows("SELECT id FROM files")[0]["id"] == fid
    assert s.rows("SELECT id FROM symbols")[0]["id"] == original
    (root / "b.py").write_text("\n\ndef alpha():\n return 1\n")
    e.index("test")
    assert s.rows("SELECT id,start FROM symbols")[0] == {"id": original, "start": 3}


def test_prisma_sql_change_real_migration(env):
    import sqlite3

    root, s, e = env
    (root / "schema.prisma").write_text("model User {\n id Int @id\n}\n")
    (root / "migration.sql").write_text("CREATE TABLE users (id INTEGER PRIMARY KEY);")
    e.index("test")
    con = sqlite3.connect(":memory:")
    con.executescript((root / "migration.sql").read_text())
    (root / "migration.sql").write_text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);")
    e.index("test")
    con.close()
    con = sqlite3.connect(":memory:")
    con.executescript((root / "migration.sql").read_text())
    con.execute("INSERT INTO users VALUES(?,?)", (1, "Ana"))
    assert con.execute("SELECT name FROM users").fetchone()[0] == "Ana"
    assert "name TEXT NOT NULL" in e.read("test", "migration.sql")["source"]
    assert s.rows("SELECT status FROM symbols WHERE name='users'")[0]["status"] == "inferred"
    con.close()


def test_repetition_resets_on_source_change_and_map(env):
    root, s, e = env
    (root / "main.py").write_text("def answer():\n return 42\n")
    e.index("test")
    assert not e.search("test", "answer")["repeated_investigation"]
    assert e.search("test", "answer")["repeated_investigation"]
    (root / "main.py").write_text("def answer():\n return 43\n")
    e.index("test")
    assert not e.search("test", "answer")["repeated_investigation"]
    assert e.map("test")["files"][0]["name"] == "answer"
    assert e.capabilities("test")["structure"] == ["python-ast"]
