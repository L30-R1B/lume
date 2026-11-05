"""Bounded argv execution with nonblocking stdin/output, process-group cleanup and causal logs."""

import json
import hashlib
import base64
import os
import selectors
import signal
import subprocess
import sys
import time
import uuid
from .security import redact


class Runner:
    def __init__(self, store):
        self.s = store

    def run(self, project, argv, timeout=120, max_bytes=None, stdin=None, cwd=".", memory_mb=None, cpu_seconds=None):
        if max_bytes is None:
            from .config import load

            max_bytes = load(self.s)["output_bytes"]
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and "\0" not in a for a in argv):
            raise ValueError("Command must be a nonempty argv array")
        if not 0 < timeout <= 86400 or not 1024 <= max_bytes <= 100_000_000:
            raise ValueError("Invalid timeout or output byte limit")
        p = self.s.project(project)
        directory = (__import__("pathlib").Path(p["root"]) / cwd).resolve(strict=True)
        if not directory.is_relative_to(p["root"]):
            raise ValueError("Working directory outside authorized root")
        if stdin is not None and len(stdin.encode()) > 2_000_000:
            raise ValueError("stdin exceeds 2 MB")
        limits = {}
        if memory_mb is not None:
            if not 32 <= memory_mb <= 65536:
                raise ValueError("memory_mb must be 32–65536")
            limits["memory_mb"] = memory_mb
        if cpu_seconds is not None:
            if not 1 <= cpu_seconds <= 86400:
                raise ValueError("cpu_seconds must be 1–86400")
            limits["cpu_seconds"] = cpu_seconds
        command = argv
        if limits:
            command = [sys.executable, "-m", "codex_economy.resource_exec", json.dumps(limits), "--", *argv]
        from .engine import Engine

        inventory, _ = Engine(self.s).scan(p)
        before_fingerprint = Engine(self.s).fingerprint(p, inventory)
        rid = uuid.uuid4().hex
        start = time.monotonic()
        with self.s.db:
            self.s.db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    rid,
                    p["id"],
                    json.dumps([redact(a) for a in argv]),
                    time.time(),
                    None,
                    None,
                    "running",
                    "",
                    "",
                    json.dumps(
                        {
                            "cwd": cwd,
                            "limits": limits,
                            "owner_pid": os.getpid(),
                            "source_fingerprint_before": before_fingerprint,
                        }
                    ),
                ),
            )
        process = None
        state = "completed"
        out = {"stdout": bytearray(), "stderr": bytearray()}
        code = None
        sel = selectors.DefaultSelector()
        streams = []

        def kill_group():
            if process:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        try:
            process = subprocess.Popen(
                command,
                cwd=directory,
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            details = json.loads(self.s.rows("SELECT details FROM runs WHERE id=?", (rid,))[0]["details"])
            details["child_pid"] = process.pid
            try:
                details["child_start_ticks"] = open(f"/proc/{process.pid}/stat").read().rsplit(")", 1)[1].split()[19]
            except (OSError, IndexError):
                details["child_start_ticks"] = None
            with self.s.db:
                self.s.db.execute("UPDATE runs SET details=? WHERE id=?", (json.dumps(details), rid))
            for label, stream in [("stdout", process.stdout), ("stderr", process.stderr)]:
                streams.append(stream)
                os.set_blocking(stream.fileno(), False)
                sel.register(stream, selectors.EVENT_READ, label)
            pending = memoryview(stdin.encode() if stdin is not None else b"")
            if stdin is not None:
                streams.append(process.stdin)
                os.set_blocking(process.stdin.fileno(), False)
                if pending:
                    sel.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                else:
                    process.stdin.close()
            while sel.get_map() or process.poll() is None:
                if time.monotonic() - start > timeout:
                    state = "timeout"
                    break
                for key, _ in sel.select(0.05):
                    if key.data == "stdin":
                        try:
                            written = os.write(key.fileobj.fileno(), pending[:65536])
                            pending = pending[written:]
                        except BrokenPipeError:
                            pending = pending[:0]
                        if not pending:
                            sel.unregister(key.fileobj)
                            key.fileobj.close()
                        continue
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        sel.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    available = max_bytes - sum(map(len, out.values()))
                    out[key.data].extend(chunk[: max(0, available)])
                    if len(chunk) > available:
                        state = "output_limit"
                        break
                if state != "completed":
                    break
            if state != "completed":
                kill_group()
            code = process.wait(timeout=5)
            kill_group()  # terminate detached descendants in the same group even if parent exited
        except BaseException as error:
            kill_group()
            if process:
                process.wait(timeout=5)
            state = "cancelled" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "spawn_error"
            out["stderr"].extend(str(error).encode())
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                self._save(rid, start, code, state, out)
                raise
        finally:
            sel.close()
            for stream in streams:
                if not stream.closed:
                    stream.close()
        return self._save(rid, start, code, state, out)

    def _save(self, rid, start, code, state, out):
        # surrogateescape round-trips invalid UTF-8 while redacting secrets before persistence.
        retained = {
            stream: redact(bytes(content).decode("utf-8", errors="surrogateescape")).encode(
                "utf-8", errors="surrogateescape"
            )
            for stream, content in out.items()
        }
        stdout = retained["stdout"].decode("utf-8", errors="replace")
        stderr = retained["stderr"].decode("utf-8", errors="replace")
        seconds = time.monotonic() - start
        row = self.s.rows("SELECT project,details FROM runs WHERE id=?", (rid,))[0]
        project_name = self.s.rows("SELECT name FROM projects WHERE id=?", (row["project"],))[0]["name"]
        details = json.loads(row["details"])
        try:
            from .engine import Engine

            project = self.s.project(project_name)
            files, _ = Engine(self.s).scan(project)
            details["source_fingerprint_after"] = Engine(self.s).fingerprint(project, files)
        except (OSError, ValueError):
            details["source_fingerprint_after"] = None
        with self.s.db:
            self.s.db.execute(
                "UPDATE runs SET elapsed=?,code=?,state=?,stdout=?,stderr=?,details=? WHERE id=?",
                (seconds, code, state, stdout, stderr, json.dumps(details), rid),
            )
            self.s.db.executemany(
                "INSERT OR REPLACE INTO run_outputs(run,stream,content,sha256) VALUES(?,?,?,?)",
                [(rid, name, content, hashlib.sha256(content).hexdigest()) for name, content in retained.items()],
            )
        return {
            "run": rid,
            "code": code,
            "state": state,
            "seconds": seconds,
            "stdout": summarize(stdout),
            "stderr": summarize(stderr),
            "full_result": "ce log " + rid,
            "redacted": True,
            "truncated_at_storage_limit": state == "output_limit",
        }


def log_bytes(store, run, stream="stdout", offset=0, length=65536):
    """Return a bounded byte range of the redacted retained output, encoded for JSON."""
    if stream not in ("stdout", "stderr") or not 0 <= offset or not 1 <= length <= 65536:
        raise ValueError("Invalid stream, offset or byte range (maximum 65536 bytes)")
    rows = store.rows(
        "SELECT length(content) AS total,substr(content,?,?) AS part,sha256 FROM run_outputs WHERE run=? AND stream=?",
        (offset + 1, length, run, stream),
    )
    if not rows:
        raise ValueError("Byte output unavailable: run not found or saved before schema 3")
    row = rows[0]
    return {
        "run": run,
        "stream": stream,
        "offset": offset,
        "length": len(row["part"]),
        "total_bytes": row["total"],
        "sha256": row["sha256"],
        "base64": base64.b64encode(row["part"]).decode("ascii"),
        "redacted": True,
        "truncated_at_storage_limit": store.rows("SELECT state FROM runs WHERE id=?", (run,))[0]["state"]
        == "output_limit",
    }


def summarize(text, budget=2500):
    lines = text.splitlines(keepends=True)
    duplicate_groups = {}
    for i, line in enumerate(lines):
        key = line.rstrip("\r\n")
        if key in duplicate_groups:
            duplicate_groups[key]["count"] += 1
        else:
            duplicate_groups[key] = {"count": 1, "first_line": i + 1}
    groups = [{"message": key[:300], **value} for key, value in duplicate_groups.items() if value["count"] > 1][:20]
    structured = None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            structured = {
                k: v
                for k, v in obj.items()
                if k.lower() in ("error", "errors", "failed", "failures", "status", "message", "summary", "exitcode")
            }
    except (ValueError, RecursionError):
        pass
    if len(text) <= budget:
        return {"text": text, "omitted_lines": 0, "repeated": groups, "structured": structured}
    errors = [
        i
        for i, line in enumerate(lines)
        if any(x in line.lower() for x in ("error", "traceback", "exception", "failed", "fatal"))
    ]
    indices = list(range(min(8, len(lines))))
    if errors:
        indices += list(range(max(0, errors[0] - 2), min(len(lines), errors[0] + 15)))
    indices += list(range(max(0, len(lines) - 8), len(lines)))
    selected = []
    used = 0
    for i in sorted(set(indices)):
        if used + len(lines[i]) <= budget:
            selected.append(i)
            used += len(lines[i])
    return {
        "text": "".join(f"{i + 1}: {lines[i]}" for i in selected),
        "omitted_lines": len(lines) - len(selected),
        "selected_lines": [i + 1 for i in selected],
        "repeated": groups,
        "structured": structured,
    }


def batch(store, project, operations):
    """Topological waves run independent operations concurrently, with individual results."""
    from concurrent.futures import ThreadPoolExecutor

    if not isinstance(operations, list) or not 1 <= len(operations) <= 32:
        raise ValueError("Batch requires 1–32 operations")
    by = {op["id"]: op for op in operations}
    if len(by) != len(operations):
        raise ValueError("Duplicate operation id")
    for op in operations:
        if set(op.get("needs", [])) - set(by):
            raise ValueError("Unknown dependency")
    results = {}
    remaining = set(by)
    # Validate DAG before executing anything.
    test = set(remaining)
    while test:
        wave = {key for key in test if not set(by[key].get("needs", [])) & test}
        if not wave:
            raise ValueError("Batch dependency cycle")
        test -= wave

    def execute_one(key):
        op = by[key]
        if any(results[n]["code"] != 0 for n in op.get("needs", [])):
            return {"code": None, "state": "dependency_failed"}
        from .store import Store

        with Store(store.home) as isolated:
            return Runner(isolated).run(project, op["argv"], timeout=op.get("timeout", 120), cwd=op.get("cwd", "."))

    while remaining:
        wave = sorted(key for key in remaining if not set(by[key].get("needs", [])) & remaining)
        with ThreadPoolExecutor(max_workers=min(4, len(wave))) as pool:
            for key, result in zip(wave, pool.map(execute_one, wave)):
                results[key] = result
        remaining -= set(wave)
    return {"results": results, "success": all(r["code"] == 0 for r in results.values())}
