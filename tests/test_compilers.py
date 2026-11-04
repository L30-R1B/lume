import shutil
import subprocess
from pathlib import Path
import pytest
from codex_economy.store import Store
from codex_economy.engine import Engine
from codex_economy.semantic import analyze


def test_typescript_alias_and_changed_definition(tmp_path):
    module = Path.home() / ".local/share/codex-economy/node/node_modules/typescript"
    if not module.exists():
        pytest.skip("TypeScript compiler not installed")
    root = tmp_path / "ts"
    shutil.copytree(Path(__file__).parent / "semantic-fixture", root)
    s = Store(tmp_path / "state")
    e = Engine(s)
    e.register("ts", root)
    e.index("ts")
    result = analyze(s, "ts", "typescript")
    assert result["complete"]
    assert any(
        f["source"] == "main.ts" and f["target"] == "lib/math.ts" and f["name"] == "twice" for f in result["facts"]
    )
    (root / "lib/math.ts").write_text("export function other(x: number) { return x; }")
    e.index("ts")
    result = analyze(s, "ts", "typescript")
    assert not result["complete"] and any("twice" in d["message"] for d in result["diagnostics"])


def test_clang_compilation_database_real_reference(tmp_path):
    root = tmp_path / "cpp"
    root.mkdir()
    (root / "logic.hpp").write_text("inline int twice(int n) { return n*2; }\n")
    (root / "main.cpp").write_text('#include "logic.hpp"\nint main() { return twice(21) == 42 ? 0 : 1; }\n')
    (root / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.16)\nproject(test CXX)\nadd_executable(app main.cpp)\n"
    )
    subprocess.run(
        ["cmake", "-S", str(root), "-B", str(root / "build"), "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
        capture_output=True,
        check=True,
    )
    s = Store(tmp_path / "state")
    e = Engine(s)
    e.register("cpp", root)
    e.index("cpp")
    result = analyze(s, "cpp", "clang")
    assert any(
        f["source"] == "main.cpp" and f["target"] == "logic.hpp" and f["name"] == "twice" for f in result["facts"]
    )
    subprocess.run(["cmake", "--build", str(root / "build")], capture_output=True, check=True)
    assert subprocess.run([str(root / "build/app")], check=False).returncode == 0


def test_compilation_configuration_invalidates_snapshot(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "main.cpp").write_text("int main() { return 0; }")
    (root / "build").mkdir()
    commands = root / "build/compile_commands.json"
    commands.write_text("[]")
    s = Store(tmp_path / "state")
    e = Engine(s)
    e.register("cpp", root)
    e.index("cpp")
    commands.write_text('[{"arguments":["c++","-DCHANGED"]}]')
    assert e.status("cpp")["state"] == "stale"
