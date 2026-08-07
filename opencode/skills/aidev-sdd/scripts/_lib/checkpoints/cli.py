"""Exit/usage conventions shared by the aidev-sdd entry scripts."""
from __future__ import annotations

import sys


class ToolError(Exception):
    """A fatal error that the entry script reports with its tool prefix and exit code."""

    def __init__(self, message: str, code: int = 1):
        self.message = message
        self.code = code
        super().__init__(message)


class LintFailure(Exception):
    """A linter failure. `message` is printed as `sdd-lint: <message>` when set;
    when None the process exits `code` silently (the check already printed its own
    diagnostics) and never prints the trailing OK line."""

    def __init__(self, message: str | None, code: int = 1):
        self.message = message
        self.code = code
        super().__init__(message or "")


def fail(prefix: str, message: str, code: int = 1) -> "None":
    """Mirror the shell `fail`: print `<prefix>: <message>` to stderr and exit."""
    print(f"{prefix}: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_value(flag: str, args: list[str], index: int) -> str:
    if index >= len(args):
        print(f"{flag} requires a value", file=sys.stderr)
        raise SystemExit(1)
    return args[index]
