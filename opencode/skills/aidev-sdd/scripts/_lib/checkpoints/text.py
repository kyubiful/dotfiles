"""Line-oriented text matching that mirrors the grep/sed usage in the shell linter."""
from __future__ import annotations

import re
from functools import lru_cache

_POSIX = (
    ("[:space:]", r"\s"),
    ("[:digit:]", r"\d"),
    ("[:alnum:]", "A-Za-z0-9"),
    ("[:alpha:]", "A-Za-z"),
    ("[:upper:]", "A-Z"),
    ("[:lower:]", "a-z"),
)


def posix(pattern: str) -> str:
    """Translate POSIX character classes to their Python-regex equivalents.

    Matching happens per line (no embedded newlines), so `\\s` is an exact stand-in
    for `[[:space:]]`."""
    for cls, rep in _POSIX:
        pattern = pattern.replace(cls, rep)
    return pattern


@lru_cache(maxsize=512)
def _compile(pattern: str) -> re.Pattern:
    return re.compile(posix(pattern))


def read_lines(path: str) -> list[str]:
    with open(path) as handle:
        return handle.read().splitlines()


def grep_q(pattern: str, path: str) -> bool:
    """grep -Eq: does any line match `pattern`?"""
    rx = _compile(pattern)
    return any(rx.search(line) for line in read_lines(path))


def grep_lines(pattern: str, lines: list[str], invert: bool = False) -> list[str]:
    """grep -E (optionally -v): keep lines that match (or don't match) `pattern`."""
    rx = _compile(pattern)
    return [line for line in lines if bool(rx.search(line)) != invert]


def head1_sub(prefix: str, path: str) -> str:
    """sed -n -E 's/^<prefix>//p' <file> | head -1: first line matching `^prefix`,
    with that prefix removed."""
    rx = _compile("^" + prefix)
    for line in read_lines(path):
        if rx.match(line):
            return rx.sub("", line, count=1)
    return ""
