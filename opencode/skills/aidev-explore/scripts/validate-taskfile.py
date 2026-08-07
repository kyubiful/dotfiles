#!/usr/bin/env python3
"""Validate the repository-root Taskfile structure and included phase tasks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, taskfile  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "references", "taskfile-contract.yml"))

USAGE = """Usage: validate-taskfile.py (--repo <repo_path> | --file <taskfile_path>) [--contract <path>]

Validates the repository-root Taskfile structure and included phase tasks."""


def main(argv: list[str]) -> int:
    repo_path = ""
    taskfile_path = ""
    contract_path = DEFAULT_CONTRACT
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--repo":
            repo_path = cli.require_value("--repo", argv, i + 1)
            i += 2
        elif arg == "--file":
            taskfile_path = cli.require_value("--file", argv, i + 1)
            i += 2
        elif arg == "--contract":
            contract_path = cli.require_value("--contract", argv, i + 1)
            i += 2
        elif arg in ("-h", "--help"):
            cli.usage_exit(USAGE, 0)
        else:
            cli.usage_exit(USAGE, 1)

    resolved_repo = None
    if not taskfile_path:
        if not repo_path:
            cli.usage_exit(USAGE, 1)
        resolved_repo = cli.resolve_dir(repo_path)

    try:
        result = taskfile.validate(
            taskfile_path=taskfile_path or None,
            repo_path=resolved_repo,
            contract_path=contract_path,
        )
        print(result)
    except cli.Failure as failure:
        for line in failure.lines:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
