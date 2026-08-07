"""Mutation engine and line-editing helpers for the sdd-state CLI.

Every mutation edits an in-memory copy of the session state (never a full YAML
reserialize) so formatting and comments survive byte-for-byte, then the result is
linted before the working copy replaces the real file."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import linters, text
from .cli import LintFailure, ToolError

PHASE_NAMES = {
    "bootstrap", "discovery", "functional-spec", "spec-validation",
    "technical-plan", "test-design", "implementation", "spec-verification", "retro",
}


def fail(message: str) -> None:
    raise ToolError(message)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def yaml_scalar(value: str) -> str:
    """Serialize free-form text as a YAML-compatible quoted scalar."""
    return json.dumps(value)


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def state_file_of(directory: str) -> str:
    directory = directory.rstrip("/")
    if not os.path.isdir(directory):
        fail(f"session directory not found: {directory}")
    state = os.path.join(directory, "sdd-state.yml")
    if not os.path.isfile(state):
        fail(f"sdd-state.yml not found in: {directory}")
    return state


def workspace_root_of_session(directory: str) -> str:
    """Resolve the workspace that owns an SDD session.

    Sessions are stored below ``<workspace>/.aicontext/deliverables/sdd/sessions``.
    Walking to the nearest ``.aicontext`` directory keeps resolution independent
    from the process working directory and prevents cross-workspace handoffs.
    """
    # Keep the lexical workspace path: resolving here would lose `.aicontext`
    # when deliverables/ is the supported symlink to an external data root.
    current = Path(os.path.abspath(directory))
    for parent in (current, *current.parents):
        if parent.name == ".aicontext":
            return str(parent.parent)
    raise ValueError(f"session is not inside a .aicontext workspace: {directory}")


def resolve_scoped_path(directory: str, scope: str, path: str) -> str:
    """Resolve a manifest path and prove that it stays inside its declared root."""
    if scope not in ("session", "workspace"):
        raise ValueError(f"invalid path scope: {scope}")
    if not path or os.path.isabs(path):
        raise ValueError(f"path must be non-empty and relative: {path}")
    if scope == "session" and path.startswith("workspace:"):
        raise ValueError("session path must not use the reserved 'workspace:' prefix")
    if ".." in Path(path).parts:
        raise ValueError(f"path must not contain '..': {path}")

    if scope == "session":
        root = os.path.realpath(directory)
        resolved = os.path.realpath(os.path.join(root, path))
    else:
        parts = Path(path).parts
        required_prefix = (".aicontext", "deliverables", "sdd")
        if len(parts) <= len(required_prefix) or parts[:3] != required_prefix:
            raise ValueError(
                "workspace path must be inside .aicontext/deliverables/sdd/: "
                f"{path}"
            )
        workspace = workspace_root_of_session(directory)
        # The SDD root itself may be reached through deliverables/ symlinking to
        # external storage. Trust that root, then reject any nested symlink escape.
        root = os.path.realpath(
            os.path.join(workspace, ".aicontext", "deliverables", "sdd")
        )
        resolved = os.path.realpath(os.path.join(root, *parts[3:]))
    try:
        contained = os.path.commonpath((root, resolved)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"{scope} path escapes its root: {path}")
    return resolved


def encode_artifact_path(scope: str, path: str) -> str:
    """Keep legacy session artifact strings while making workspace scope explicit."""
    return path if scope == "session" else f"workspace:{path}"


def decode_artifact_path(value: str) -> tuple[str, str]:
    if value.startswith("workspace:"):
        return "workspace", value[len("workspace:"):]
    return "session", value


def resolve_state_artifact(directory: str, value: str) -> str:
    scope, path = decode_artifact_path(value)
    return resolve_scoped_path(directory, scope, path)


def require_phase_name(phase: str) -> None:
    if phase not in PHASE_NAMES:
        fail(f"unknown phase: {phase}")


def read_records(path: str) -> list[str]:
    with open(path) as handle:
        data = handle.read()
    records = data.split("\n")
    if records and records[-1] == "":
        records.pop()
    return records


def write_records(path: str, records: list[str]) -> None:
    with open(path, "w") as handle:
        handle.write("\n".join(records) + "\n")


def capture_lint(func, *args) -> tuple[bool, str]:
    """Run a lint function, capturing everything it would emit to stdout/stderr
    plus the `sdd-state:`-prefixed line that the sourced `fail` prints. Returns
    (ok, combined_text_without_trailing_newlines) mirroring `$( (fn) 2>&1 )`."""
    import io
    import contextlib

    buf = io.StringIO()
    ok = True
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            func(*args)
        except LintFailure as err:
            ok = False
            if err.message is not None:
                print(f"sdd-state: {err.message}", file=buf)
    return ok, buf.getvalue().rstrip("\n")


class StateEngine:
    def __init__(self, force: bool = False):
        self.state = ""
        self.work = ""
        self.records: list[str] = []
        self.force = force or os.environ.get("FORCE") == "1"

    def begin(self, directory: str) -> None:
        self.state = state_file_of(directory)
        fd, self.work = tempfile.mkstemp(
            prefix=".sdd-state-",
            suffix=".wip",
            dir=os.path.dirname(self.state),
        )
        os.close(fd)
        shutil.copy2(self.state, self.work)
        self.records = read_records(self.work)

    def _flush(self) -> None:
        write_records(self.work, self.records)

    def discard(self) -> None:
        if self.work and os.path.isfile(self.work) and not os.path.islink(self.work):
            os.remove(self.work)
        self.work = ""

    def commit(self) -> None:
        self._touch_updated_at()
        self._flush()
        ok, out = capture_lint(linters.lint_session_state, self.work)
        if not ok:
            lint_err = out
            if lint_err.startswith("sdd-lint: "):
                lint_err = lint_err[len("sdd-lint: "):]
            if lint_err.startswith("sdd-state: "):
                lint_err = lint_err[len("sdd-state: "):]
            if self.force:
                import sys
                print(
                    f"sdd-state: warning: committing despite lint failure: {lint_err}",
                    file=sys.stderr,
                )
            else:
                self.discard()
                fail(f"mutation rolled back — post-mutation lint failed: {lint_err}")
        os.replace(self.work, self.state)
        self.work = ""

    # -- line-editing helpers (each mirrors an awk block) --------------------

    def _touch_updated_at(self) -> None:
        out = []
        in_session = False
        for line in self.records:
            if re.match(r"^session:", line):
                in_session = True
                out.append(line)
                continue
            if in_session and re.match(r"^\S", line):
                in_session = False
            if in_session and re.match(r"^\s+updated_at:", line):
                out.append(f'  updated_at: "{now_utc()}"')
                continue
            out.append(line)
        self.records = out

    def set_top_scalar(self, key: str, value: str) -> None:
        out = []
        done = False
        anchor = re.compile("^" + key + ":")
        for line in self.records:
            if not done and anchor.match(line):
                out.append(f"{key}: {value}")
                done = True
                continue
            out.append(line)
        if not done:
            fail(f"top-level key not found: {key}")
        self.records = out

    def set_nested_scalar(self, parent: str, child: str, key: str, value: str) -> None:
        out = []
        done = False
        in_parent = in_child = False
        parent_re = re.compile("^" + parent + ":")
        child_re = re.compile("^  " + child + ":")
        key_re = re.compile("^    " + key + ":")
        for line in self.records:
            if re.match(r"^\S", line):
                in_parent = bool(parent_re.match(line))
                in_child = False
            elif in_parent and re.match(r"^  [^\s#-]", line):
                in_child = bool(child_re.match(line))
            if in_parent and in_child and not done and key_re.match(line):
                out.append(f"    {key}: {value}")
                done = True
                continue
            out.append(line)
        if not done:
            fail(f"key not found: {parent}.{child}.{key}")
        self.records = out

    def append_nested_list_item(self, parent: str, child: str, key: str, item: str) -> None:
        out = []
        done = False
        in_parent = in_child = False
        parent_re = re.compile("^" + parent + ":")
        child_re = re.compile("^  " + child + ":")
        key_re = re.compile("^    " + key + ":")
        for line in self.records:
            if re.match(r"^\S", line):
                in_parent = bool(parent_re.match(line))
                in_child = False
            elif in_parent and re.match(r"^  [^\s#-]", line):
                in_child = bool(child_re.match(line))
            if in_parent and in_child and not done and key_re.match(line):
                if re.search(r"\[\]\s*$", line):
                    out.append(f"    {key}:")
                    out.append(f"      - {item}")
                else:
                    out.append(line)
                    out.append(f"      - {item}")
                done = True
                continue
            out.append(line)
        if not done:
            fail(f"list not found: {parent}.{child}.{key}")
        self.records = out

    def nested_list_contains(self, parent: str, child: str, key: str, item: str) -> bool:
        in_parent = in_child = in_list = False
        found = False
        parent_re = re.compile("^" + parent + ":")
        child_re = re.compile("^  " + child + ":")
        key_re = re.compile("^    " + key + ":")
        for line in self.records:
            matched = False
            if re.match(r"^\S", line):
                in_parent = bool(parent_re.match(line))
                in_child = False
            elif in_parent and re.match(r"^  [^\s#-]", line):
                in_child = bool(child_re.match(line))
            if in_parent and in_child and key_re.match(line):
                in_list = True
                matched = True
            elif in_parent and in_child and in_list and re.match(r"^      - ", line):
                value = re.sub(r"^      - ", "", line)
                value = re.sub(r'^["\']|["\']$', "", value)
                if value == item:
                    found = True
                matched = True
            if not matched:
                in_list = False
        return found

    def remove_nested_list_item(self, parent: str, child: str, key: str, item: str) -> bool:
        out = []
        in_parent = in_child = in_list = False
        removed = False
        parent_re = re.compile("^" + parent + ":")
        child_re = re.compile("^  " + child + ":")
        key_re = re.compile("^    " + key + ":")
        for line in self.records:
            matched = False
            if re.match(r"^\S", line):
                in_parent = bool(parent_re.match(line))
                in_child = False
            elif in_parent and re.match(r"^  [^\s#-]", line):
                in_child = bool(child_re.match(line))
            if in_parent and in_child and key_re.match(line):
                in_list = True
                matched = True
            elif in_parent and in_child and in_list and re.match(r"^      - ", line):
                value = re.sub(r"^      - ", "", line)
                value = re.sub(r'^["\']|["\']$', "", value)
                if value == item:
                    removed = True
                    continue
                matched = True
            if not matched:
                in_list = False
            out.append(line)
        self.records = out
        return removed

    def metrics_touch(self, phase: str, op: str) -> None:
        ts = now_utc()
        if not any(re.match(r"^metrics:", line) for line in self.records):
            self.records = _insert_before(self.records, r"^decisions:", ["metrics:", "  phases: []"])

        if _metrics_has_phase(self.records, phase):
            self.records = _metrics_update_entry(self.records, phase, op, ts)
        else:
            started, completed, invocations, rounds = '""', '""', 0, 0
            if op == "start":
                started, invocations = f'"{ts}"', 1
            elif op == "round":
                rounds = 1
            elif op == "complete":
                completed = f'"{ts}"'
            records, found = _metrics_create_entry(
                self.records, phase, started, completed, invocations, rounds
            )
            if not found:
                fail("metrics.phases block not found")
            self.records = records


def _strip_quotes(value: str) -> str:
    return re.sub(r'^["\']|["\']$', "", value)


def _insert_before(records: list[str], anchor: str, new_lines: list[str]) -> list[str]:
    out = []
    done = False
    rx = re.compile(anchor)
    for line in records:
        if not done and rx.match(line):
            out.extend(new_lines)
            done = True
        out.append(line)
    return out


def insert_after(records: list[str], anchor: str, new_lines: list[str]) -> tuple[list[str], bool]:
    out = []
    done = False
    rx = re.compile(anchor)
    for line in records:
        out.append(line)
        if not done and rx.match(line):
            out.extend(new_lines)
            done = True
    return out, done


def replace_orchestration_subblock(records, header: str, new_lines: list[str]) -> list[str]:
    out = []
    in_o = False
    skip = False
    header_re = re.compile(header)
    for line in records:
        if re.match(r"^orchestration:", line):
            in_o = True
            out.append(line)
            continue
        if in_o and re.match(r"^\S", line):
            in_o = False
        if in_o and header_re.match(line):
            out.extend(new_lines)
            skip = True
            continue
        if skip and re.match(r"^    ", line):
            continue
        skip = False
        out.append(line)
    return out


def _metrics_has_phase(records, phase: str) -> bool:
    in_m = False
    entry_re = re.compile(r"^\s*-\s+phase:\s*" + re.escape(phase) + r"\s*$")
    for line in records:
        if re.match(r"^metrics:", line):
            in_m = True
            continue
        if in_m and re.match(r"^\S", line):
            in_m = False
        if in_m and entry_re.match(line):
            return True
    return False


def _metrics_update_entry(records, phase, op, ts) -> list[str]:
    out = []
    in_m = in_entry = False
    entry_re = re.compile(r"^\s*-\s+phase:\s*" + re.escape(phase) + r"\s*$")
    any_phase_re = re.compile(r"^\s*-\s+phase:")

    def emit(key, val):
        return f"      {key}: {val}"

    for line in records:
        if re.match(r"^metrics:", line):
            in_m = True
            out.append(line)
            continue
        if in_m and re.match(r"^\S", line):
            in_m = False
            in_entry = False
        if in_m and any_phase_re.match(line):
            in_entry = bool(entry_re.match(line))
            out.append(line)
            continue
        if in_m and in_entry and re.match(r"^      started_at:", line):
            if op == "start":
                rest = re.sub(r"^      started_at:\s*", "", line)
                if rest in ('""', ""):
                    out.append(emit("started_at", f'"{ts}"'))
                    continue
            out.append(line)
            continue
        if in_m and in_entry and re.match(r"^      completed_at:", line):
            if op == "complete":
                out.append(emit("completed_at", f'"{ts}"'))
                continue
            out.append(line)
            continue
        if in_m and in_entry and re.match(r"^      specialist_invocations:", line):
            if op == "start":
                n = re.sub(r"^      specialist_invocations:\s*", "", line)
                out.append(emit("specialist_invocations", _plus_one(n)))
                continue
            out.append(line)
            continue
        if in_m and in_entry and re.match(r"^      question_rounds:", line):
            if op == "round":
                n = re.sub(r"^      question_rounds:\s*", "", line)
                out.append(emit("question_rounds", _plus_one(n)))
                continue
            out.append(line)
            continue
        out.append(line)
    return out


def _metrics_create_entry(records, phase, started, completed, invocations, rounds):
    out = []
    in_m = False
    done = False
    for line in records:
        if re.match(r"^metrics:", line):
            in_m = True
            out.append(line)
            continue
        if in_m and not done and re.match(r"^\s+phases:", line):
            if re.search(r"\[\]\s*$", line):
                out.append("  phases:")
            else:
                out.append(line)
            out.append(f"    - phase: {phase}")
            out.append(f"      started_at: {started}")
            out.append(f"      completed_at: {completed}")
            out.append(f"      specialist_invocations: {invocations}")
            out.append(f"      question_rounds: {rounds}")
            done = True
            continue
        if in_m and re.match(r"^\S", line):
            in_m = False
        out.append(line)
    return out, done


def _plus_one(value: str) -> str:
    value = value.strip()
    try:
        return str(int(value) + 1)
    except ValueError:
        return str(1)
