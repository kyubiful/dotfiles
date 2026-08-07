"""Append or refresh the trailing artifact signature table."""
from __future__ import annotations

import re

from . import lockfile

_BLANK = re.compile(r"^[ \t\r\f\v]*$")
_DIVIDER = re.compile(r"^---[ \t\r\f\v]*$")
_AGENT_ROW = re.compile(r"^\| Agent \|")


def _strip_existing_signature(lines: list[str]) -> list[str]:
    last_divider = 0  # 1-based index of last `---` divider line
    for i, line in enumerate(lines, start=1):
        if _DIVIDER.match(line):
            last_divider = i

    cut = len(lines)
    if last_divider > 0:
        has_agent_row = any(_AGENT_ROW.match(lines[i - 1]) for i in range(last_divider + 1, len(lines) + 1))
        if has_agent_row:
            cut = last_divider - 1
            while cut > 0 and _BLANK.match(lines[cut - 1]):
                cut -= 1
    return lines[:cut]


def append(artifact: str, agent: str, assistant: str, model: str, cwd: str | None = None) -> str:
    lock = lockfile.lock_path(cwd)

    sha = lockfile.extract_sha(agent, lock)
    commit = "null" if (not sha or sha == "null") else sha[:7]
    version_ref = lockfile.extract_version_ref(lock)

    with open(artifact) as handle:
        lines = handle.read().splitlines()

    kept = _strip_existing_signature(lines)
    base = "".join(line + "\n" for line in kept)
    table = (
        "\n---\n\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        f"| Agent | {agent} |\n"
        f"| Assistant | {assistant} |\n"
        f"| Model | {model} |\n"
        f"| Commit | {commit} |\n"
        f"| Version Ref | {version_ref} |\n"
    )
    with open(artifact, "w") as handle:
        handle.write(base + table)

    return (f"signature-append: OK: {artifact} signed by {agent} "
            f"({assistant}, {model}) commit={commit} ref={version_ref}")
