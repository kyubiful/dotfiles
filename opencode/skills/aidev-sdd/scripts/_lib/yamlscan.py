"""Line-oriented YAML scanning for the sdd-lint modes (awk/sed-equivalent scanners).

These helpers never parse YAML semantically; they replicate the shell linter's
byte-for-byte matching so behaviour stays identical."""
from __future__ import annotations

import re

from .phases import STANDARD_PHASES, track_mandatory_phases, track_skipped_phases

_COMMENT = re.compile(r"\s+#.*$")
_NONSPACE = re.compile(r"^\S")


def trim_scalar(value: str) -> str:
    value = _COMMENT.sub("", value)
    value = value.strip()
    if value[:1] in ("'", '"'):
        value = value[1:]
    if value[-1:] in ("'", '"'):
        value = value[:-1]
    return value


def is_nullish(value: str) -> bool:
    return trim_scalar(value) in ("", "null", "~")


def require_section_item(parent: str, item: str, lines: list[str]) -> bool:
    in_parent = False
    p = re.compile("^" + parent + ":")
    it = re.compile("^  " + item + ":")
    for line in lines:
        if p.search(line):
            in_parent = True
            continue
        if in_parent and _NONSPACE.match(line):
            in_parent = False
        if in_parent and it.search(line):
            return True
    return False


def nested_value(parent: str, item: str, key: str, lines: list[str]) -> str:
    in_parent = in_item = False
    p = re.compile("^" + parent + ":")
    itemre = re.compile("^  " + item + ":")
    keyre = re.compile("^    " + key + ":")
    keysub = re.compile("^    " + key + r":\s*")
    sibling = re.compile(r"^  \S[^:]*:")
    for line in lines:
        if p.search(line):
            in_parent = True
            continue
        if in_parent and _NONSPACE.match(line):
            in_parent = False
            in_item = False
        if in_parent and itemre.search(line):
            in_item = True
            continue
        if in_item and sibling.match(line):
            in_item = False
        if in_item and keyre.search(line):
            return keysub.sub("", line, count=1)
    return ""


def _session_track(lines: list[str]) -> str:
    for line in lines:
        if re.match(r"^track:", line):
            return trim_scalar(re.sub(r"^track:\s*", "", line, count=1))
    return ""


def session_mandatory_phases(lines: list[str]) -> list[str]:
    """Active phase set for a session. Static tracks use their fixed list; the
    smart track has no predefined set, so its active phases are every standard
    phase not marked skipped in the session state."""
    track = _session_track(lines)
    if track == "smart":
        return [
            p
            for p in STANDARD_PHASES
            if trim_scalar(nested_value("phases", p, "status", lines)) != "skipped"
        ]
    return track_mandatory_phases(track)


def session_skipped_phases(lines: list[str]) -> list[str]:
    track = _session_track(lines)
    if track == "smart":
        return [
            p
            for p in STANDARD_PHASES
            if trim_scalar(nested_value("phases", p, "status", lines)) == "skipped"
        ]
    return track_skipped_phases(track)


def phase_artifact_value(phase: str, artifact: str, lines: list[str]) -> str:
    in_phases = in_phase = in_artifacts = False
    phasere = re.compile("^  " + phase + ":")
    for line in lines:
        if re.match(r"^phases:", line):
            in_phases = True
            continue
        if in_phases and _NONSPACE.match(line):
            return ""
        if in_phases and phasere.search(line):
            in_phase = True
            continue
        if in_phase and re.match(r"^  \S[^:]*:", line):
            in_phase = False
            in_artifacts = False
        if in_phase and re.match(r"^    artifacts:\s*\[\]\s*$", line):
            return ""
        if in_phase and re.match(r"^    artifacts:", line):
            in_artifacts = True
            continue
        if in_artifacts and re.match(r"^    \S", line):
            return ""
        if in_artifacts and re.match(r"^      -\s*", line):
            value = re.sub(r"^      -\s*", "", line)
            value = _COMMENT.sub("", value)
            value = value.strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = value[1:-1]
            basename = value.split("/")[-1]
            if value == artifact or basename == artifact:
                return value
    return ""


def artifact_value(artifact: str, lines: list[str]) -> str:
    for phase in STANDARD_PHASES:
        value = phase_artifact_value(phase, artifact, lines)
        if value != "":
            return value
    return ""


