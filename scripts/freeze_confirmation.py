import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
root = base / "tests/confirmation-inputs"
tasks = []
# Held-out functions differ from exploratory functions and include edge cases.
operations = [
    (
        "distance",
        ["a", "b"],
        "return a + b;",
        [(2, 7, 5), (7, 2, 5), (-3, 2, 5), (4, 4, 0)],
        "the absolute distance between a and b",
    ),
    (
        "minimum",
        ["a", "b"],
        "return a > b ? a : b;",
        [(2, 7, 2), (7, 2, 2), (-3, 2, -3), (4, 4, 4)],
        "the smaller of a and b",
    ),
    (
        "maximum",
        ["a", "b"],
        "return a < b ? a : b;",
        [(2, 7, 7), (7, 2, 7), (-3, 2, 2), (4, 4, 4)],
        "the larger of a and b",
    ),
    ("cube", ["x"], "return x * x;", [(3, 27), (-2, -8), (0, 0), (1, 1)], "x cubed"),
]
for family in ("python", "node", "cpp"):
    for name, args, bug, cases, description in operations:
        directory = root / (family + "-" + name)
        directory.mkdir(parents=True, exist_ok=True)
        if family == "python":
            target = "logic.py"
            verify = ["python3", "check.py"]
            protected = ["check.py"]
            pybug = {
                "distance": "return a + b",
                "minimum": "return max(a,b)",
                "maximum": "return min(a,b)",
                "cube": "return x * x",
            }[name]
            (directory / target).write_text(f"def {name}({', '.join(args)}):\n    {pybug}\n")
            (directory / "check.py").write_text(
                f"from logic import {name}\n"
                + "".join(f"assert {name}({', '.join(str(x) for x in row[:-1])}) == {row[-1]}\n" for row in cases)
            )
        elif family == "node":
            target = "logic.js"
            verify = ["node", "check.js"]
            protected = ["check.js"]
            (directory / target).write_text(f"exports.{name} = ({', '.join(args)}) => {{ {bug} }};\n")
            (directory / "check.js").write_text(
                f'const assert = require("node:assert/strict");\nconst {{{name}}} = require("./logic");\n'
                + "".join(f"assert.equal({name}({', '.join(str(x) for x in row[:-1])}), {row[-1]});\n" for row in cases)
            )
        else:
            target = "logic.hpp"
            verify = ["python3", "verify.py"]
            protected = ["check.cpp", "CMakeLists.txt", "verify.py"]
            (directory / target).write_text(
                f"#pragma once\ninline int {name}({', '.join('int ' + a for a in args)}) {{ {bug} }}\n"
            )
            (directory / "check.cpp").write_text(
                '#include <cassert>\n#include "logic.hpp"\nint main() {\n'
                + "".join(f"assert({name}({', '.join(str(x) for x in row[:-1])}) == {row[-1]});\n" for row in cases)
                + "}\n"
            )
            (directory / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.16)\nproject(check CXX)\nenable_testing()\nadd_executable(check check.cpp)\nadd_test(NAME logic COMMAND check)\n"
            )
            (directory / "verify.py").write_text(
                'import subprocess\nfor cmd in [["cmake","-S",".","-B","build"],["cmake","--build","build"],["ctest","--test-dir","build","--output-on-failure"]]:\n subprocess.run(cmd,check=True)\n'
            )
        for i in range(12):
            (directory / f"notes-{i}.md").write_text(f"# Topic {i}\nUnrelated administration documentation.\n" * 20)
        tasks.append(
            {
                "id": family + "-" + name,
                "family": family,
                "root": str(directory),
                "objective": f"Correct {name} in {target} to compute {description}.",
                "acceptance": "All checks pass; only the target implementation changes; every other source and test remains byte-identical.",
                "target": target,
                "protected": protected,
                "verify": verify,
            }
        )
hashes = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob("*") if f.is_file()}
manifest = {
    "version": 2,
    "phase": "confirmation-held-out-small-functions",
    "seed": 20261105,
    "model": "gpt-6.1-sol",
    "effort": "high",
    "arms": ["A", "B", "C"],
    "repetitions": 3,
    "timeout": 180,
    "context_bytes": 6000,
    "output": str(base / "evidence/confirmation"),
    "fixture_hashes": hashes,
    "tasks": tasks,
}
(base / "evidence/confirmation-manifest.json").write_text(json.dumps(manifest, indent=2))
