import json
import os
import selectors
import signal
import subprocess
import time
import uuid

from .security import redact


class Runner:
    def __init__(self, store):
        self.s = store

    def run(self, project, argv, timeout=120, max_bytes=10_000_000, stdin=None):
        if not argv or not all(isinstance(a, str) and "\0" not in a for a in argv):
            raise ValueError("Command must be a nonempty argv array")
        if not 0 < timeout <= 86400 or not 1024 <= max_bytes <= 100_000_000:
            raise ValueError("Invalid timeout or output byte limit")
        p = self.s.project(project)
        rid = uuid.uuid4().hex
        start = time.monotonic()
        with self.s.db:
            self.s.db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)",
                (rid, p["id"], json.dumps([redact(a) for a in argv]), time.time(), None, None, "running", "", "", "{}"),
            )
        process = None
        state = "completed"
        out = {"stdout": bytearray(), "stderr": bytearray()}
        try:
            process = subprocess.Popen(
                argv,
                cwd=p["root"],
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            if stdin is not None:
                process.stdin.write(stdin.encode())
                process.stdin.close()
            sel = selectors.DefaultSelector()
            for label, stream in [("stdout", process.stdout), ("stderr", process.stderr)]:
                os.set_blocking(stream.fileno(), False)
                sel.register(stream, selectors.EVENT_READ, label)
            while sel.get_map():
                if time.monotonic() - start > timeout:
                    state = "timeout"
                    break
                for key, _ in sel.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        sel.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        available = max_bytes - sum(len(v) for v in out.values())
                        out[key.data].extend(chunk[: max(0, available)])
                        if len(chunk) > available:
                            state = "output_limit"
                            break
                if state != "completed":
                    break
            sel.close()
            if state != "completed":
                os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=5)
        except BaseException as e:
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            state = "cancelled" if isinstance(e, (KeyboardInterrupt, SystemExit)) else "spawn_error"
            code = None
            out["stderr"].extend(str(e).encode())
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                self._save(rid, start, code, state, out)
                raise
        return self._save(rid, start, code, state, out)

    def _save(self, rid, start, code, state, out):
        stdout = redact(bytes(out["stdout"]).decode("utf-8", errors="replace"))
        stderr = redact(bytes(out["stderr"]).decode("utf-8", errors="replace"))
        seconds = time.monotonic() - start
        with self.s.db:
            self.s.db.execute(
                "UPDATE runs SET elapsed=?,code=?,state=?,stdout=?,stderr=? WHERE id=?",
                (seconds, code, state, stdout, stderr, rid),
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


def summarize(text, budget=2500):
    if len(text) <= budget:
        return {"text": text, "omitted_lines": 0}
    lines = text.splitlines(keepends=True)
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
    }
