"""Real build-system model extraction. Project builds are trusted executable code."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from .security import digest

GRADLE_INIT = """
import groovy.json.JsonOutput
gradle.projectsEvaluated {
  def report = gradle.rootProject.allprojects.collect { p ->
    [path:p.path, directory:p.projectDir.canonicalPath,
     plugins:p.plugins.collect { it.class.name },
     tasks:p.tasks.collect { [name:it.path, group:it.group, type:it.class.name] },
     configurations:p.configurations.collect { c ->
       [name:c.name, resolved:({ ->
         if (!c.canBeResolved || !(c.name in ['compileClasspath','runtimeClasspath','debugCompileClasspath','debugRuntimeClasspath'])) return []
         try {
           return c.incoming.resolutionResult.allDependencies.collect { r ->
             if (r instanceof org.gradle.api.artifacts.result.ResolvedDependencyResult) { [requested:r.requested.displayName, selected:r.selected.id.displayName, status:'resolved_by_tool'] }
             else { [requested:r.requested.displayName, status:'unresolved', error:r.failure.message] }
           }
         } catch (Exception ex) { return [[status:'unresolved', error:ex.message]] }
       })(), dependencies:c.dependencies.collect { d ->
         [group:d.group, name:d.name, version:d.version,
          project:(d instanceof org.gradle.api.artifacts.ProjectDependency ? d.path : null)]
       }]
     },
     sourceSets:(p.extensions.findByName('sourceSets')?.collect { s ->
        [name:s.name, directories:s.allSource.srcDirs.collect { [path:it.canonicalPath, generated:it.toPath().startsWith(p.layout.buildDirectory.get().asFile.toPath())] }]
     } ?: [])]
  }
  println('CE_GRADLE_MODEL=' + JsonOutput.toJson(report))
}
"""


def gradle(project):
    root = Path(project["root"])
    configured = os.environ.get("CE_GRADLE_BIN")
    executable = configured or (str(root / "gradlew") if (root / "gradlew").is_file() else shutil.which("gradle"))
    if not executable:
        default = Path.home() / ".local/share/codex-economy/gradle/gradle-9.2.1/bin/gradle"
        if default.is_file():
            executable = str(default)
    if not executable:
        raise ValueError("Gradle unavailable; install Gradle or provide a trusted gradlew/CE_GRADLE_BIN")
    with tempfile.TemporaryDirectory(prefix="ce-gradle-") as folder:
        script = Path(folder) / "model.gradle"
        script.write_text(GRADLE_INIT)
        proc = subprocess.run(
            [executable, "--offline", "--no-daemon", "--max-workers=1", "-q", "-I", str(script), "help"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env={**os.environ, "GRADLE_OPTS": "-Dorg.gradle.jvmargs=-Xmx384m -XX:MaxMetaspaceSize=256m"},
        )
    if proc.returncode:
        raise ValueError("Gradle model failed: " + proc.stderr[-2000:])
    line = next((line for line in proc.stdout.splitlines() if line.startswith("CE_GRADLE_MODEL=")), None)
    if line is None:
        raise ValueError("Gradle did not emit its model")
    return {
        "modules": json.loads(line.split("=", 1)[1]),
        "origin": "gradle-projectsEvaluated",
        "status": "resolved_by_tool",
        "offline": True,
    }


def cmake(project):
    root = Path(project["root"])
    build = root / "build"
    query = build / ".cmake/api/v1/query"
    query.mkdir(parents=True, exist_ok=True)
    (query / "codemodel-v2").touch()
    proc = subprocess.run(
        ["cmake", "-S", str(root), "-B", str(build), "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode:
        raise ValueError("CMake configure failed: " + proc.stderr[-2000:])
    reply = build / ".cmake/api/v1/reply"
    indexes = sorted(reply.glob("index-*.json"))
    if not indexes:
        raise ValueError("CMake File API reply missing")
    index = json.loads(indexes[-1].read_text())
    descriptor = index["reply"]["codemodel-v2"]
    model = json.loads((reply / descriptor["jsonFile"]).read_text())
    targets = []
    for config in model["configurations"]:
        for target in config["targets"]:
            targets.append(json.loads((reply / target["jsonFile"]).read_text()))
    tests = subprocess.run(
        ["ctest", "--test-dir", str(build), "--show-only=json-v1"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "targets": targets,
        "tests": json.loads(tests.stdout).get("tests", []) if tests.returncode == 0 else [],
        "origin": "cmake-file-api-v2/ctest-json-v1",
        "status": "resolved_by_tool",
    }


def analyze_build(store, name, family):
    from .engine import Engine

    project = store.project(name)
    engine = Engine(store)
    before = engine.require_current(name)
    if family == "gradle":
        result = gradle(project)
    elif family == "cmake":
        result = cmake(project)
    else:
        raise ValueError("Build adapter must be gradle or cmake")
    # CMake can regenerate compilation configuration. Refresh first, then bind derived model.
    current = engine.status(name)
    if current["state"] == "stale":
        engine.index(name)
    current = engine.require_current(name)
    entities = []
    if family == "gradle":
        for module in result["modules"]:
            path = Path(module["directory"])
            if not path.is_relative_to(project["root"]):
                continue
            relative = str(path.relative_to(project["root"]))
            entities.append(("build_module", module["path"], relative, module))
            for task in module["tasks"]:
                entities.append(("build_task", task["name"], relative, task))
            for config in module["configurations"]:
                for dependency in config["dependencies"]:
                    entities.append(
                        ("dependency", dependency["name"], relative, {"configuration": config["name"], **dependency})
                    )
    else:
        entities.extend(("build_target", t["name"], "CMakeLists.txt", t) for t in result["targets"])
        entities.extend(("test", t["name"], "CMakeLists.txt", t) for t in result["tests"])
    with store.db:
        store.db.execute("DELETE FROM entities WHERE project=? AND origin=?", (project["id"], result["origin"]))
        for kind, title, path, payload in entities:
            store.db.execute(
                "INSERT OR REPLACE INTO entities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    digest(str(project["id"]) + family + kind + title + path + json.dumps(payload, sort_keys=True)),
                    project["id"],
                    current["id"],
                    path,
                    1,
                    1,
                    kind,
                    title,
                    json.dumps(payload),
                    result["origin"],
                    result["status"],
                ),
            )
    result.update({"snapshot": current["id"], "previous_snapshot": before["id"]})
    return result


def python_semantic(project, store):
    import jedi
    from .engine import Engine

    facts = []
    diagnostics = []
    # Only source inventory allowed by project policy is exposed to the analyzer.
    files, _ = Engine(store).scan(project)
    jp = jedi.Project(project["root"], load_unsafe_extensions=False)
    limited = False
    for relative, (source, _) in files.items():
        if not relative.endswith(".py"):
            continue
        script = jedi.Script(source, path=str(Path(project["root"]) / relative), project=jp)
        diagnostics.extend(str(e) for e in script.get_syntax_errors())
        for reference in script.get_names(all_scopes=True, definitions=False, references=True):
            if len(facts) >= 10000:
                limited = True
                break
            for definition in reference.goto(follow_imports=True, follow_builtin_imports=False):
                if definition.module_path and definition.module_path.is_relative_to(project["root"]):
                    facts.append(
                        {
                            "source": relative,
                            "target": str(definition.module_path.relative_to(project["root"])),
                            "line": reference.line,
                            "target_line": definition.line,
                            "name": reference.name,
                            "kind": "semantic_reference",
                            "status": "resolved_by_tool",
                            "origin": "jedi-" + jedi.__version__,
                        }
                    )
    return {
        "facts": facts,
        "diagnostics": diagnostics,
        "complete": not diagnostics and not limited,
        "limit_reached": limited,
    }
