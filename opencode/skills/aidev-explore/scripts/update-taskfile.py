#!/usr/bin/env python3
"""Write the repository-root Taskfile idempotently from stdin."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402

from _lib import cli, taskfile, textio  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "references", "taskfile-contract.yml"))

USAGE = """Usage: update-taskfile.py --repo <repo_path> --content-stdin

Writes the repository-root Taskfile content idempotently, preserving an
existing Taskfile.yaml when that extension is already in use."""


def _trimmed(content: str) -> str:
    lines = content.splitlines()
    first, last = 0, len(lines) - 1
    while first <= last and lines[first].strip() == "":
        first += 1
    while last >= first and lines[last].strip() == "":
        last -= 1
    kept = lines[first:last + 1]
    return "".join(line + "\n" for line in kept) + "\n"


def main(argv: list[str]) -> int:
    repo_path = ""
    content_stdin = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--repo":
            repo_path = cli.require_value("--repo", argv, i + 1)
            i += 2
        elif arg == "--content-stdin":
            content_stdin = True
            i += 1
        elif arg in ("-h", "--help"):
            cli.usage_exit(USAGE, 0)
        else:
            cli.usage_exit(USAGE, 1)

    if not repo_path or not content_stdin:
        cli.usage_exit(USAGE, 1)

    repo_path = cli.resolve_dir(repo_path)
    content = sys.stdin.read()

    fd, content_file = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)

        if textio.has_regex(content_file, r"^[ \t]*```"):
            cli.die(f"Taskfile content must not be wrapped in Markdown code fences: {content_file}")

        try:
            yaml.safe_load(content)
        except yaml.YAMLError as exc:
            print(f"Taskfile content is not valid YAML; refusing to write it: {content_file}", file=sys.stderr)
            print(str(exc), file=sys.stderr)
            return 1

        try:
            taskfile.validate(taskfile_path=content_file, repo_path=repo_path, contract_path=DEFAULT_CONTRACT)
        except cli.Failure as failure:
            print(f"Taskfile content does not satisfy the Taskfile contract; refusing to "
                  f"write it: {content_file}", file=sys.stderr)
            for line in failure.lines:
                print(line, file=sys.stderr)
            return 1

        taskfile_yml = os.path.join(repo_path, "Taskfile.yml")
        taskfile_yaml = os.path.join(repo_path, "Taskfile.yaml")
        if os.path.isfile(taskfile_yml) and os.path.isfile(taskfile_yaml):
            cli.die(f"Both Taskfile.yml and Taskfile.yaml exist; refusing to overwrite "
                    f"ambiguously in {repo_path}")

        target_file = taskfile_yaml if os.path.isfile(taskfile_yaml) else taskfile_yml
        with open(target_file, "w") as handle:
            handle.write(_trimmed(content))
    finally:
        if os.path.exists(content_file):
            os.unlink(content_file)

    print(f"Wrote {target_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
