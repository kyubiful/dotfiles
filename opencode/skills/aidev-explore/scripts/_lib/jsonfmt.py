"""JSON serialization matching detect-repo's exact byte layout.

Nested values are compact (`{"k":v}`), array elements are joined with `", "`, and
strings escape only backslash, double-quote, and newline — replicating the shell helpers.
"""
from __future__ import annotations

import re

_TRIM = re.compile(r"^\s+|\s+$")


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def s(value: str) -> str:
    return '"' + esc(value) + '"'


def b(value: bool) -> str:
    return "true" if value else "false"


def obj(pairs: list[tuple[str, str]]) -> str:
    return "{" + ",".join(f'"{k}":{v}' for k, v in pairs) + "}"


def arr(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def arr_from_lines(values: list[str]) -> str:
    """json_array_from_lines: trim each value, drop empties, quote the rest."""
    quoted = [s(v.strip()) for v in values if v.strip()]
    return arr(quoted)
