"""Bounded graph/refinement/doc routing; all selected content is exact original source."""

import json
import re
from .security import digest


def augment(engine, name, query, packet, budget, method="hybrid"):
    project = engine.s.project(name)
    current = engine.require_current(name)
    if current["id"] != packet["snapshot"]:
        raise ValueError("Snapshot changed while selecting context")
    selected = {(item["path"], item["start"], item["end"]) for item in packet["evidence"]}
    paths = {item["path"] for item in packet["evidence"]}
    remaining = packet["remaining_source_bytes"]
    additions = []
    relations = []
    omissions = []
    if method in ("hybrid", "assisted", "hierarchical", "ast-prune", "longcodezip"):
        for path in sorted(paths)[:3]:
            neighbors = engine.graph(name, path, depth=1, limit=12)
            for relation in neighbors["edges"]:
                relations.append(relation)
                other = relation["target"] if relation["source"] == path else relation["source"]
                if other not in paths:
                    file = engine.s.rows(
                        "SELECT path,hash,source,id FROM files WHERE project=? AND path=?", (project["id"], other)
                    )
                    if file:
                        symbols = engine.s.rows(
                            "SELECT start,end FROM symbols WHERE file=? ORDER BY start LIMIT 1", (file[0]["id"],)
                        )
                        span = (
                            symbols[0]
                            if symbols
                            else {"start": 1, "end": min(100, len(file[0]["source"].splitlines()))}
                        )
                        additions.append({**file[0], **span, "reason": "graph", "relation": relation["id"]})
                if len(additions) >= 12:
                    break
            if len(additions) >= 12:
                break
    # Documentation by subject is conditional, never a requirement to read all project docs.
    topics = {
        "architecture": r"architect|estrutura|design",
        "database": r"database|schema|migration|prisma|banco|sql",
        "deploy": r"deploy|docker|compose|kubern|implant",
        "security": r"auth|security|seguran|permission",
        "api": r"endpoint|api|route|rota",
    }
    for topic, pattern in topics.items():
        if not re.search(pattern, query, re.I):
            continue
        docs = engine.s.rows(
            "SELECT f.path,f.hash,f.source,f.id,e.start,e.end FROM entities e JOIN files f ON f.project=e.project AND f.path=e.path WHERE e.project=? AND e.kind='document' AND json_extract(e.payload,'$.topic')=? LIMIT 2",
            (project["id"], topic),
        )
        additions.extend(
            {**doc, "end": min(doc["end"], doc["start"] + 120), "reason": "subject_document"} for doc in docs
        )
    for row in additions[:16]:
        key = (row["path"], row["start"], row["end"])
        if key in selected or row["path"] in paths:
            continue
        if row["end"] < row["start"] or row["end"] - row["start"] > 2000:
            omissions.append({"path": row["path"], "reason": "related span too large"})
            continue
        item = engine.read(name, row["path"], row["start"], row["end"], row["hash"])
        item["selection_reason"] = row["reason"]
        size = len(json.dumps(item, ensure_ascii=False).encode())
        if size > remaining:
            omissions.append({"path": row["path"], "reason": "related evidence budget"})
            continue
        packet["evidence"].append(item)
        remaining -= size
        selected.add(key)
        paths.add(row["path"])
    # Link test contracts without asserting inferred relation correctness.
    tests = engine.s.rows(
        "SELECT path,name,start,end,status,origin FROM entities WHERE project=? AND kind='test' LIMIT 100",
        (project["id"],),
    )
    query_terms = set(re.findall(r"\w+", query.lower()))
    related = [
        test for test in tests if test["path"] in paths or query_terms & set(re.findall(r"\w+", test["name"].lower()))
    ][:8]
    engine.require_current(name)
    packet.update(
        {
            "relations": relations[:36],
            "related_tests": related,
            "omissions": packet["omissions"] + omissions,
            "remaining_source_bytes": remaining,
            "strategy": method,
            "original_source_only": True,
            "insufficient": not packet["evidence"],
        }
    )
    return bound_packet(packet, budget)


def refine(engine, name, query, missing_fact, budget=6000, mode="hybrid", previous=None):
    if not missing_fact or len(missing_fact) > 1000:
        raise ValueError("Missing fact must be explicit and at most 1000 characters")
    result = engine.context(name, query + " " + missing_fact, budget, mode)
    previous = previous or []
    fingerprints = {digest(json.dumps(item, sort_keys=True)) for item in previous}
    result["new_evidence"] = [
        item for item in result["evidence"] if digest(json.dumps(item, sort_keys=True)) not in fingerprints
    ]
    result["missing_fact"] = missing_fact
    result["stop_reason"] = "no_new_evidence" if not result["new_evidence"] else "budget_or_candidate_limit"
    return result


def bound_packet(packet, budget):
    """Budget the full serialized UTF-8 result, not just source text."""
    packet["budget_scope"] = "entire serialized UTF-8 JSON; not a Codex task token cap"
    packet["requested_bytes"] = budget
    packet["sufficiency"] = "unassessed" if packet.get("evidence") else "insufficient"

    def size():
        return len(json.dumps(packet, ensure_ascii=False).encode())

    omitted = 0
    for key in ("relations", "related_tests", "index_omissions", "omissions"):
        while size() > budget and packet.get(key):
            packet[key].pop()
            omitted += 1
    while size() > budget and packet.get("evidence"):
        packet["evidence"].pop()
        omitted += 1
    packet["metadata_or_evidence_omitted"] = omitted
    packet["insufficient"] = not packet.get("evidence")
    if size() > budget:
        minimal = {
            "snapshot": packet.get("snapshot"),
            "evidence": packet.get("evidence", []),
            "insufficient": not packet.get("evidence"),
            "omissions": [{"count": omitted}],
        }
        while len(json.dumps(minimal, ensure_ascii=False).encode()) > budget and minimal["evidence"]:
            minimal["evidence"].pop()
            minimal["omissions"][0]["count"] += 1
        minimal["insufficient"] = not minimal["evidence"]
        return minimal
    return packet
