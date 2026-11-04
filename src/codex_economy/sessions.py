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
        data = self.get(sid)["payload"]
        if set(patch) - FIELDS or state not in ("active", "blocked", "accepted", "failed"):
            raise ValueError("Unknown session fields or state")
        if state == "accepted" and not patch.get("checks", data["checks"]):
            raise ValueError("Acceptance requires recorded checks")
        data.update(patch)
        with self.s.db:
            self.s.db.execute(
                "UPDATE sessions SET payload=?,state=?,updated=? WHERE id=?",
                (json.dumps(data), state, time.time(), sid),
            )
        return self.get(sid)
