"""Useful-context continuity with snapshot-bound task result cache and explicit verification."""

import json
import time
from .security import digest
from .sessions import Sessions
from .engine import Engine


def handoff(store, sid, budget=4000):
    if not 256 <= budget <= 32000:
        raise ValueError("Handoff byte budget must be 256–32000")
    session = Sessions(store).get(sid)
    data = session["payload"]
    project = store.rows("SELECT name FROM projects WHERE id=?", (session["project"],))[0]["name"]
    current = Engine(store).status(project)
    packet = {
        "session": sid,
        "state": session["state"],
        "project": project,
        "current_snapshot": current.get("id"),
        "index_state": current["state"],
        "objective": data["objective"],
        "acceptance": data["acceptance"],
        "next_step": data["next_step"],
        "decisions": data["decisions"][-5:],
        "checks": data["checks"][-3:],
        "affected_files": data["affected_files"],
        "omissions": [],
    }
    for field in ("decisions", "checks", "affected_files"):
        while len(json.dumps(packet).encode()) > budget and packet[field]:
            packet[field].pop(0)
            packet["omissions"].append(field)
    if len(json.dumps(packet).encode()) > budget:
        return {
            "session": sid,
            "insufficient": True,
            "reason": "Required objective/acceptance exceed budget; retrieve session explicitly",
            "next_step": data["next_step"][:200],
        }
    return packet


def policy(store, sid, window_bytes=32000):
    session = Sessions(store).get(sid)
    data = session["payload"]
    serialized = len(json.dumps(data).encode())
    project = store.rows("SELECT name FROM projects WHERE id=?", (session["project"],))[0]["name"]
    status = Engine(store).status(project)
    # Context utility decreases after source changes and after old failures crowd out current state.
    stale = data.get("snapshot") != status.get("id") or status["state"] in ("missing", "stale")
    action = "refresh" if stale else "handoff" if serialized > window_bytes else "continue"
    return {
        "action": action,
        "payload_bytes": serialized,
        "window_bytes": window_bytes,
        "source_changed": stale,
        "history_masking": False,
        "reason": "current evidence invalid"
        if stale
        else "state exceeds useful window"
        if action == "handoff"
        else "state remains useful",
    }


def accept(store, sid, run_ids):
    session = Sessions(store).get(sid)
    if not run_ids:
        raise ValueError("Acceptance requires independent verification run IDs")
    checks = []
    for rid in run_ids:
        rows = store.rows("SELECT id,project,code,state FROM runs WHERE id=?", (rid,))
        if (
            not rows
            or rows[0]["project"] != session["project"]
            or rows[0]["code"] != 0
            or rows[0]["state"] != "completed"
        ):
            raise ValueError("Verification is missing, failed, incomplete or belongs to another project")
        checks.append(rows[0])
    name = store.rows("SELECT name FROM projects WHERE id=?", (session["project"],))[0]["name"]
    status = Engine(store).require_current(name)
    updated = Sessions(store).update(
        sid, {"checks": checks, "snapshot": status["id"], "next_step": "complete"}, "accepted"
    )
    key = digest(json.dumps([session["project"], session["payload"]["objective"], session["payload"]["acceptance"]]))
    store.cache_put("task", key, status["fingerprint"], {"session": sid, "checks": checks}, ttl=86400 * 7)
    with store.db:
        store.db.execute(
            "INSERT OR REPLACE INTO approvals VALUES(?,?,?,?,?)",
            (sid, session["project"], status["fingerprint"], json.dumps(checks), time.time()),
        )
    return updated


def cached_result(store, project, objective, acceptance):
    engine = Engine(store)
    p = store.project(project)
    current = engine.require_current(project)
    key = digest(json.dumps([p["id"], objective, acceptance]))
    cached = store.cache_get("task", key, current["fingerprint"])
    if not cached:
        return None
    try:
        previous = Sessions(store).get(cached["session"])
    except ValueError:
        return None
    if previous["state"] != "accepted":
        return None
    for check in cached["checks"]:
        rid = check.get("id", check.get("run"))
        rows = store.rows("SELECT code,state FROM runs WHERE id=?", (rid,))
        if not rows or rows[0]["code"] != 0 or rows[0]["state"] != "completed":
            return None
    session = Sessions(store).create(project, objective, acceptance)
    Sessions(store).update(
        session["session"],
        {
            "snapshot": current["id"],
            "affected_files": previous["payload"]["affected_files"],
            "decisions": [
                {"reuse_previous_verified_session": cached["session"], "fingerprint": current["fingerprint"]}
            ],
            "next_step": "rerun independent acceptance; cached evidence is not fresh execution",
        },
    )
    return {
        "session": session["session"],
        "state": "cached_evidence",
        "accepted": False,
        "cache_hit": True,
        "source_session": cached["session"],
        "codex_requests": 0,
        "next_step": "independent verification required",
    }
