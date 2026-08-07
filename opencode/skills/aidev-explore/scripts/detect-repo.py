#!/usr/bin/env python3
"""Deterministic repository detection. Usage: detect-repo.py <repo_path>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, repodetect  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 1 or not argv[0]:
        cli.die("Usage: detect-repo.py <repo_path>")
    repo_path = cli.resolve_dir(argv[0])
    sys.stdout.write(repodetect.detect(repo_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
