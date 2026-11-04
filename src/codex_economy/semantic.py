"""Opt-in compiler analysis runs outside retrieval. It may load project compiler plugins."""

import json
import os
import subprocess
import time
from pathlib import Path

from .engine import Engine


def analyze(store, name, family):
    p = store.project(name)
    snapshot = Engine(store).require_current(name)
    if family == "typescript":
        module = Path(
            os.environ.get(
                "CE_TYPESCRIPT_PATH", Path.home() / ".local/share/codex-economy/node/node_modules/typescript"
            )
        )
        if not module.exists():
            raise ValueError(
                "Install TypeScript: npm install --prefix ~/.local/share/codex-economy/node typescript; or set CE_TYPESCRIPT_PATH"
            )
        proc = subprocess.run(
            ["node", str(Path(__file__).with_name("typescript.cjs")), str(module), p["root"]],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode:
            raise ValueError("TypeScript compiler analysis failed: " + proc.stderr[:1000])
        result = json.loads(proc.stdout)
    elif family == "clang":
        result = clang_analyze(p)
    else:
        raise ValueError("Compiler semantic adapter not installed for " + family)
    # Reject facts if sources or config changed while the compiler was running.
    if Engine(store).require_current(name)["id"] != snapshot["id"]:
        raise ValueError("Snapshot changed during compiler analysis")
    with store.db:
        store.db.execute("DELETE FROM edges WHERE project=? AND kind='compiler_reference'", (p["id"],))
        for f in result["facts"]:
            store.db.execute(
                "INSERT INTO edges(project,source,target,kind,origin,status,snapshot) VALUES(?,?,?,?,?,?,?)",
                (p["id"], f["source"], f["target"], f["kind"], f["origin"], f["status"], snapshot["id"]),
            )
        store.db.execute(
            "INSERT INTO events(created,kind,payload) VALUES(?,?,?)",
            (time.time(), "semantic", json.dumps({"project": name, **result})),
        )
    return result


def clang_analyze(project):
    """Consume actual compile_commands.json; never execute its shell command."""
    import shlex
    from clang import cindex

    root = Path(project["root"])
    databases = [root / "compile_commands.json", root / "build/compile_commands.json"]
    database = next((f for f in databases if f.is_file()), None)
    if database is None:
        raise ValueError("Generate compile_commands.json using CMake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON")
    entries = json.loads(database.read_text())
    index = cindex.Index.create()
    facts = []
    diagnostics = []
    for entry in entries:
        directory = Path(entry["directory"]).resolve()
        file = (directory / entry["file"]).resolve()
        if not file.is_relative_to(root):
            continue
        argv = entry.get("arguments") or shlex.split(entry["command"])
        args = []
        skip = False
        for arg in argv[1:]:
            if skip:
                skip = False
                continue
            if arg in ("-o", "-MF", "-MT", "-MQ"):
                skip = True
                continue
            if arg == "-c" or (directory / arg).resolve() == file:
                continue
            args.append(arg)
        args += ["-working-directory=" + str(directory)]
        tu = index.parse(str(file), args=args)
        diagnostics.extend(str(d) for d in tu.diagnostics)

        def visit(cursor):
            loc = cursor.location
            if loc.file:
                origin = Path(loc.file.name).resolve()
                if not origin.is_relative_to(root):
                    return
                ref = cursor.referenced
                if ref and ref.location.file:
                    target = Path(ref.location.file.name).resolve()
                    if target.is_relative_to(root):
                        facts.append(
                            {
                                "source": str(origin.relative_to(root)),
                                "target": str(target.relative_to(root)),
                                "name": cursor.spelling,
                                "line": loc.line,
                                "target_line": ref.location.line,
                                "kind": "compiler_reference",
                                "status": "resolved_by_tool",
                                "origin": "libclang",
                            }
                        )
            for child in cursor.get_children():
                visit(child)

        visit(tu.cursor)
    return {"facts": facts, "diagnostics": diagnostics, "complete": not diagnostics, "database": str(database)}
