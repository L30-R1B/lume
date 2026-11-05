"""Declared framework/build contracts. Heuristics retain explicit inferred status."""

import json
import re
from pathlib import Path
from defusedxml import ElementTree as XML
from .security import digest

ANDROID = "{http://schemas.android.com/apk/res/android}"


def collect(path, source):
    result = []

    def emit(kind, name, payload=None, status="resolved_by_tool", offset=0, end=None, origin="declared-contract-v1"):
        line = source[:offset].count("\n") + 1
        result.append(
            {
                "path": path,
                "kind": kind,
                "name": str(name),
                "start": line,
                "end": end or line,
                "payload": payload or {},
                "status": status,
                "origin": origin,
            }
        )

    p = Path(path)
    base = p.name
    if p.suffix.lower() in (".md", ".rst", ".txt"):
        emit(
            "document",
            base,
            {
                "topic": next(
                    (x for x in ("architecture", "database", "deploy", "security", "api") if x in path.lower()),
                    "general",
                )
            },
            end=max(1, len(source.splitlines())),
        )
    if p.suffix == ".py":
        for match in re.finditer(r"(?m)^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", source):
            emit("test", match[1], status="resolved_by_tool", offset=match.start(), origin="python-test-convention")
    if p.suffix in (".js", ".jsx", ".ts", ".tsx"):
        for match in re.finditer(r'\b(?:test|it|describe)\s*\(\s*([\'"])(.*?)\1', source):
            emit("test", match[2], status="inferred", offset=match.start(), origin="js-test-convention")
        if "app" in p.parts and base.split(".")[0] in ("page", "route", "layout", "loading", "error", "not-found"):
            parts = list(p.parts)
            idx = parts.index("app")
            route = "/" + "/".join(v for v in parts[idx + 1 : -1] if not v.startswith("(") and not v.startswith("@"))
            methods = re.findall(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b", source)
            directive = re.match(r'\s*[\'"](use client|use server)[\'"]', source)
            emit(
                "next_" + base.split(".")[0],
                route,
                {
                    "methods": methods,
                    "boundary": directive[1] if directive else "server-default",
                    "convention": "app-router",
                },
                status="inferred",
                origin="next-file-convention-v1",
            )
        for match in re.finditer(r'(?m)^\s*[\'"]use server[\'"]', source):
            emit("server_action_boundary", base, status="inferred", offset=match.start())
    if base == "package.json":
        obj = json.loads(source)
        for name, command in obj.get("scripts", {}).items():
            emit(
                "build_command", name, {"argv": ["npm", "run", name], "cwd": str(p.parent), "declared_command": command}
            )
        for group in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in obj.get(group, {}).items():
                emit("dependency", name, {"version": version, "group": group})
    if p.suffix == ".prisma":
        for match in re.finditer(r"(?m)^\s*(model|enum|datasource|generator)\s+(\w+)\s*\{", source):
            start = match.end()
            finish = source.find("}", start)
            if finish < 0:
                finish = len(source)
            body = source[start:finish]
            fields = [
                {"name": m[1], "type": m[2], "attributes": m[3].strip()}
                for m in re.finditer(r"(?m)^\s*(\w+)\s+([\w?\[\]]+)\s*(.*)$", body)
            ]
            emit(
                "prisma_" + match[1],
                match[2],
                {"fields": fields},
                "inferred",
                match.start(),
                source[:finish].count("\n") + 1,
                "prisma-schema-heuristic-v1",
            )
    if p.suffix == ".sql":
        for match in re.finditer(
            r'(?is)\bCREATE\s+(TABLE|VIEW|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?["`]?([\w.]+)', source
        ):
            emit(
                "sql_" + match[1].lower(),
                match[2],
                {"migration": "migration" in path.lower()},
                "inferred",
                match.start(),
                origin="sql-declaration-heuristic-v1",
            )
    if base in ("settings.gradle", "settings.gradle.kts", "build.gradle", "build.gradle.kts"):
        emit("gradle_module", str(p.parent), {"generated": False}, "inferred")
        for match in re.finditer(r'(?:include|includeBuild)\s*\(?\s*[\'"]([^\'"]+)', source):
            emit("gradle_include", match[1], status="inferred", offset=match.start())
        for match in re.finditer(
            r'\b(?:implementation|api|testImplementation|classpath|compileOnly)\s*\(?\s*[\'"]([^\'"]+)', source
        ):
            emit("dependency", match[1], {"ecosystem": "gradle"}, "inferred", match.start())
        for match in re.finditer(r'\b(?:id|kotlin)\s*\(?\s*[\'"]([^\'"]+)', source):
            emit("gradle_plugin", match[1], status="inferred", offset=match.start())
    if base == "AndroidManifest.xml":
        tree = XML.fromstring(source)
        emit("android_manifest", tree.get("package", "manifest"), {"package": tree.get("package")})
        for node in tree.iter():
            if node.tag in ("activity", "service", "receiver", "provider", "uses-permission"):
                emit(
                    "android_" + node.tag,
                    node.get(ANDROID + "name", "unnamed"),
                    {"exported": node.get(ANDROID + "exported"), "attributes": dict(node.attrib)},
                )
    elif p.suffix == ".xml" and "res" in p.parts:
        tree = XML.fromstring(source)
        for node in tree.iter():
            if node.get("name"):
                emit("android_resource", node.get("name"), {"type": node.tag, "value": node.text or ""})
        for match in re.finditer(r"@(?:\+)?(\w+)/(\w+)", source):
            emit("android_resource_reference", match[2], {"type": match[1]}, "inferred", match.start())
    if base in ("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"):
        import yaml

        obj = yaml.safe_load(source)
        if not isinstance(obj, dict):
            raise ValueError("Compose must be a mapping")
        for name, service in (obj.get("services") or {}).items():
            if not isinstance(service, dict):
                raise ValueError("Compose service must be a mapping")
            emit(
                "compose_service",
                name,
                {
                    k: service[k]
                    for k in ("ports", "expose", "networks", "depends_on", "volumes", "healthcheck", "build", "image")
                    if k in service
                },
            )
    if base.startswith("Dockerfile"):
        for match in re.finditer(r"(?im)^(FROM|EXPOSE|HEALTHCHECK|ENTRYPOINT|CMD)\s+(.+)$", source):
            emit("docker_" + match[1].lower(), match[2], status="inferred", offset=match.start())
    if p.suffix in (".yaml", ".yml") and base not in (
        "compose.yml",
        "compose.yaml",
        "docker-compose.yml",
        "docker-compose.yaml",
    ):
        import yaml

        for obj in yaml.safe_load_all(source):
            if isinstance(obj, dict) and obj.get("kind") and obj.get("apiVersion"):
                emit(
                    "infrastructure_manifest",
                    obj.get("metadata", {}).get("name", "unnamed"),
                    {"kind": obj["kind"], "apiVersion": obj["apiVersion"], "spec": obj.get("spec", {})},
                )
    if base == "CMakeLists.txt":
        for match in re.finditer(r"(?i)\b(add_executable|add_library|add_test)\s*\(\s*(?:NAME\s+)?([^\s)]+)", source):
            emit(
                "test" if match[1].lower() == "add_test" else "build_target",
                match[2],
                {"system": "cmake"},
                "inferred",
                match.start(),
            )
    for entity in result:
        json.dumps(entity["payload"])
        entity["id"] = digest(json.dumps([path, entity["kind"], entity["name"], entity["start"]]))
    return result
