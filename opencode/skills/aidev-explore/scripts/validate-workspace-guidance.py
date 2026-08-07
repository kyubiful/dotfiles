#!/usr/bin/env python3
"""Validate ARCHITECTURE.md/AGENTS.md/Taskfile guidance for every repo under <workspace>/repos/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, discovery, docvalidate, taskfile  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCES = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "references"))
ARCHITECTURE_CONTRACT = os.path.join(REFERENCES, "architecture-doc-contract.yml")
AGENTS_CONTRACT = os.path.join(REFERENCES, "agents-doc-contract.yml")
TASKFILE_CONTRACT = os.path.join(REFERENCES, "taskfile-contract.yml")

USAGE = """Usage: validate-workspace-guidance.py --workspace <workspace_root>

Validates repository-local ARCHITECTURE.md and AGENTS.md guidance for every
repository discovered under <workspace_root>/repos/. Repository-root Taskfiles
are validated only when present."""


def _run(func) -> tuple[int, list[str]]:
    try:
        return 0, [func()]
    except cli.Failure as failure:
        return 1, failure.lines


def _print_indented(lines: list[str]) -> None:
    for line in lines:
        print(f"  {line}")


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
    prefix = os.path.join(workspace, "repos") + os.sep
    repos = [r for r in discovery.discover(workspace) if r.startswith(prefix)]

    if not repos:
        print(f"No repositories found under {workspace}/repos", file=sys.stderr)
        return 1

    passed = 0
    failed = 0
    for repo_path in repos:
        rel_repo = repo_path[len(workspace) + 1:]
        arch_status, arch_output = _run(
            lambda p=repo_path: docvalidate.validate_architecture(
                os.path.join(p, "ARCHITECTURE.md"), ARCHITECTURE_CONTRACT))
        agents_status, agents_output = _run(
            lambda p=repo_path: docvalidate.validate_agents(p, AGENTS_CONTRACT))

        taskfile_yml = os.path.join(repo_path, "Taskfile.yml")
        taskfile_yaml = os.path.join(repo_path, "Taskfile.yaml")
        if os.path.isfile(taskfile_yml) or os.path.isfile(taskfile_yaml):
            taskfile_status, taskfile_output = _run(
                lambda p=repo_path: taskfile.validate(
                    taskfile_path=None, repo_path=p, contract_path=TASKFILE_CONTRACT))
        else:
            taskfile_status, taskfile_output = 0, ["Skipped: no repository-root Taskfile."]

        if arch_status == 0 and agents_status == 0 and taskfile_status == 0:
            print(f"PASS {rel_repo}")
            passed += 1
            continue

        print(f"FAIL {rel_repo}")
        failed += 1
        if arch_status != 0:
            print(" ARCHITECTURE.md")
            _print_indented(arch_output)
        if agents_status != 0:
            print(" AGENTS.md")
            _print_indented(agents_output)
        if taskfile_status != 0:
            print(" TASKFILE")
            _print_indented(taskfile_output)

    print(f"Workspace guidance validation summary: total={len(repos)} passed={passed} failed={failed}")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
