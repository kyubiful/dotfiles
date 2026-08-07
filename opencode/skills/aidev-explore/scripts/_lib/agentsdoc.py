"""Shared AGENTS.md context-reference maintenance for the update-agents-* scripts.

Removes the obsolete `aidev-explore:local-dev` managed block and idempotently appends a
context paragraph, printing the same messages as the original scripts.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import textio

START_MARKER = "<!-- aidev-explore:local-dev:start -->"
END_MARKER = "<!-- aidev-explore:local-dev:end -->"


def _strip_managed_block(lines: list[str]) -> list[str]:
    state = ""
    out: list[str] = []
    for line in lines:
        if state != "inside" and START_MARKER in line:
            state = "inside"
            continue
        if state == "inside":
            if END_MARKER in line:
                state = "outside"
            continue
        out.append(line)
    return out


def update(repo_path: str, paragraph: str, already_message: str, updated_message: str) -> "None":
    agents_file = os.path.join(repo_path, "AGENTS.md")
    printed: list[str] = []

    if os.path.isfile(agents_file):
        start_count = textio.count_fixed_substr(agents_file, START_MARKER)
        end_count = textio.count_fixed_substr(agents_file, END_MARKER)

        if start_count > 1 or end_count > 1:
            _die(f"AGENTS.md has duplicate obsolete local-dev markers "
                 f"(start={start_count}, end={end_count}): {agents_file}")
        if start_count != end_count:
            _die(f"AGENTS.md has unbalanced obsolete local-dev markers "
                 f"(start={start_count}, end={end_count}): {agents_file}")
        if start_count == 1:
            kept = _strip_managed_block(Path(agents_file).read_text().splitlines())
            Path(agents_file).write_text("".join(line + "\n" for line in kept))
            printed.append(f"Removed obsolete local-dev block from {agents_file}")

    if os.path.isfile(agents_file) and textio.has_fixed_wholeline(agents_file, paragraph):
        for line in printed:
            print(line)
        print(already_message)
        return

    _append_paragraph(agents_file, paragraph)

    for line in printed:
        print(line)
    print(updated_message)


def _append_paragraph(agents_file: str, paragraph: str) -> "None":
    exists = os.path.isfile(agents_file)
    content = Path(agents_file).read_bytes() if exists else b""
    if exists and content:
        suffix = b"" if content.endswith(b"\n") else b"\n"
        with open(agents_file, "ab") as handle:
            handle.write(suffix + b"\n" + paragraph.encode() + b"\n")
    else:
        Path(agents_file).write_text(paragraph + "\n")


def _die(message: str) -> "None":
    import sys
    print(message, file=sys.stderr)
    raise SystemExit(1)
