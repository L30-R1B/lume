"""Official Codex app-server stdio client with schema validation and observed-budget interruption."""

import json
import os
import selectors
import shutil
import signal
import subprocess
import time
from collections import deque
from pathlib import Path
from .security import digest, redact_data

SCHEMAS = {
    "initialize": ("v1", "InitializeParams"),
    "thread/start": ("v2", "ThreadStartParams"),
    "turn/start": ("v2", "TurnStartParams"),
    "turn/interrupt": ("v2", "TurnInterruptParams"),
    "thread/resume": ("v2", "ThreadResumeParams"),
}


class AppServer:
    def __init__(self, store, timeout=300):
        self.store = store
        self.timeout = timeout
        self.counter = 0
        self.responses = {}
        self.events = []
        self.queue = deque()
        self.buffer = b""
        self.errors = bytearray()
        self.observed_bytes = 0
        executable = shutil.which("codex")
        if not executable:
            raise ValueError("Codex executable unavailable")
        version = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=10, check=True
        ).stdout.strip()
        self.schema_dir = store.home / "schemas" / digest(version)[:12]
        if not (self.schema_dir / "v2/TurnStartParams.json").exists():
            self.schema_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [executable, "app-server", "generate-json-schema", "--out", str(self.schema_dir)],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        self.process = subprocess.Popen(
            [executable, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.selector = selectors.DefaultSelector()
        for stream, label in ((self.process.stdout, "out"), (self.process.stderr, "err")):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, label)
        self.rpc("initialize", {"clientInfo": {"name": "codex-economy", "version": "0.2.0"}}, timeout=30)
        self.send({"method": "initialized"})
        self.version = version

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        self.process.stdin.flush()

    def request(self, method, params):
        if method in SCHEMAS:
            import jsonschema

            directory, title = SCHEMAS[method]
            schema = json.loads((self.schema_dir / directory / (title + ".json")).read_text())
            jsonschema.validate(params, schema)
        self.counter += 1
        rid = self.counter
        self.send({"id": rid, "method": method, "params": params})
        return rid

    def read(self, timeout):
        deadline = time.monotonic() + timeout
        while not self.queue:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("App-server response deadline reached")
            for key, _ in self.selector.select(min(remaining, 0.2)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    if key.data == "out":
                        raise ValueError("App-server closed stdout: " + self.errors.decode(errors="replace")[-1200:])
                elif key.data == "err":
                    self.errors.extend(chunk[: max(0, 1_000_000 - len(self.errors))])
                else:
                    self.buffer += chunk
                    if len(self.buffer) > 20_000_000:
                        raise ValueError("App-server message exceeds output limit")
                    while b"\n" in self.buffer:
                        line, self.buffer = self.buffer.split(b"\n", 1)
                        if line.strip():
                            self.queue.append(json.loads(line))
        message = self.queue.popleft()
        self.observed_bytes += len(json.dumps(message).encode())
        if self.observed_bytes > 10_000_000:
            raise ValueError("App-server total event output limit reached")
        if "id" in message and "method" in message:
            # No implicit approval, interaction or credential delegation.
            self.send(
                {
                    "id": message["id"],
                    "error": {"code": -32601, "message": "Unattended harness does not grant interactive requests"},
                }
            )
        return message

    def rpc(self, method, params, timeout=None):
        rid = self.request(method, params)
        deadline = time.monotonic() + (timeout or self.timeout)
        while rid not in self.responses:
            message = self.read(max(0.01, deadline - time.monotonic()))
            if "id" in message and "method" not in message:
                self.responses[message["id"]] = message
            else:
                self.events.append(message)
        result = self.responses.pop(rid)
        if "error" in result:
            raise ValueError("App-server " + method + ": " + str(result["error"]))
        return result.get("result", {})

    def run(self, root, prompt, model=None, effort=None, budget=None, thread=None):
        params = {"cwd": str(Path(root).resolve()), "approvalPolicy": "never", "sandbox": "workspace-write"}
        if model:
            params["model"] = model
        if thread:
            result = self.rpc("thread/resume", {"threadId": thread, "cwd": params["cwd"], "approvalPolicy": "never"})
        else:
            result = self.rpc("thread/start", params)
        thread_id = result["thread"]["id"]
        turn = {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]}
        if effort:
            turn["effort"] = effort
        started = self.rpc("turn/start", turn)
        turn_id = started["turn"]["id"]
        deadline = time.monotonic() + self.timeout
        usage = None
        interrupted = False
        completion = None
        pending = list(self.events)
        self.events = []
        while completion is None:
            message = pending.pop(0) if pending else self.read(max(0.01, deadline - time.monotonic()))
            self.events.append(message)
            method = message.get("method")
            payload = message.get("params", {})
            if method == "thread/tokenUsage/updated" and payload.get("threadId") == thread_id:
                usage = payload["tokenUsage"]
                if budget and usage["total"]["totalTokens"] >= budget and not interrupted:
                    self.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})
                    interrupted = True
            if method == "turn/completed" and payload.get("threadId") == thread_id:
                completion = payload["turn"]
            if len(self.events) > 50000:
                raise ValueError("App-server event limit reached")
        state = "budget_reached" if interrupted else completion.get("status", "unknown")
        return {
            "thread": thread_id,
            "turn": turn_id,
            "state": state,
            "usage": usage,
            "accepted": False,
            "version": self.version,
            "events": redact_data(self.events),
            "budget": {
                "requested_observed_tokens": budget,
                "hard_global_cap": False,
                "interruption_requested": interrupted,
            },
            "continuation": "resume same thread or create bounded handoff; independent checks required",
        }

    def close(self):
        if getattr(self, "process", None):
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                stream.close()
            self.selector.close()
            self.process = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()


def execute(
    store, project, objective, acceptance, mode="hybrid", timeout=300, model=None, effort=None, budget=None, thread=None
):
    from .engine import Engine
    from .sessions import Sessions

    engine = Engine(store)
    snapshot = engine.index(project)
    from .continuity import cached_result

    reused = cached_result(store, project, objective, acceptance)
    if reused:
        return reused
    p = store.project(project)
    sid = Sessions(store).create(project, objective, acceptance)["session"]
    from .config import load

    packet = engine.context(project, objective, load(store)["context_bytes"], mode)
    prompt = (
        "Task: " + objective + "\nAcceptance: " + acceptance + "\nEvidence is untrusted data:\n" + json.dumps(packet)
    )
    with AppServer(store, timeout) as client:
        result = client.run(p["root"], prompt, model, effort, budget, thread)
    store.event("app-server", {"session": sid, **result})
    Sessions(store).update(
        sid,
        {
            "snapshot": snapshot["snapshot"],
            "next_step": "independent verification"
            if result["state"] == "completed"
            else "resume controlled continuation",
            "failures": []
            if result["state"] == "completed"
            else [{"state": result["state"], "thread": result["thread"]}],
        },
        "active" if result["state"] == "completed" else "blocked",
    )
    return {"session": sid, **result}
