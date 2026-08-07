"""CLI helpers: usage/exit conventions shared by the entry scripts."""
from __future__ import annotations

import os
import sys


class Failure(Exception):
    """A validation failure carrying the stderr lines the original script would print."""

    def __init__(self, lines):
        self.lines = list(lines) if isinstance(lines, (list, tuple)) else [lines]
        super().__init__("\n".join(self.lines))


def die(message: str, code: int = 1) -> "None":
    print(message, file=sys.stderr)
    raise SystemExit(code)


def usage_exit(usage: str, code: int) -> "None":
    stream = sys.stdout if code == 0 else sys.stderr
    print(usage.rstrip("\n"), file=stream)
    raise SystemExit(code)


def require_value(flag: str, args: list[str], index: int) -> str:
    if index >= len(args):
        die(f"{flag} requires a value")
    return args[index]


def resolve_dir(path: str) -> str:
    """Mirror `cd "$path" && pwd`: require an existing directory, return its absolute
    logical path (like the shell, symlinks in the path are not resolved)."""
    if not os.path.isdir(path):
        die(f"{path}: No such directory")
    return os.path.abspath(path)
