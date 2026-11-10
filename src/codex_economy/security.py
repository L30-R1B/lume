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
        ".pytest_cache",
        ".ruff_cache",
        "*.egg-info",
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


def read_source(root, relative, policy, expected_root=None):
    root = Path(root).absolute()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or excluded(str(rel), policy):
        raise ValueError("Path rejected by project policy")
    # openat + O_NOFOLLOW on every component prevents both directory and file symlink races.
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened = os.fstat(fd)
    if expected_root and f"{opened.st_dev}:{opened.st_ino}" != expected_root:
        os.close(fd)
        raise ValueError("Authorized root changed during read")
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
            chunks = []
            count = 0
            while count <= policy["max_file_bytes"]:
                chunk = os.read(f, min(65536, policy["max_file_bytes"] + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
            data = b"".join(chunks)
            b = os.fstat(f)
            current = os.stat(rel.name, dir_fd=fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (b.st_dev, b.st_ino):
                raise ValueError("Path replaced during read")
            if (
                (a.st_mtime_ns, a.st_size) != (b.st_mtime_ns, b.st_size)
                or len(data) > policy["max_file_bytes"]
                or len(data) != a.st_size
            ):
                raise ValueError("File changed during read")
        finally:
            os.close(f)
    finally:
        os.close(fd)
    if b"\0" in data:
        raise ValueError("Binary file")
    return data.decode("utf-8"), digest(data)


def redact(s):
    # Do not treat a quoted code literal such as `"Bearer "` as a credential.
    # JSON escaping puts a backslash before that closing quote, so exclude it
    # from both the token start and token body while still masking real values.
    s = re.sub(r"(?i)(bearer\s+)(?![\"'\\])([^\s\"'\\]+)", r"\1[REDACTED]", s)
    s = re.sub(r"(?i)((?:api[_-]?key|password|token|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", s)
    s = re.sub(r"\b(?:sk-|ts_)[a-zA-Z0-9_-]{12,}", "[REDACTED]", s)
    return s


def redact_data(value):
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if re.fullmatch(r"(?i)(api[_-]?key|password|secret|access[_-]?token|authorization)", str(key))
                else redact_data(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


def write_project(root, relative, content, expected=None):
    """Atomic managed extension writes confined through no-follow directory handles."""
    import uuid

    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("Invalid managed path")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".ce-" + uuid.uuid4().hex
    original_mode = 0o600
    try:
        for part in rel.parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        existing = None
        try:
            old = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                original_mode = os.fstat(old).st_mode & 0o777
                existing = os.read(old, 1_000_001).decode()
            finally:
                os.close(old)
        except FileNotFoundError:
            pass
        if existing is not None and expected is not None and existing != expected:
            raise ValueError("Managed file changed externally; refusing overwrite")
        if existing is not None and expected is None and existing != content:
            raise ValueError("Unmanaged file exists; refusing overwrite")
        target = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            os.fchmod(target, original_mode)
            data = content.encode()
            offset = 0
            while offset < len(data):
                offset += os.write(target, data[offset:])
            os.fsync(target)
        finally:
            os.close(target)
        os.rename(temporary, rel.name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass
        os.close(fd)
    return str(Path(root) / rel)


def remove_project_file(root, relative, expected):
    """Remove one unchanged managed file, opening every parent without following symlinks."""
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("Invalid managed path")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in rel.parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        try:
            file_fd = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        except FileNotFoundError:
            return False
        try:
            info = os.fstat(file_fd)
            content = os.read(file_fd, 1_000_001).decode("utf-8")
            current = os.stat(rel.name, dir_fd=fd, follow_symlinks=False)
            if content != expected or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError("Managed file changed externally; refusing removal")
        finally:
            os.close(file_fd)
        os.unlink(rel.name, dir_fd=fd)
        os.fsync(fd)
        return True
    finally:
        os.close(fd)
