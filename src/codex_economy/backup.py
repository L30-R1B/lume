"""Portable state bundles, checksums and strict extraction; user credentials excluded."""

import hashlib
import io
import json
import os
import tarfile
import tempfile
from pathlib import Path
from .store import recover
from .config import validate
from .security import write_project


def bundle(store, destination):
    target = Path(destination)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with tempfile.TemporaryDirectory(prefix="ce-backup-") as folder:
        database = Path(folder) / "state.sqlite"
        store.backup(database)
        items = {"state.sqlite": database.read_bytes()}
        config = store.home / "config.json"
        if config.exists():
            items["config.json"] = config.read_bytes()
        manifest = {
            "version": 1,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in items.items()},
            "credentials_included": False,
        }
        items["manifest.json"] = json.dumps(manifest).encode()
        with os.fdopen(fd, "wb") as output:
            with tarfile.open(fileobj=output, mode="w:gz") as archive:
                for name, data in items.items():
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    entry.mode = 0o600
                    archive.addfile(entry, io.BytesIO(data))
    return {
        "backup": str(target.absolute()),
        "bundle": True,
        "credentials_included": False,
        "configuration_included": config.exists(),
    }


def restore_bundle(home, source):
    home = Path(home)
    contents = {}
    total = 0
    with tarfile.open(source, "r:gz") as archive:
        for member in archive:
            if (
                member.name not in ("state.sqlite", "config.json", "manifest.json")
                or not member.isfile()
                or member.name in contents
            ):
                raise ValueError("Invalid backup bundle member")
            total += member.size
            if not 0 <= member.size <= 256_000_000 or total > 300_000_000:
                raise ValueError("Backup bundle exceeds size limit")
            contents[member.name] = archive.extractfile(member).read()
    if "manifest.json" not in contents or "state.sqlite" not in contents:
        raise ValueError("Incomplete backup bundle")
    manifest = json.loads(contents.pop("manifest.json"))
    if manifest.get("version") != 1 or set(manifest.get("files", {})) != set(contents):
        raise ValueError("Invalid backup manifest")
    for name, data in contents.items():
        if hashlib.sha256(data).hexdigest() != manifest["files"][name]:
            raise ValueError("Backup checksum mismatch")
    if "config.json" in contents:
        validate(json.loads(contents["config.json"]))
    with tempfile.TemporaryDirectory(prefix="ce-restore-") as folder:
        file = Path(folder) / "state.sqlite"
        file.write_bytes(contents["state.sqlite"])
        result = recover(home, file)
    if "config.json" in contents:
        config = home / "config.json"
        write_project(
            home,
            "config.json",
            contents["config.json"].decode(),
            expected=config.read_text() if config.exists() else None,
        )
    return {**result, "configuration_restored": "config.json" in contents, "credentials_preserved": True}
