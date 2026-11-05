import os
import sqlite3
import time
from pathlib import Path

home = Path(os.environ.get("CE_HOME", Path.home() / ".local/state/codex-economy"))
source = sqlite3.connect(home / "state.sqlite", timeout=30)
path = home / ("pre-upgrade-" + str(time.time_ns()) + ".sqlite")
backup = sqlite3.connect(path)
try:
    source.backup(backup)
    if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Pre-upgrade backup is corrupt")
finally:
    backup.close()
    source.close()
os.chmod(path, 0o600)
