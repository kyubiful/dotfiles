#!/usr/bin/env python3
"""Extract a resource sha from .aicontext/aicontext.lock (null-safe)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import lockfile  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: signature-extract.py <resource-name>", file=sys.stderr)
        return 1
    print(lockfile.extract_sha(argv[0], lockfile.lock_path()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
