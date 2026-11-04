"""Transactional local state. All paths here belong to the application, never a repository."""

import json
import os
import sqlite3
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


class Store:
    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("CE_HOME", Path.home() / ".local/state/codex-economy")).resolve()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.home / "state.sqlite", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("BEGIN IMMEDIATE")
        v = self.db.execute("PRAGMA user_version").fetchone()[0]
        if v == 0:
            # executescript commits the current lock; schema statements are applied individually.
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    self.db.execute(statement)
            self.db.commit()
        elif v != 1:
            self.db.rollback()
            raise ValueError(f"Unsupported schema {v}; use a compatible release")
        self.db.commit()
        os.chmod(self.home / "state.sqlite", 0o600)

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def project(self, name):
        rows = self.rows("SELECT * FROM projects WHERE name=?", (name,))
        if not rows:
            raise ValueError(f"Unknown project {name}; register it first")
        p = rows[0]
        p["policy"] = json.loads(p["policy"])
        return p

    def backup(self, destination):
        p = Path(destination)
        if p.exists():
            raise ValueError("Backup destination exists")
        con = sqlite3.connect(p)
        try:
            self.db.backup(con)
        finally:
            con.close()
        os.chmod(p, 0o600)
        return {"backup": str(p.resolve()), "integrity": "ok"}

    def integrity(self):
        return {
            "sqlite": self.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": self.rows("PRAGMA foreign_key_check"),
        }
