import fnmatch
import hashlib
import os
import re
from pathlib import Path

DEFAULT_POLICY = {
    "version": 1,
    "external": False,
    "max_file_bytes": 1_000_000,
    "exclude": [
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "build",
        "dist",
        ".next",
        ".gradle",
        "__pycache__",
        ".env*",
        "*.pem",
        "*.key",
        "*credentials*",
        "*secret*",
        ".codex",
        ".ce",
        "*.sqlite*",
    ],
}


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def excluded(path, policy):
    return any(
        fnmatch.fnmatch(part, pat) or fnmatch.fnmatch(path, pat)
        for part in Path(path).parts
        for pat in policy["exclude"]
    )


def read_source(root, relative, policy):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or excluded(str(rel), policy):
        raise ValueError("Path rejected by project policy")
    # openat + O_NOFOLLOW on every component prevents both directory and file symlink races.
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in rel.parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        f = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            import stat

            a = os.fstat(f)
            if not stat.S_ISREG(a.st_mode) or a.st_size > policy["max_file_bytes"]:
                raise ValueError("Not a regular bounded source file")
            data = os.read(f, policy["max_file_bytes"] + 1)
            b = os.fstat(f)
            if (a.st_mtime_ns, a.st_size) != (b.st_mtime_ns, b.st_size) or len(data) > policy["max_file_bytes"]:
                raise ValueError("File changed during read")
        finally:
            os.close(f)
    finally:
        os.close(fd)
    if b"\0" in data:
        raise ValueError("Binary file")
    return data.decode("utf-8"), digest(data)


def redact(s):
    s = re.sub(r'(?i)(bearer\s+)[^\s"\']+', r"\1[REDACTED]", s)
    s = re.sub(r"(?i)((?:api[_-]?key|password|token|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", s)
    s = re.sub(r"\b(?:sk-|ts_)[a-zA-Z0-9_-]{12,}", "[REDACTED]", s)
    return s
