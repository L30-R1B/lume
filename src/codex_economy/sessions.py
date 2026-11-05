import json
import time
import uuid

FIELDS = {
    "objective",
    "acceptance",
    "snapshot",
    "affected_files",
    "decisions",
    "hypotheses",
    "checks",
    "failures",
    "next_step",
}


class Sessions:
    def __init__(self, store):
        self.s = store

    def create(self, project, objective, acceptance):
        if not objective or not acceptance:
            raise ValueError("Objective and acceptance are required")
        sid = uuid.uuid4().hex
        p = self.s.project(project)
        data = {
            "objective": objective,
            "acceptance": acceptance,
            "snapshot": None,
            "affected_files": [],
            "decisions": [],
            "hypotheses": [],
            "checks": [],
            "failures": [],
            "next_step": "prepare",
        }
        with self.s.db:
            self.s.db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?)",
                (sid, p["id"], "active", json.dumps(data), time.time(), time.time()),
            )
        return {"session": sid, **data}

    def get(self, sid):
        rows = self.s.rows("SELECT * FROM sessions WHERE id=?", (sid,))
        if not rows:
            raise ValueError("Session not found")
        return {**rows[0], "payload": json.loads(rows[0]["payload"])}

    def update(self, sid, patch, state="active"):
        original = self.get(sid)
        data = original["payload"]
        if set(patch) - FIELDS or state not in ("active", "blocked", "accepted", "failed"):
            raise ValueError("Unknown session fields or state")
        if state == "accepted" and not patch.get("checks", data["checks"]):
            raise ValueError("Acceptance requires recorded checks")
        if state == "accepted" and original["state"] in ("blocked", "failed"):
            raise ValueError("Blocked or failed sessions must resume successfully before acceptance")
        if state == "accepted":
            from .engine import Engine

            name = self.s.rows("SELECT name FROM projects WHERE id=?", (original["project"],))[0]["name"]
            snapshot = Engine(self.s).require_current(name)
            for check in patch.get("checks", data["checks"]):
                rid = check.get("run", check.get("id")) if isinstance(check, dict) else None
                rows = self.s.rows("SELECT * FROM runs WHERE id=?", (rid,))
                if (
                    not rows
                    or rows[0]["project"] != original["project"]
                    or rows[0]["state"] != "completed"
                    or rows[0]["code"] != 0
                    or rows[0]["started"] < original["created"]
                ):
                    raise ValueError("Acceptance requires successful independent runs from this session and project")
                if json.loads(rows[0]["details"]).get("source_fingerprint_after") != snapshot["fingerprint"]:
                    raise ValueError("Verification no longer matches current source; rerun acceptance checks")
        data.update(patch)
        with self.s.db:
            self.s.db.execute(
                "UPDATE sessions SET payload=?,state=?,updated=? WHERE id=?",
                (json.dumps(data), state, time.time(), sid),
            )
        return self.get(sid)
