#!/usr/bin/env python3
"""Validate AGENTS.md against the aidev-explore contract."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, docvalidate  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "references", "agents-doc-contract.yml"))

USAGE = """Usage: validate-agents-doc.py --repo <repo_path> [--contract <path>]

Validates that AGENTS.md contains the required architecture discovery paragraph,
contains the Taskfile paragraph only when a repository-root Taskfile exists, and
has no obsolete aidev-explore local-dev managed block."""


def main(argv: list[str]) -> int:
    repo_path = ""
    contract_path = DEFAULT_CONTRACT
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--repo":
            repo_path = cli.require_value("--repo", argv, i + 1)
            i += 2
        elif arg == "--contract":
            contract_path = cli.require_value("--contract", argv, i + 1)
            i += 2
        elif arg in ("-h", "--help"):
            cli.usage_exit(USAGE, 0)
        else:
            cli.usage_exit(USAGE, 1)
    if not repo_path:
        cli.usage_exit(USAGE, 1)

    repo_path = cli.resolve_dir(repo_path)
    try:
        print(docvalidate.validate_agents(repo_path, contract_path))
    except cli.Failure as failure:
        for line in failure.lines:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
