#!/usr/bin/env python3
"""Discover git repositories in a workspace."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, discovery  # noqa: E402

USAGE = """Usage: discover-repos.py --workspace <workspace_root>

Lists git repositories found at the workspace root, immediate children, and
immediate children of repos/."""


def main(argv: list[str]) -> int:
    workspace = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--workspace":
            workspace = cli.require_value("--workspace", argv, i + 1)
            i += 2
        elif arg in ("-h", "--help"):
            cli.usage_exit(USAGE, 0)
        else:
            cli.usage_exit(USAGE, 1)
    if not workspace:
        cli.usage_exit(USAGE, 1)

    workspace = cli.resolve_dir(workspace)
    repos = discovery.discover(workspace)
    if not repos:
        cli.die(f"No git repositories found in {workspace}")
    for repo in repos:
        print(repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
