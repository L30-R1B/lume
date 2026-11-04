"""Adapters report syntactic facts; none claim universal semantic resolution."""

import ast
import importlib
import json
import re
from pathlib import Path

VERSION = "adapters-2"
LANG = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
}
DEFS = {
    "function_declaration",
    "class_declaration",
    "method_definition",
    "interface_declaration",
    "type_alias_declaration",
    "function_definition",
    "struct_specifier",
    "class_specifier",
    "object_declaration",
}


def extract(path, source):
    ext = Path(path).suffix
    symbols = []
    relations = []
    adapter = "text"
    warnings = []
    if ext == ".py":
        adapter = "python-ast"
        try:
            tree = ast.parse(source)
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append((n.name, type(n).__name__, n.lineno, n.end_lineno, "resolved_by_tool"))
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    for a in n.names:
                        relations.append(
                            ((n.module or a.name) if isinstance(n, ast.ImportFrom) else a.name, "imports", "inferred")
                        )
                if isinstance(n, ast.Call):
                    name = ast.unparse(n.func)
                    relations.append((name, "calls", "inferred"))
        except SyntaxError as e:
            warnings.append(str(e))
    elif ext in LANG:
        from tree_sitter import Language, Parser

        lang = LANG[ext]
        adapter = "tree-sitter-" + lang
        module = importlib.import_module("tree_sitter_" + ("typescript" if lang == "tsx" else lang))
        factory = getattr(module, "language_" + lang, None) or module.language
        tree = Parser(Language(factory())).parse(source.encode())
        if tree.root_node.has_error:
            warnings.append("Parse contains ERROR nodes; structure incomplete")
        stack = [tree.root_node]
        data = source.encode()
        while stack:
            n = stack.pop()
            if n.type in DEFS:
                name = n.child_by_field_name("name")
                if name is None and n.type == "function_definition":
                    decl = n.child_by_field_name("declarator")
                    if decl:
                        name = decl.child_by_field_name("declarator") or decl
                if name is None:
                    name = next((c for c in n.children if c.type in ("simple_identifier", "type_identifier")), None)
                if name:
                    symbols.append(
                        (
                            data[name.start_byte : name.end_byte].decode(),
                            n.type,
                            n.start_point.row + 1,
                            n.end_point.row + 1,
                            "resolved_by_tool",
                        )
                    )
            if n.type in ("import_statement", "import_header", "preproc_include"):
                relations.append((data[n.start_byte : n.end_byte].decode(), "imports", "inferred"))
            if n.type in ("call_expression", "call_suffix"):
                fun = n.child_by_field_name("function")
                if fun:
                    relations.append((data[fun.start_byte : fun.end_byte].decode(), "calls", "inferred"))
            stack.extend(reversed(n.children))
    elif ext in (".prisma", ".sql"):
        adapter = "schema-heuristic"
        pattern = r'(?im)^\s*(model|enum|CREATE\s+TABLE|CREATE\s+VIEW)\s+["`]?([\w.]+)'
        for m in re.finditer(pattern, source):
            line = source[: m.start()].count("\n") + 1
            symbols.append((m[2], m[1], line, line, "inferred"))
        for m in re.finditer(r'(?i)(?:REFERENCES|@relation\s*\([^)]*references:)\s*["`]?([\w.]+)', source):
            relations.append((m[1], "schema_reference", "inferred"))
    elif Path(path).name in ("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"):
        import yaml

        adapter = "compose-yaml"
        obj = yaml.safe_load(source)
        if isinstance(obj, dict):
            for name, svc in (obj.get("services") or {}).items():
                symbols.append((name, "service", 1, len(source.splitlines()), "resolved_by_tool"))
                if isinstance(svc, dict):
                    for dep in svc.get("depends_on", []):
                        relations.append((dep, "declared_service_dependency", "resolved_by_tool"))
    return {"adapter": adapter, "symbols": symbols, "relations": relations, "warnings": warnings}


def commands(files):
    result = []
    for path, source in files.items():
        base = Path(path).name
        if base == "package.json":
            try:
                for name in json.loads(source).get("scripts", {}):
                    result.append({"cwd": str(Path(path).parent), "name": name, "argv": ["npm", "run", name]})
            except (ValueError, AttributeError):
                pass
        if base == "CMakeLists.txt":
            result.extend(
                [
                    {
                        "name": "configure",
                        "argv": ["cmake", "-S", ".", "-B", "build", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
                    },
                    {"name": "build", "argv": ["cmake", "--build", "build"]},
                    {"name": "test", "argv": ["ctest", "--test-dir", "build", "--output-on-failure"]},
                ]
            )
        if base in ("build.gradle", "build.gradle.kts"):
            result.append({"name": "gradle-test", "argv": ["./gradlew", "test"]})
        if base in ("pyproject.toml", "pytest.ini"):
            result.append({"name": "python-test", "argv": ["python3", "-m", "pytest"]})
    return result
