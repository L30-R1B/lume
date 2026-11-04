import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import adapters
from .security import DEFAULT_POLICY, digest, excluded, read_source


class Engine:
    def __init__(self, store):
        self.s = store
        self.db = store.db

    def register(self, name, root):
        if not re.fullmatch(r"[\w.-]{1,80}", name):
            raise ValueError("Project name must contain 1–80 letters, digits, dots, hyphens or underscores")
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Project root must be a directory")
        with self.db:
            self.db.execute(
                "INSERT INTO projects(name,root,policy) VALUES(?,?,?) ON CONFLICT(name) DO NOTHING",
                (name, str(root), json.dumps(DEFAULT_POLICY)),
            )
        p = self.s.project(name)
        if p["root"] != str(root):
            raise ValueError("Name already registered with another root")
        return p

    def scan(self, p):
        files = {}
        omissions = []
        root = p["root"]
        for directory, dirs, names in os.walk(root, followlinks=False):
            rel = Path(directory).relative_to(root)
            dirs[:] = sorted(
                d for d in dirs if not excluded(str(rel / d), p["policy"]) and not Path(directory, d).is_symlink()
            )
            for name in sorted(names):
                path = str(rel / name)
                if excluded(path, p["policy"]):
                    continue
                try:
                    source, h = read_source(root, path, p["policy"])
                    files[path] = (source, h)
                except (OSError, ValueError, UnicodeError) as e:
                    omissions.append({"path": path, "reason": str(e)})
        return files, omissions

    def fingerprint(self, p, files):
        try:
            proc = subprocess.run(
                ["git", "-C", p["root"], "rev-parse", "HEAD"], check=False, capture_output=True, text=True, timeout=5
            )
            head = proc.stdout.strip() if proc.returncode == 0 else "unversioned"
        except (OSError, subprocess.TimeoutExpired):
            head = "unavailable"
        toolchain = {}
        import importlib.metadata

        for package in (
            "tree-sitter",
            "tree-sitter-javascript",
            "tree-sitter-typescript",
            "tree-sitter-kotlin",
            "libclang",
        ):
            try:
                toolchain[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                toolchain[package] = "missing"
        # Generated compiler configuration is excluded from source inventory but invalidates analysis.
        for relative in ("build/compile_commands.json", "compile_commands.json"):
            file = Path(p["root"]) / relative
            if file.is_file() and not file.is_symlink() and file.stat().st_size <= 10_000_000:
                toolchain[relative] = digest(file.read_bytes())
        return digest(
            json.dumps(
                [
                    adapters.VERSION,
                    toolchain,
                    p["root"],
                    p["policy"],
                    head,
                    [(k, v[1]) for k, v in sorted(files.items())],
                ],
                sort_keys=True,
            )
        )

    def index(self, name, force=False):
        p = self.s.project(name)
        start = time.monotonic()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prior = self.s.rows("SELECT details FROM snapshots WHERE project=? ORDER BY id DESC LIMIT 1", (p["id"],))
            if prior and json.loads(prior[0]["details"]).get("extractor_version") != adapters.VERSION:
                force = True
            files, omissions = self.scan(p)
            fingerprint = self.fingerprint(p, files)
            snap = self.db.execute(
                "INSERT INTO snapshots(project,fingerprint,created,state,details) VALUES(?,?,?,?,?)",
                (p["id"], fingerprint, time.time(), "building", "{}"),
            ).lastrowid
            previous = {r["path"]: r for r in self.s.rows("SELECT * FROM files WHERE project=?", (p["id"],))}
            changed = 0
            facts = {}
            for path, (source, h) in files.items():
                key = digest(adapters.VERSION + path + h)
                cached = self.s.rows("SELECT value FROM cache WHERE namespace='extract' AND key=?", (key,))
                if cached and not force:
                    fact = json.loads(cached[0]["value"])
                else:
                    fact = adapters.extract(path, source)
                    self.db.execute(
                        "INSERT OR REPLACE INTO cache VALUES(?,?,?,NULL)", ("extract", key, json.dumps(fact))
                    )
                facts[path] = fact
                if path not in previous:
                    renames = [old for old, row in previous.items() if old not in files and row["hash"] == h]
                    if len(renames) == 1:
                        old = renames[0]
                        self.db.execute("UPDATE files SET path=? WHERE id=?", (path, previous[old]["id"]))
                        previous.pop(old)
                if force or path not in previous or previous[path]["hash"] != h:
                    changed += 1
                    self.db.execute(
                        "INSERT INTO files(project,path,hash,source,adapter,snapshot) VALUES(?,?,?,?,?,?) ON CONFLICT(project,path) DO UPDATE SET hash=excluded.hash,source=excluded.source,adapter=excluded.adapter,snapshot=excluded.snapshot",
                        (p["id"], path, h, source, fact["adapter"], snap),
                    )
                    fid = self.db.execute(
                        "SELECT id FROM files WHERE project=? AND path=?", (p["id"], path)
                    ).fetchone()[0]
                    self.db.execute("DELETE FROM symbols WHERE file=?", (fid,))
                    self.db.execute("DELETE FROM search WHERE project=? AND file=?", (p["id"], fid))
                    self.db.execute("INSERT INTO search VALUES(?,?,?,?)", (path, source, p["id"], fid))
                    occurrences = {}
                    for symbol, kind, a, b, status in fact["symbols"]:
                        identity = (kind, symbol)
                        occurrences[identity] = occurrences.get(identity, 0) + 1
                        sid = digest(f"{fid}:{kind}:{symbol}:{occurrences[identity]}")
                        self.db.execute(
                            "INSERT OR REPLACE INTO symbols VALUES(?,?,?,?,?,?,?,?)",
                            (sid, fid, symbol, kind, a, b, adapters.VERSION + ":" + fact["adapter"], status),
                        )
                self.db.execute("UPDATE files SET snapshot=? WHERE project=? AND path=?", (snap, p["id"], path))
            deleted = set(previous) - set(files)
            for path in deleted:
                fid = previous[path]["id"]
                self.db.execute("DELETE FROM search WHERE project=? AND file=?", (p["id"], fid))
                self.db.execute("DELETE FROM files WHERE id=?", (fid,))
            self.db.execute("DELETE FROM edges WHERE project=?", (p["id"],))
            names = {}
            for row in self.s.rows(
                "SELECT s.name,f.path FROM symbols s JOIN files f ON f.id=s.file WHERE f.project=?", (p["id"],)
            ):
                names.setdefault(row["name"], []).append(row["path"])
            # Rebuild derived edges for ALL files: dependencies and aliases invalidate relations.
            for path, fact in facts.items():
                for target, kind, status in fact["relations"]:
                    targets = names.get(target, [])
                    if kind == "imports":
                        spec = re.findall(r'[\'"]([^\'"]+)[\'"]', target)
                        module = spec[-1] if spec else target.replace(".", "/")
                        base = str(Path(path).parent / module) if module.startswith(".") else module
                        base = os.path.normpath(base)
                        matches = [
                            candidate
                            for candidate in files
                            if candidate
                            in (
                                base,
                                base + ".py",
                                base + ".ts",
                                base + ".tsx",
                                base + ".js",
                                base + "/index.ts",
                                base + "/__init__.py",
                            )
                        ]
                        targets = matches
                    for dest in targets or [target]:
                        self.db.execute(
                            "INSERT INTO edges(project,source,target,kind,origin,status,snapshot) VALUES(?,?,?,?,?,?,?)",
                            (p["id"], path, dest, kind, adapters.VERSION, status, snap),
                        )
            # Detect concurrent external edits before publishing the snapshot.
            verify, _ = self.scan(p)
            if self.fingerprint(p, verify) != fingerprint:
                raise ValueError("Workspace changed during index; retry required")
            warnings = [{"path": k, "warnings": v["warnings"]} for k, v in facts.items() if v["warnings"]]
            state = "partial" if omissions or warnings else "ready"
            details = {
                "extractor_version": adapters.VERSION,
                "files": len(files),
                "changed": changed,
                "deleted": len(deleted),
                "omissions": omissions,
                "warnings": warnings,
                "seconds": time.monotonic() - start,
                "commands": adapters.commands({k: v[0] for k, v in files.items()}),
            }
            self.db.execute("UPDATE snapshots SET state=?,details=? WHERE id=?", (state, json.dumps(details), snap))
            self.db.commit()
            return {"snapshot": snap, "fingerprint": fingerprint, "state": state, **details}
        except BaseException:
            self.db.rollback()
            raise

    def status(self, name):
        p = self.s.project(name)
        rows = self.s.rows("SELECT * FROM snapshots WHERE project=? ORDER BY id DESC LIMIT 1", (p["id"],))
        if not rows:
            return {"state": "missing"}
        s = rows[0]
        files, omissions = self.scan(p)
        if s["fingerprint"] != self.fingerprint(p, files):
            s["state"] = "stale"
        s["details"] = json.loads(s["details"])
        s["current_omissions"] = omissions
        return s

    def require_current(self, name):
        status = self.status(name)
        if status["state"] in ("missing", "stale", "building"):
            raise ValueError("Index " + status["state"] + "; run ce index " + name)
        return status

    def read(self, name, path, start=1, end=200, expected_hash=None):
        if start < 1 or end < start or end - start > 2000:
            raise ValueError("Use a valid interval of at most 2001 lines")
        p = self.s.project(name)
        source, h = read_source(p["root"], path, p["policy"])
        if expected_hash and expected_hash != h:
            raise ValueError("Hash mismatch; source changed, refresh evidence")
        lines = source.splitlines(keepends=True)
        return {
            "path": path,
            "hash": h,
            "start": start,
            "end": min(end, len(lines)),
            "source": "".join(lines[start - 1 : end]),
            "omitted_before": min(start - 1, len(lines)),
            "omitted_after": max(0, len(lines) - end),
        }

    def search(self, name, query, limit=20, mode="lexical"):
        if not query or len(query) > 2000 or not 1 <= limit <= 200:
            raise ValueError("Query must be 1–2000 characters; limit 1–200")
        if mode not in ("lexical", "structural", "hybrid", "full", "assisted"):
            raise ValueError("Unsupported retrieval mode")
        status = self.require_current(name)
        p = self.s.project(name)
        terms = re.findall(r"\w+", query)[:24]
        fts = " OR ".join('"' + t + '"' for t in terms)
        rows = self.s.rows(
            "SELECT f.path,f.hash,f.source,f.id,bm25(search) AS rank FROM search JOIN files f ON f.id=search.file WHERE search MATCH ? AND f.project=? ORDER BY rank LIMIT ?",
            (fts or '""', p["id"], limit),
        )
        # Exact literals outrank token matches without interpreting SQL or FTS syntax.
        rows.sort(key=lambda r: (query not in r["source"] and query not in r["path"], r["rank"]))
        signature = digest(json.dumps([p["id"], status["fingerprint"], query, mode]))
        previous_queries = self.s.rows(
            "SELECT count(*) AS n FROM events WHERE kind='retrieval' AND payload=?", (signature,)
        )[0]["n"]
        with self.db:
            self.db.execute(
                "INSERT INTO events(created,kind,payload) VALUES(?,?,?)", (time.time(), "retrieval", signature)
            )
        effective = mode
        if mode in ("hybrid", "assisted"):
            from .providers import LocalReranker

            candidates = self.s.rows(
                "SELECT path,hash,source,id FROM files WHERE project=? ORDER BY path LIMIT 500", (p["id"],)
            )
            semantic = LocalReranker().rank(query, candidates)
            rank = {r["path"]: 1 / (60 + i) for i, r in enumerate(rows)}
            by = {r["path"]: r for r in rows}
            for i, r in enumerate(semantic):
                rank[r["path"]] = rank.get(r["path"], 0) + 1 / (60 + i)
                by[r["path"]] = r
            rows = [by[k] for k in sorted(rank, key=rank.get, reverse=True)[:limit]]
        if mode == "structural":
            symbols = self.s.rows(
                "SELECT f.path,f.hash,f.source,f.id,s.start,s.end,s.name FROM symbols s JOIN files f ON s.file=f.id WHERE f.project=? AND s.name LIKE ? LIMIT ?",
                (p["id"], "%" + query + "%", limit),
            )
            rows = symbols or rows
        if mode == "assisted":
            from .providers import Jev

            rows, meta = Jev(self.s).rank(p, query, rows)
            effective = meta
        for r in rows:
            if "start" not in r:
                lines = r["source"].splitlines()
                match = next(
                    (
                        i
                        for i, line in enumerate(lines)
                        if query.casefold() in line.casefold() or any(t.casefold() in line.casefold() for t in terms)
                    ),
                    0,
                )
                syms = self.s.rows(
                    "SELECT start,end FROM symbols WHERE file=? AND start<=? AND end>=? ORDER BY end-start LIMIT 1",
                    (r["id"], match + 1, match + 1),
                )
                r["start"], r["end"] = (
                    (syms[0]["start"], syms[0]["end"]) if syms else (max(1, match - 5), min(len(lines), match + 16))
                )
            r.pop("source", None)
        return {
            "snapshot": status["id"],
            "repeated_investigation": previous_queries > 0,
            "previous_equivalent_queries": previous_queries,
            "state": status["state"],
            "effective_mode": effective,
            "candidates": rows,
            "candidate_limit": limit,
            "insufficient": not rows,
        }

    def graph(self, name, path, direction="both", kind=None, depth=1, limit=30):
        self.require_current(name)
        if direction not in ("both", "in", "out") or not 1 <= depth <= 4 or not 1 <= limit <= 200:
            raise ValueError("Graph direction both/in/out, depth 1–4, limit 1–200")
        p = self.s.project(name)
        frontier = {path}
        visited = set()
        results = {}
        for _ in range(depth):
            nxt = set()
            for node in sorted(frontier - visited):
                visited.add(node)
                query = "SELECT * FROM edges WHERE project=? AND "
                cond = {"both": "(source=? OR target=?)", "in": "target=?", "out": "source=?"}[direction]
                args = [p["id"], node] + ([node] if direction == "both" else [])
                if kind:
                    cond += " AND kind=?"
                    args.append(kind)
                for row in self.s.rows(query + cond + " LIMIT ?", (*args, limit + 1)):
                    results[row["id"]] = row
                    nxt.update((row["source"], row["target"]))
                    if len(results) > limit:
                        return {"edges": list(results.values())[:limit], "omitted": True}
            frontier = nxt
        return {"edges": list(results.values()), "omitted": False}

    def context(self, name, query, budget=4000, mode="hybrid"):
        if not 128 <= budget <= 100000:
            raise ValueError("Context byte budget must be 128–100000")
        found = self.search(name, query, mode=mode)
        evidence = []
        omitted = []
        for row in found["candidates"]:
            a, b = row["start"], row["end"]
            if mode == "full":
                a, b = 1, 2001
            if b - a > 2000:
                omitted.append({"path": row["path"], "reason": "symbol exceeds read limit"})
                continue
            item = self.read(name, row["path"], a, b, row["hash"])
            size = len(json.dumps(item, ensure_ascii=False).encode())
            if size <= budget:
                evidence.append(item)
                budget -= size
            else:
                omitted.append({"path": row["path"], "reason": "budget"})
        return {
            **found,
            "candidates": None,
            "evidence": evidence,
            "omissions": omitted,
            "remaining_source_bytes": budget,
            "budget_scope": "serialized evidence items, excluding envelope; not a token cap",
            "insufficient": not evidence,
        }

    def capabilities(self, name):
        p = self.s.project(name)
        status = self.status(name)
        adapters_used = self.s.rows("SELECT DISTINCT adapter FROM files WHERE project=?", (p["id"],))
        resolved = self.s.rows(
            "SELECT count(*) AS n FROM edges WHERE project=? AND status='resolved_by_tool' AND kind='compiler_reference'",
            (p["id"],),
        )[0]["n"]
        return {
            "project": name,
            "state": status["state"],
            "text": True,
            "structure": [r["adapter"] for r in adapters_used if r["adapter"] != "text"],
            "compiler_references": resolved,
            "semantics_fresh": status["state"] == "ready" and resolved > 0,
            "framework_relations": False,
            "build_test_commands": status.get("details", {}).get("commands", []),
            "dynamic_graph": False,
            "limits": [
                "inferred calls are not resolved references",
                "index refresh discards compiler edges; run semantic again",
                "no universal dynamic path coverage",
            ],
        }

    def map(self, name):
        current = self.require_current(name)
        p = self.s.project(name)
        return {
            "snapshot": current["id"],
            "fingerprint": current["fingerprint"],
            "files": self.s.rows(
                "SELECT f.path,f.hash,f.adapter,s.name,s.kind,s.start,s.end,s.origin,s.status FROM files f LEFT JOIN symbols s ON s.file=f.id WHERE f.project=? ORDER BY f.path,s.start LIMIT 1000",
                (p["id"],),
            ),
            "limit": 1000,
            "description": "deterministic hierarchy of paths and original symbol locations; no generated summaries",
        }
