"""Read fields from `.aicontext/aicontext.lock`.

The lock is authored by external aicontext tooling with an uncertain internal
shape, so these readers reproduce the original scripts' line-oriented scan
verbatim rather than relying on a YAML object model."""
from __future__ import annotations

import os
import re

_SCALAR = re.compile(r"^[^:]*:[ \t\r\f\v]*")
_TOP_LEVEL = re.compile(r"^[A-Za-z]")


def lock_path(cwd: str | None = None) -> str:
    base = cwd if cwd is not None else os.environ.get("CWD") or os.getcwd()
    return os.path.join(base, ".aicontext", "aicontext.lock")


def _scalar_after_colon(line: str) -> str:
    return _SCALAR.sub("", line)


def extract_sha(resource_name: str, lock: str) -> str:
    """Return the sha for `resource_name`, falling back to the first package sha, else 'null'."""
    if not os.path.isfile(lock):
        return "null"
    lines = _read_lines(lock)

    # Pass 1: resource-level sha.
    in_s = False
    rname = rsha = ""
    result = None
    for line in lines:
        if line.startswith("resources:"):
            in_s = True
            continue
        if in_s and _TOP_LEVEL.match(line):
            in_s = False
        if not in_s:
            continue
        if re.match(r"^  [^ ]", line):
            if rname == resource_name and rsha != "":
                result = rsha
                break
            rname = rsha = ""
            continue
        if line.startswith("    name:"):
            rname = _scalar_after_colon(line)
        elif line.startswith("    sha:"):
            rsha = _scalar_after_colon(line)
    if result is None and rname == resource_name and rsha != "":
        result = rsha
    if result:
        return result

    # Pass 2: first packages.*.sha.
    in_s = False
    for line in lines:
        if line.startswith("packages:"):
            in_s = True
            continue
        if in_s and _TOP_LEVEL.match(line):
            in_s = False
        if not in_s:
            continue
        if line.startswith("    sha:"):
            return _scalar_after_colon(line)

    return "null"


def extract_version_ref(lock: str) -> str:
    """Return the first packages.*.version value (quote-stripped), else 'null'."""
    if not os.path.isfile(lock):
        return "null"
    in_p = False
    for line in _read_lines(lock):
        if line.startswith("packages:"):
            in_p = True
            continue
        if in_p and _TOP_LEVEL.match(line):
            in_p = False
        if in_p and line.startswith("    version:"):
            val = _scalar_after_colon(line)
            val = re.sub(r'^["\']', "", val)
            val = re.sub(r'["\']$', "", val)
            return val or "null"
    return "null"


def _read_lines(path: str) -> list[str]:
    with open(path) as handle:
        return handle.read().splitlines()
