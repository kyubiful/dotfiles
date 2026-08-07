#!/usr/bin/env python3
"""Ensure AGENTS.md references the repository ARCHITECTURE.md as required agent context."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import agentsdoc, cli  # noqa: E402

USAGE = """Usage: update-agents-architecture-context.py --repo <repo_path>

Ensures AGENTS.md references the repository ARCHITECTURE.md as required agent
context. Creates AGENTS.md if missing, removes the obsolete aidev-explore
local-dev managed block when present, and appends only when the exact paragraph
is absent."""

PARAGRAPH = ("Repository architecture context lives in ARCHITECTURE.md. "
             "Always read it to acquire context and/or before making changes.")


def main(argv: list[str]) -> int:
    repo_path = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--repo":
            repo_path = cli.require_value("--repo", argv, i + 1)
            i += 2
        elif arg in ("-h", "--help"):
            cli.usage_exit(USAGE, 0)
        else:
            cli.usage_exit(USAGE, 1)
    if not repo_path:
        cli.usage_exit(USAGE, 1)

    repo_path = cli.resolve_dir(repo_path)
    architecture_file = os.path.join(repo_path, "ARCHITECTURE.md")
    if not os.path.isfile(architecture_file):
        cli.die(f"Architecture document not found: {architecture_file}")

    agents_file = os.path.join(repo_path, "AGENTS.md")
    agentsdoc.update(
        repo_path,
        PARAGRAPH,
        already_message=f"AGENTS.md already references ARCHITECTURE.md for {os.path.basename(repo_path)}",
        updated_message=f"Updated {agents_file} with ARCHITECTURE.md context reference",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
