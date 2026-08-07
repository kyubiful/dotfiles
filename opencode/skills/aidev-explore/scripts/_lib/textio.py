"""Line-oriented file matching that mirrors the grep flags used by the scripts."""
from __future__ import annotations

import re
from pathlib import Path

# Matches absolute macOS and Linux user-home paths within a single line.
# Portable home-directory references such as `~/` and `$HOME/` are allowed.
LOCAL_PATH_RE = re.compile(r"(^|[ \t\r\f\v])/(Users|home)/")


def read_lines(path: str | Path) -> list[str]:
    return Path(path).read_text().splitlines()


def has_fixed_wholeline(path: str | Path, needle: str) -> bool:
    """grep -Fxq: a whole line equals `needle`."""
    return any(line == needle for line in read_lines(path))


def has_fixed_substr(path: str | Path, needle: str) -> bool:
    """grep -Fq: some line contains `needle`."""
    return any(needle in line for line in read_lines(path))


def count_fixed_substr(path: str | Path, needle: str) -> int:
    """grep -Fc: number of lines containing `needle`."""
    return sum(1 for line in read_lines(path) if needle in line)


def has_regex(path: str | Path, pattern: str) -> bool:
    """grep -Eq: some line matches `pattern`."""
    rx = re.compile(pattern)
    return any(rx.search(line) for line in read_lines(path))


def grep_n(path: str | Path, pattern: str) -> list[str]:
    """grep -nE: `lineno:content` for each matching line."""
    rx = re.compile(pattern)
    out: list[str] = []
    for i, line in enumerate(read_lines(path), start=1):
        if rx.search(line):
            out.append(f"{i}:{line}")
    return out
