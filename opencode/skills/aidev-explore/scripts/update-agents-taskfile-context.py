#!/usr/bin/env python3
"""Ensure AGENTS.md references an existing repository-root Taskfile."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import agentsdoc, cli  # noqa: E402

USAGE = """Usage: update-agents-taskfile-context.py --repo <repo_path>

Ensures AGENTS.md references an existing repository-root Taskfile as the source
of local development commands. Creates AGENTS.md if missing, removes the
obsolete aidev-explore local-dev managed block when present, and appends only
when the exact paragraph is absent."""

PARAGRAPH = ("Local development commands live in the repository-root Taskfile "
             "(`Taskfile.yml`, or `Taskfile.yaml` when already present). Always prefer "
             "`task <phase>` for standard local workflows (`install`, `build`, `lint`, "
             "`format`, `test`, `start`).")


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
    taskfile_yml = os.path.join(repo_path, "Taskfile.yml")
    taskfile_yaml = os.path.join(repo_path, "Taskfile.yaml")

    if os.path.isfile(taskfile_yml) and os.path.isfile(taskfile_yaml):
        cli.die(f"Both Taskfile.yml and Taskfile.yaml exist; cannot determine a single "
                f"source of truth in {repo_path}")
    if not os.path.isfile(taskfile_yml) and not os.path.isfile(taskfile_yaml):
        cli.die(f"Taskfile not found in {repo_path}")

    agents_file = os.path.join(repo_path, "AGENTS.md")
    agentsdoc.update(
        repo_path,
        PARAGRAPH,
        already_message=f"AGENTS.md already references the repository Taskfile for {os.path.basename(repo_path)}",
        updated_message=f"Updated {agents_file} with Taskfile context reference",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
