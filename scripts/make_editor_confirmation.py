import hashlib
import json
import shutil
from pathlib import Path

base = Path(__file__).resolve().parents[1]
fixtures = base / "tests/editor-confirmation-inputs"
tasks = []
ops = {
    "unique": {
        "args": "values",
        "description": "return unique integers preserving first-occurrence order without mutating the input",
        "py": "def unique(values):\n    return list(values)\n",
        "js": "exports.unique = function(values) { return [...values]; };\n",
        "cpp": "inline std::vector<int> unique(std::vector<int> values) { return values; }\n",
        "cases": [([3, 1, 3, 2, 1], [3, 1, 2]), ([], []), ([-1, -1, 0], [-1, 0])],
    },
    "parse_port": {
        "args": "text",
        "description": "accept only a nonempty ASCII decimal digit string representing an integer from 1 to 65535, returning None/null/-1 respectively on invalid input",
        "py": "def parse_port(text):\n    return int(text) if text else None\n",
        "js": "exports.parse_port = function(text) { return Number(text); };\n",
        "cpp": "inline int parse_port(std::string text) { return text.empty() ? -1 : std::atoi(text.c_str()); }\n",
        "cases": [
            ("1", 1),
            ("65535", 65535),
            ("8080", 8080),
            ("0", None),
            ("65536", None),
            ("-1", None),
            ("1x", None),
            ("", None),
            (" 80", None),
            ("１２", None),
            ("١٢", None),
            ("99999999999999999999999999", None),
        ],
    },
    "retry_delay": {
        "args": "attempt, base, cap",
        "description": "implement nonnegative integer exponential backoff min(cap, base * 2**attempt); handle attempts through 60 without overflow and return zero when base or cap is zero",
        "py": 'def retry_delay(attempt, base, cap):\n    raise NotImplementedError("implement backoff")\n',
        "js": 'exports.retry_delay = function(attempt, base, cap) { throw new Error("implement backoff"); };\n',
        "cpp": 'inline long long retry_delay(int attempt, long long base, long long cap) { throw std::logic_error("implement backoff"); }\n',
        "cases": [((0, 2, 100), 2), ((3, 2, 100), 16), ((60, 10, 1000), 1000), ((20, 0, 100), 0), ((2, 3, 0), 0)],
    },
    "merge_intervals": {
        "args": "intervals",
        "description": "implement merging of overlapping closed integer intervals, including equal endpoints; sort output ascending; preserve disjoint intervals and do not mutate the input",
        "py": 'def merge_intervals(intervals):\n    raise NotImplementedError("implement interval merging")\n',
        "js": 'exports.merge_intervals = function(intervals) { throw new Error("implement interval merging"); };\n',
        "cpp": 'inline std::vector<std::vector<int>> merge_intervals(std::vector<std::vector<int>> intervals) { throw std::logic_error("implement interval merging"); }\n',
        "cases": [
            ([[4, 5], [1, 3], [2, 4]], [[1, 5]]),
            ([[1, 2], [4, 6]], [[1, 2], [4, 6]]),
            ([[-3, -1], [-1, 0]], [[-3, 0]]),
            ([], []),
        ],
    },
}


def cpp_literal(value):
    if isinstance(value, list):
        return "{" + ",".join(cpp_literal(v) for v in value) + "}"
    if isinstance(value, str):
        return json.dumps(value)
    if value is None:
        return "-1"
    return str(value)


