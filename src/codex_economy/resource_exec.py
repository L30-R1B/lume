"""Resource limits applied in a fresh single-thread process before exec; no shell."""

import json
import os
import resource
import sys


def main():
    limits = json.loads(sys.argv[1])
    argv = sys.argv[3:]
    if "memory_mb" in limits:
        amount = limits["memory_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (amount, amount))
    if "cpu_seconds" in limits:
        amount = limits["cpu_seconds"]
        resource.setrlimit(resource.RLIMIT_CPU, (amount, amount))
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
