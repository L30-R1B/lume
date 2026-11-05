"""Versioned transactional state, maintenance locks and explicit cache validity."""

import fcntl
import json
import os
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, root TEXT UNIQUE NOT NULL, policy TEXT NOT NULL);
CREATE TABLE snapshots(id INTEGER PRIMARY KEY, project INTEGER REFERENCES projects(id), fingerprint TEXT, created REAL, state TEXT, details TEXT);
CREATE TABLE files(id INTEGER PRIMARY KEY, project INTEGER REFERENCES projects(id), path TEXT, hash TEXT, source TEXT, adapter TEXT, snapshot INTEGER, UNIQUE(project,path));
CREATE TABLE symbols(id TEXT PRIMARY KEY, file INTEGER REFERENCES files(id) ON DELETE CASCADE, name TEXT, kind TEXT, start INTEGER, end INTEGER, origin TEXT, status TEXT);
CREATE TABLE edges(id INTEGER PRIMARY KEY, project INTEGER, source TEXT, target TEXT, kind TEXT, origin TEXT, status TEXT, snapshot INTEGER);
CREATE VIRTUAL TABLE search USING fts5(path, source, project UNINDEXED, file UNINDEXED);
CREATE TABLE sessions(id TEXT PRIMARY KEY, project INTEGER, state TEXT, payload TEXT, created REAL, updated REAL);
CREATE TABLE runs(id TEXT PRIMARY KEY, project INTEGER, argv TEXT, started REAL, elapsed REAL, code INTEGER, state TEXT, stdout TEXT, stderr TEXT, details TEXT);
CREATE TABLE cache(namespace TEXT, key TEXT, value TEXT, expires REAL, PRIMARY KEY(namespace,key));
CREATE TABLE events(id INTEGER PRIMARY KEY, created REAL, kind TEXT, payload TEXT);
PRAGMA user_version=1;
"""
MIGRATIONS = {
    2: [
        "ALTER TABLE projects ADD COLUMN root_identity TEXT NOT NULL DEFAULT ''",
        "CREATE TABLE entities(id TEXT PRIMARY KEY, project INTEGER REFERENCES projects(id), snapshot INTEGER REFERENCES snapshots(id), path TEXT, start INTEGER, end INTEGER, kind TEXT, name TEXT, payload TEXT, origin TEXT, status TEXT)",
        "CREATE INDEX entities_lookup ON entities(project,kind,path)",
        "CREATE INDEX edges_source ON edges(project,source,kind)",
        "CREATE INDEX edges_target ON edges(project,target,kind)",
        "CREATE INDEX symbols_name ON symbols(name,file)",
        "CREATE INDEX snapshots_project ON snapshots(project,id)",
        "CREATE INDEX events_kind ON events(kind,created)",
        "CREATE TABLE jobs(id TEXT PRIMARY KEY, project INTEGER, state TEXT NOT NULL, payload TEXT NOT NULL, updated REAL NOT NULL)",
        "CREATE TABLE approvals(id TEXT PRIMARY KEY, project INTEGER, fingerprint TEXT, checks TEXT, created REAL)",
        "PRAGMA user_version=2",
    ],
    3: [
        "CREATE TABLE run_outputs(run TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, stream TEXT NOT NULL CHECK(stream IN ('stdout','stderr')), content BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(run,stream))",
        "PRAGMA user_version=3",
    ],
}
VERSION = 3


def root_identity(root):
    stat = os.stat(root, follow_symlinks=False)
    import stat as mode

    if not mode.S_ISDIR(stat.st_mode):
        raise ValueError("Authorized root is no longer a directory")
    return f"{stat.st_dev}:{stat.st_ino}"


class Store:
    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("CE_HOME", Path.home() / ".local/state/codex-economy")).absolute()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.home.is_symlink():
            raise ValueError("State directory cannot be a symlink")
        self._lock = os.open(self.home / ".maintenance.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        fcntl.flock(self._lock, fcntl.LOCK_SH)
        self.db = sqlite3.connect(self.home / "state.sqlite", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            v = self.db.execute("PRAGMA user_version").fetchone()[0]
            if v == 0:
                for statement in SCHEMA.split(";"):
                    if statement.strip():
                        self.db.execute(statement)
                v = 1
            if v > VERSION:
                raise ValueError(f"Unsupported schema {v}; requires newer application")
            for version in range(v + 1, VERSION + 1):
                for statement in MIGRATIONS[version]:
                    self.db.execute(statement)
                if version == 2:
                    for row in self.db.execute("SELECT id,root FROM projects").fetchall():
                        try:
                            identity = root_identity(row["root"])
                        except (OSError, ValueError):
                            identity = "unavailable"
                        self.db.execute("UPDATE projects SET root_identity=? WHERE id=?", (identity, row["id"]))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.close()
            raise
        os.chmod(self.home / "state.sqlite", 0o600)

    def close(self):
        if getattr(self, "db", None) is not None:
            self.db.close()
            self.db = None
        if getattr(self, "_lock", None) is not None:
            os.close(self._lock)
            self._lock = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def project(self, name):
        rows = self.rows("SELECT * FROM projects WHERE name=?", (name,))
        if not rows:
            raise ValueError(f"Unknown project {name}; register it first")
        p = rows[0]
        p["policy"] = json.loads(p["policy"])
        if p["root_identity"] and root_identity(p["root"]) != p["root_identity"]:
            raise ValueError("Authorized project root changed identity; register its new root explicitly")
        return p

    def event(self, kind, payload):
        from .security import redact_data

        with self.db:
            self.db.execute(
                "INSERT INTO events(created,kind,payload) VALUES(?,?,?)",
                (time.time(), kind, json.dumps(redact_data(payload))),
            )

    def cache_get(self, namespace, key, validity):
        if namespace not in ("extract", "inference", "task"):
            raise ValueError("Invalid cache namespace")
        rows = self.rows("SELECT value,expires FROM cache WHERE namespace=? AND key=?", (namespace, key))
        if not rows or (rows[0]["expires"] is not None and rows[0]["expires"] <= time.time()):
            return None
        value = json.loads(rows[0]["value"])
        return value.get("result") if value.get("validity") == validity else None

    def cache_put(self, namespace, key, validity, result, ttl=3600):
        if namespace not in ("extract", "inference", "task") or not 1 <= ttl <= 86400 * 30:
            raise ValueError("Invalid cache policy")
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO cache VALUES(?,?,?,?)",
                (namespace, key, json.dumps({"validity": validity, "result": result}), time.time() + ttl),
            )

    def backup(self, destination):
        path = Path(destination)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        con = sqlite3.connect(path)
        try:
            self.db.backup(con)
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup failed integrity")
        finally:
            con.close()
        return {"backup": str(path.absolute()), "integrity": "ok", "schema": VERSION}

    def integrity(self):
        self.db.execute("INSERT INTO search(search) VALUES('integrity-check')")
        self.db.commit()
        return {
            "sqlite": self.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": self.rows("PRAGMA foreign_key_check"),
        }

    def prune(self, days=30):
        if not 1 <= days <= 3650:
            raise ValueError("Retention must be 1–3650 days")
        cutoff = time.time() - days * 86400
        with self.db:
            self.db.execute("DELETE FROM events WHERE created<?", (cutoff,))
            self.db.execute("DELETE FROM runs WHERE started<? AND state!='running'", (cutoff,))
            self.db.execute("DELETE FROM cache WHERE expires IS NOT NULL AND expires<?", (time.time(),))
            self.db.execute(
                "DELETE FROM cache WHERE namespace='extract' AND rowid NOT IN (SELECT rowid FROM cache WHERE namespace='extract' ORDER BY rowid DESC LIMIT 10000)"
            )
            keep = {
                r["snapshot"]
                for r in self.rows("SELECT DISTINCT snapshot FROM files UNION SELECT DISTINCT snapshot FROM entities")
            }
            keep.update(r["id"] for r in self.rows("SELECT MAX(id) AS id FROM snapshots GROUP BY project"))
            for row in self.rows("SELECT id FROM snapshots WHERE created<?", (cutoff,)):
                if row["id"] not in keep:
                    self.db.execute("DELETE FROM snapshots WHERE id=?", (row["id"],))
        self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")
        return {"retention_days": days, "extraction_cache_max_entries": 10000}


def recover(home, source=None):
    """Offline restore or index reset; preserve corrupt DB and companion WAL files."""
    import shutil
    import uuid

    home = Path(home).absolute()
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(home / ".maintenance.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("State is in use; stop other ce/MCP processes before recovery") from None
        if source:
            src = Path(source).resolve(strict=True)
            con = sqlite3.connect(src.as_uri() + "?mode=ro", uri=True)
            try:
                if (
                    con.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                    or not 1 <= con.execute("PRAGMA user_version").fetchone()[0] <= VERSION
                ):
                    raise ValueError("Invalid backup")
                destination = home / ("restore-" + uuid.uuid4().hex + ".sqlite")
                restored = sqlite3.connect(destination)
                try:
                    con.backup(restored)
                finally:
                    restored.close()
                os.chmod(destination, 0o600)
            finally:
                con.close()
        archive = home / ("recovery-" + uuid.uuid4().hex)
        archive.mkdir(mode=0o700)
        for suffix in ("", "-wal", "-shm"):
            existing = home / ("state.sqlite" + suffix)
            if existing.exists():
                shutil.move(str(existing), str(archive / existing.name))
        if source:
            os.replace(destination, home / "state.sqlite")
    finally:
        os.close(fd)
    with Store(home) as store:
        integrity = store.integrity()
    return {
        "state": "restored" if source else "reset",
        "archive": str(archive),
        "integrity": integrity,
        "projects_preserved": True,
        "registry_reimport_required": not bool(source),
    }
