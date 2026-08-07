#!/usr/bin/env python3
"""Append (or refresh) the artifact signature table."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import cli, signature  # noqa: E402

USAGE = """Usage: signature-append.py --artifact <path> --agent <name> --assistant <id> --model <name>

  --artifact   Path to the owned artifact markdown file to sign.
  --agent      Specialist agent name (e.g. AIDevResearcher).
  --assistant  Runtime identity: vscode | opencode | copilotcli | claudecode.
  --model      Self-reported model name at write time.

Resolves Commit (7-char sha) and Version Ref from .aicontext/aicontext.lock,
falling back to null/null when the lock is absent. Idempotent: an existing
trailing signature table is replaced, never duplicated."""

PREFIX = "signature-append"


def main(argv: list[str]) -> int:
    artifact = agent = assistant = model = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--artifact":
            artifact = cli.require_value("--artifact", argv, i + 1)
            i += 2
        elif arg == "--agent":
            agent = cli.require_value("--agent", argv, i + 1)
            i += 2
        elif arg == "--assistant":
            assistant = cli.require_value("--assistant", argv, i + 1)
            i += 2
        elif arg == "--model":
            model = cli.require_value("--model", argv, i + 1)
            i += 2
        elif arg in ("-h", "--help"):
            print(USAGE)
            return 0
        else:
            print(USAGE, file=sys.stderr)
            return 1

    if not (artifact and agent and assistant and model):
        print(USAGE, file=sys.stderr)
        return 1
    if not os.path.isfile(artifact):
        cli.fail(PREFIX, f"artifact not found: {artifact}")

    print(signature.append(artifact, agent, assistant, model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