for family in ("python", "node", "cpp"):
    for name, op in ops.items():
        root = fixtures / (family + "-" + name)
        root.mkdir(parents=True, exist_ok=True)
        if family == "python":
            target = "logic.py"
            (root / target).write_text(op["py"])
            checks = f"from logic import {name}\nimport copy\n"
            for argument, expected in op["cases"]:
                args = argument if name == "retry_delay" else (argument,)
                checks += f"args=copy.deepcopy({args!r})\nbefore=copy.deepcopy(args)\nassert {name}(*args)=={expected!r}\nassert args==before\n"
            (root / "check.py").write_text(checks)
            verify = ["python3", "check.py"]
            protected = ["check.py"]
        elif family == "node":
            target = "logic.js"
            (root / target).write_text(op["js"])
            checks = f'const assert=require("node:assert/strict"); const {{{name}}}=require("./logic");\n'
            for argument, expected in op["cases"]:
                args = list(argument) if name == "retry_delay" else [argument]
                checks += (
                    "{ const args="
                    + json.dumps(args)
                    + "; const before=JSON.stringify(args); assert.deepEqual("
                    + name
                    + "(...args),"
                    + json.dumps(expected)
                    + "); assert.equal(JSON.stringify(args),before); }\n"
                )
            (root / "check.js").write_text(checks)
            verify = ["node", "check.js"]
            protected = ["check.js"]
        else:
            target = "logic.hpp"
            (root / target).write_text(
                "#pragma once\n#include <vector>\n#include <string>\n#include <cstdlib>\n#include <algorithm>\n#include <unordered_set>\n#include <stdexcept>\n#include <limits>\n"
                + op["cpp"]
            )
            checks = '#include <cassert>\n#include "logic.hpp"\nint main(){\n'
            for argument, expected in op["cases"]:
                args = list(argument) if name == "retry_delay" else [argument]
                call = name + "(" + ",".join(cpp_literal(a) for a in args) + ")"
                if isinstance(expected, list):
                    typ = "std::vector<std::vector<int>>" if name == "merge_intervals" else "std::vector<int>"
                    checks += "{ " + typ + " expected=" + cpp_literal(expected) + ";assert(" + call + "==expected); }\n"
                else:
                    checks += "assert(" + call + "==" + cpp_literal(expected) + ");\n"
            (root / "check.cpp").write_text(checks + "}\n")
            (root / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.16)\nproject(validation CXX)\nset(CMAKE_CXX_STANDARD 17)\nenable_testing()\nadd_executable(check check.cpp)\nadd_test(NAME acceptance COMMAND check)\n"
            )
            (root / "verify.py").write_text(
                'import subprocess\nfor argv in [["cmake","-S",".","-B","build"],["cmake","--build","build"],["ctest","--test-dir","build","--output-on-failure"]]:\n subprocess.run(argv,check=True)\n'
            )
            verify = ["python3", "verify.py"]
            protected = ["check.cpp", "CMakeLists.txt", "verify.py"]
        for i in range(8):
            (root / f"document-{i}.md").write_text(
                f"# Unrelated module {i}\nFactory inventory administration background.\n" * 10
            )
        tasks.append(
            {
                "id": family + "-" + name,
                "family": family,
                "root": str(root),
                "objective": f"In {target}, correct or implement {name} to {op['description']}. Only change {target}.",
                "acceptance": "All existing checks pass; no test or unrelated source changes.",
                "target": target,
                "protected": protected,
                "verify": verify,
            }
        )
manifest = {
    "version": 4,
    "phase": "heldout-structured-editor-confirmation",
    "seed": 20261108,
    "model": "gpt-6.1-sol",
    "effort": "high",
    "arms": ["A", "E"],
    "comparison_arm": "E",
    "repetitions": 3,
    "timeout": 180,
    "context_bytes": 6000,
    "output": str(base / "evidence/editor-confirmation"),
    "tasks": tasks,
    "codex_binary": shutil.which("codex"),
    "reference_config_hash": hashlib.sha256((Path.home() / ".codex/config.toml").read_bytes()).hexdigest(),
    "fixture_hashes": {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in fixtures.rglob("*") if f.is_file()},
}
for file in (base / "src/codex_economy").glob("*"):
    if file.suffix in (".py", ".cjs"):
        manifest["fixture_hashes"][str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
(base / "evidence/editor-confirmation-manifest.json").write_text(json.dumps(manifest, indent=2))
