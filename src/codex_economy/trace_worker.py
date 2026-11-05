"""Observed Python call edges; no inferred links or network service."""

import atexit
import json
import os
import runpy
import sys
from pathlib import Path


def main():
    root = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2])
    script = (root / sys.argv[3]).resolve()
    if not script.is_relative_to(root):
        raise ValueError("Trace script outside root")
    argv = sys.argv[3:]
    sys.argv = argv
    sys.path.insert(0, str(root))
    edges = {}

    def profile(frame, event, arg):
        if event != "call" or len(edges) >= 10000:
            return
        target = Path(frame.f_code.co_filename)
        caller = frame.f_back
        if not target.is_absolute() or not target.is_relative_to(root) or caller is None:
            return
        source = Path(caller.f_code.co_filename)
        if not source.is_absolute() or not source.is_relative_to(root):
            return
        key = (
            str(source.relative_to(root)),
            str(target.relative_to(root)),
            caller.f_lineno,
            frame.f_code.co_firstlineno,
            frame.f_code.co_name,
        )
        edges[key] = edges.get(key, 0) + 1

    def save():
        sys.setprofile(None)
        payload = {
            "edges": [
                dict(source=k[0], target=k[1], line=k[2], target_line=k[3], name=k[4], count=v)
                for k, v in edges.items()
            ],
            "limit": 10000,
            "limit_reached": len(edges) >= 10000,
            "origin": "python-sys.setprofile",
            "status": "observed",
        }
        destination.write_text(json.dumps(payload))
        os.chmod(destination, 0o600)

    atexit.register(save)
    sys.setprofile(profile)
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
