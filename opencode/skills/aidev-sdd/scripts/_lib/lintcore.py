"""Fail/require/reject primitives shared by every lint mode."""
from __future__ import annotations

import os

from . import text
from .cli import LintFailure


def fail(message: str, code: int = 1) -> None:
    raise LintFailure(message, code)


def require_file(path: str) -> None:
    if not os.path.isfile(path):
        fail(f"file not found: {path}")


def require_pattern(pattern: str, path: str, message: str) -> None:
    if not text.grep_q(pattern, path):
        fail(message)


def reject_pattern(pattern: str, path: str, message: str) -> None:
    if text.grep_q(pattern, path):
        fail(message)