def parse_phase_artifact_entries(lines: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    in_phase = in_artifacts = False
    in_phases = False
    phase = ""
    for line in lines:
        if re.match(r"^phases:", line):
            in_phases = True
            continue
        if in_phases and _NONSPACE.match(line):
            break
        if in_phases and re.match(r"^  \S[^:]*:", line):
            name = re.sub(r"^  ", "", line)
            name = re.sub(r":.*", "", name)
            phase = name
            in_phase = True
            in_artifacts = False
            continue
        if in_phase and re.match(r"^    artifacts:\s*\[\]\s*$", line):
            out.append((phase, ""))
            in_artifacts = False
            continue
        if in_phase and re.match(r"^    artifacts:", line):
            in_artifacts = True
            continue
        if in_artifacts and re.match(r"^    \S", line):
            in_artifacts = False
            continue
        if in_artifacts and re.match(r"^      -\s*", line):
            value = re.sub(r"^      -\s*", "", line)
            out.append((phase, value))
    return out


def parse_state_specs(lines: list[str]) -> list[tuple[str, str, str]]:
    """Return ``(path, scope, relation)`` entries.

    States created before scoped references omit ``scope``; those persisted
    session-local paths remain valid and are interpreted as ``session``.
    """
    out: list[tuple[str, str, str]] = []
    in_specs = False
    state = {"started": False, "path": "", "scope": "session", "relation": ""}

    def flush():
        if state["started"]:
            out.append((state["path"], state["scope"], state["relation"]))
            state["path"] = ""
            state["scope"] = "session"
            state["relation"] = ""
            state["started"] = False

    for line in lines:
        if re.match(r"^specs:", line):
            in_specs = True
            continue
        if in_specs and _NONSPACE.match(line):
            flush()
            break
        if in_specs and re.match(r"^  -\s*", line):
            flush()
            state["started"] = True
            rest = re.sub(r"^  -\s*", "", line)
            if re.match(r"^path:", rest):
                state["path"] = re.sub(r"^path:\s*", "", rest)
            elif re.match(r"^scope:", rest):
                state["scope"] = re.sub(r"^scope:\s*", "", rest)
            elif re.match(r"^relation:", rest):
                state["relation"] = re.sub(r"^relation:\s*", "", rest)
            continue
        if in_specs and state["started"] and re.match(r"^    path:", line):
            state["path"] = re.sub(r"^    path:\s*", "", line)
            continue
        if in_specs and state["started"] and re.match(r"^    scope:", line):
            state["scope"] = re.sub(r"^    scope:\s*", "", line)
            continue
        if in_specs and state["started"] and re.match(r"^    relation:", line):
            state["relation"] = re.sub(r"^    relation:\s*", "", line)
            continue
    else:
        flush()
    return out


def parse_contract_entries(lines: list[str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    in_contracts = False
    state = {"started": False, "id": "", "path": "", "sha256": ""}

    def flush():
        if state["started"]:
            out.append((state["id"], state["path"], state["sha256"]))
            state["id"] = ""
            state["path"] = ""
            state["sha256"] = ""
            state["started"] = False

    for line in lines:
        if re.match(r"^contracts:", line):
            in_contracts = True
            continue
        if in_contracts and _NONSPACE.match(line):
            flush()
            break
        if in_contracts and re.match(r"^  -\s*", line):
            flush()
            state["started"] = True
            rest = re.sub(r"^  -\s*", "", line)
            if re.match(r"^id:", rest):
                state["id"] = re.sub(r"^id:\s*", "", rest)
            elif re.match(r"^path:", rest):
                state["path"] = re.sub(r"^path:\s*", "", rest)
            elif re.match(r"^sha256:", rest):
                state["sha256"] = re.sub(r"^sha256:\s*", "", rest)
            continue
        if in_contracts and state["started"] and re.match(r"^    id:", line):
            state["id"] = re.sub(r"^    id:\s*", "", line)
            continue
        if in_contracts and state["started"] and re.match(r"^    path:", line):
            state["path"] = re.sub(r"^    path:\s*", "", line)
            continue
        if in_contracts and state["started"] and re.match(r"^    sha256:", line):
            state["sha256"] = re.sub(r"^    sha256:\s*", "", line)
            continue
    else:
        flush()
    return out


def phase_declares_artifacts(phase: str, lines: list[str]) -> bool:
    in_phases = in_phase = False
    phasere = re.compile("^  " + phase + ":")
    for line in lines:
        if re.match(r"^phases:", line):
            in_phases = True
            continue
        if in_phases and _NONSPACE.match(line):
            return False
        if in_phases and phasere.search(line):
            in_phase = True
            continue
        if in_phase and re.match(r"^  \S[^:]*:", line):
            return False
        if in_phase and re.match(r"^    artifacts:", line):
            return True
    return False


def gate_has_evidence(phase: str, lines: list[str]) -> bool:
    in_gates = in_phase = in_evidence = False
    phasere = re.compile("^  " + phase + ":")
    for line in lines:
        if re.match(r"^gates:", line):
            in_gates = True
            continue
        if in_gates and _NONSPACE.match(line):
            in_gates = False
            in_phase = False
            in_evidence = False
        if in_gates and phasere.search(line):
            in_phase = True
            continue
        if in_phase and re.match(r"^  \S[^:]*:", line):
            in_phase = False
            in_evidence = False
        if in_phase and re.match(r"^    evidence:\s*\[[^\]]+\]", line):
            return True
        if in_phase and re.match(r"^    evidence:\s*\[\s*\]", line):
            continue
        if in_phase and re.match(r"^    evidence:\s*$", line):
            in_evidence = True
            continue
        if in_phase and in_evidence and re.match(r"^      -\s+\S", line):
            return True
        if in_phase and in_evidence and re.match(r"^    \S", line):
            in_evidence = False
    return False


def pending_delegation_active(lines: list[str]) -> bool:
    in_orch = False
    for line in lines:
        if re.match(r"^orchestration:", line):
            in_orch = True
            continue
        if in_orch and _NONSPACE.match(line):
            in_orch = False
        if in_orch and re.match(r"^  pending_delegation:", line):
            value = re.sub(r"^  pending_delegation:\s*", "", line)
            if value == "" or not re.match(r"^(null|~)$", value):
                return True
            return False
    return False


def pending_delegation_value(key: str, lines: list[str]) -> str:
    in_orch = in_pending = False
    keyre = re.compile("^    " + key + ":")
    keysub = re.compile("^    " + key + r":\s*")
    for line in lines:
        if re.match(r"^orchestration:", line):
            in_orch = True
            continue
        if in_orch and _NONSPACE.match(line):
            in_orch = False
            in_pending = False
        if in_orch and re.match(r"^  pending_delegation:", line):
            value = re.sub(r"^  pending_delegation:\s*", "", line)
            if value == "" or not re.match(r"^(null|~)$", value):
                in_pending = True
            continue
        if in_pending and re.match(r"^  \S[^:]*:", line):
            in_pending = False
        if in_pending and keyre.search(line):
            return keysub.sub("", line, count=1)
    return ""
