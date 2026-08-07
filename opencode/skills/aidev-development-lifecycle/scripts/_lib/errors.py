"""Errors raised by lifecycle setup operations."""
from __future__ import annotations

from typing import Sequence


class SetupError(Exception):
    """A user-actionable setup or parsing error."""


class CommandError(SetupError):
    """A subprocess failure with its command and captured output."""

    def __init__(self, command: Sequence[str], message: str, output: str = ""):
        self.command = list(command)
        self.output = output.strip()
        rendered = " ".join(self.command)
        detail = f": {self.output}" if self.output else ""
        super().__init__(f"{message}: {rendered}{detail}")
