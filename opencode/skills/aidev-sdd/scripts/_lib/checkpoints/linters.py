"""All sdd-lint modes with strict output parity."""
from __future__ import annotations

import os
import re
from pathlib import Path
import sys
from dataclasses import dataclass

import yaml

from . import state, text
from .cli import LintFailure
from .lintcore import fail, reject_pattern, require_file, require_pattern
from .phases import (
    STANDARD_PHASES,
    expected_phase_artifacts,
    phase_order,
    track_mandatory_phases,
    track_skipped_phases,
)
from .timestamps import (
    validate_current_timestamp_scalar,
    validate_decisions_timestamps,
)
from .yamlscan import (
    artifact_value,
    gate_has_evidence,
    is_nullish,
    nested_value,
    parse_contract_entries,
    parse_phase_artifact_entries,
    parse_state_specs,
    pending_delegation_active,
    pending_delegation_value,
    phase_artifact_value,
    phase_declares_artifacts,
    require_section_item,
    session_mandatory_phases,
    trim_scalar,
)


def _top_scalar(name: str, lines: list[str]) -> str:
    anchor = re.compile("^" + name + ":")
    strip = re.compile("^" + name + r":\s*")
    for line in lines:
        if anchor.match(line):
            return strip.sub("", line, count=1)
    return ""


def _indented_scalar(name: str, lines: list[str]) -> str:
    anchor = re.compile(r"^\s+" + name + ":")
    strip = re.compile(r"^\s+" + name + r":\s*")
    for line in lines:
        if anchor.match(line):
            return strip.sub("", line, count=1)
    return ""


def _require_nested_pattern(parent, item, key, pattern, lines, message):
    value = trim_scalar(nested_value(parent, item, key, lines))
    if not value or not re.match(r"^(" + pattern + r")$", value):
        fail(message)


def _require_decided_gate_evidence(phase, lines):
    status = trim_scalar(nested_value("gates", phase, "status", lines))
    if status == "pending":
        return
    if not gate_has_evidence(phase, lines):
        fail(f"session gate {phase} has status {status} but no evidence")


def _artifact_phase_requires_file(phase, lines):
    phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
    gate_status = trim_scalar(nested_value("gates", phase, "status", lines))
    if phase_status == "complete":
        return True
    if re.match(r"^(pass|conditional-pass|fail)$", gate_status):
        return True
    return False


def _validate_smart_phase_contract(lines):
    # The smart track's active phase set is chosen per session and persisted via
    # the phases.<phase>.status: skipped markers. Enforce the immutable core, the
    # selection dependencies, and that current_phase is active.
    session_status = trim_scalar(_top_scalar("status", lines))
    current_phase = trim_scalar(_top_scalar("current_phase", lines))

    for phase in ("bootstrap", "implementation", "spec-verification", "retro"):
        phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
        gate_status = trim_scalar(nested_value("gates", phase, "status", lines))
        if phase_status == "skipped":
            fail(f"smart track: core phase {phase} cannot be skipped")
        if gate_status == "skipped":
            fail(f"smart track: core gate {phase} cannot be skipped")

    fs = trim_scalar(nested_value("phases", "functional-spec", "status", lines))
    sv = trim_scalar(nested_value("phases", "spec-validation", "status", lines))
    td = trim_scalar(nested_value("phases", "test-design", "status", lines))
    if sv != "skipped" and fs == "skipped":
        fail("smart track: spec-validation requires functional-spec (functional-spec is skipped)")
    if td != "skipped" and fs == "skipped":
        fail("smart track: test-design requires functional-spec (functional-spec is skipped)")

    phase_status = trim_scalar(nested_value("phases", current_phase, "status", lines))
    if phase_status == "skipped":
        fail(f"smart track: current_phase {current_phase} is skipped")

    if session_status == "complete":
        for phase in session_mandatory_phases(lines):
            phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
            gate_status = trim_scalar(nested_value("gates", phase, "status", lines))
            if phase_status != "complete":
                fail(f"smart track: phase {phase} must be complete when session status is complete")
            if gate_status not in ("pass", "conditional-pass"):
                fail(f"smart track: gate {phase} must be pass or conditional-pass when session status is complete")


def _validate_track_phase_contract(lines, track):
    if not track:
        return
    if track == "smart":
        _validate_smart_phase_contract(lines)
        return
    session_status = trim_scalar(_top_scalar("status", lines))
    current_phase = trim_scalar(_top_scalar("current_phase", lines))

    for phase in track_skipped_phases(track):
        phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
        gate_status = trim_scalar(nested_value("gates", phase, "status", lines))
        if phase_status != "skipped":
            fail(f"session phase {phase} must be skipped for track {track}")
        if gate_status != "skipped":
            fail(f"session gate {phase} must be skipped for track {track}")
        if current_phase == phase:
            fail(f"session current_phase {current_phase} is skipped for track {track}")

    for phase in track_mandatory_phases(track):
        phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
        gate_status = trim_scalar(nested_value("gates", phase, "status", lines))
        if phase_status == "skipped":
            fail(f"session phase {phase} is mandatory for track {track} and cannot be skipped")
        if gate_status == "skipped":
            fail(f"session gate {phase} is mandatory for track {track} and cannot be skipped")
        if session_status == "complete":
            if phase_status != "complete":
                fail(
                    f"session phase {phase} must be complete when session status "
                    f"is complete for track {track}"
                )
            if gate_status not in ("pass", "conditional-pass"):
                fail(
                    f"session gate {phase} must be pass or conditional-pass when "
                    f"session status is complete for track {track}"
                )


def _validate_session_specs(lines, state_dir):
    current_phase = trim_scalar(_top_scalar("current_phase", lines))
    session_status = trim_scalar(_top_scalar("status", lines))
    track = trim_scalar(_top_scalar("track", lines))
    spec_required = False
    if track == "exhaustive":
        if session_status == "complete" or phase_order(current_phase) >= phase_order(
            "spec-validation"
        ):
            spec_required = True

    spec_count = 0
    for spec_path, spec_scope, spec_relation in parse_state_specs(lines):
        spec_path = trim_scalar(spec_path)
        spec_scope = trim_scalar(spec_scope) or "session"
        spec_relation = trim_scalar(spec_relation)
        if spec_path == "" and spec_relation == "":
            continue
        spec_count += 1
        if not spec_path:
            fail("session spec entry must declare path")
        if spec_scope not in ("session", "workspace"):
            fail(f"spec scope must be session or workspace (got: {spec_scope})")
        if spec_relation not in ("primary", "dependency", "reference"):
            fail(
                "spec relation must be primary, dependency, or reference "
                f"(got: {spec_relation})"
            )
        try:
            resolved = state.resolve_scoped_path(state_dir, spec_scope, spec_path)
        except ValueError as err:
            fail(str(err))
        if spec_required and not os.path.isfile(resolved):
            fail(f"spec path not found: {spec_scope}:{spec_path}")

    canonical_deletion_recorded = (
        current_phase == "retro" and _canonical_spec_deletion_recorded(lines)
    )
    if spec_required and spec_count == 0 and not canonical_deletion_recorded:
        fail("session must declare at least one spec path once spec-validation starts")


def _canonical_spec_deletion_recorded(lines):
    return any(
        re.match(r'^\s+decision:\s*["\']?Canonical spec deleted:', line)
        for line in lines
    )


def _validate_session_artifacts(lines, state_dir):
    for phase, value in parse_phase_artifact_entries(lines):
        value = trim_scalar(value)
        if value == "":
            continue
        if phase not in STANDARD_PHASES:
            fail(f"session artifact is listed under unknown phase: {phase}")
        if is_nullish(value):
            fail(f"session phase artifact must be a concrete path: {phase} -> {value}")
        try:
            resolved = state.resolve_state_artifact(state_dir, value)
        except ValueError as err:
            fail(str(err))
        if not os.path.isfile(resolved):
            fail(f"session phase artifact path not found: {phase} -> {value}")

    for phase in STANDARD_PHASES:
        if not phase_declares_artifacts(phase, lines):
            fail(f"session phase {phase} must declare artifacts")
        if not _artifact_phase_requires_file(phase, lines):
            continue
        for expected in expected_phase_artifacts(phase):
            if not expected:
                continue
            value = trim_scalar(phase_artifact_value(phase, expected, lines))
            if not value:
                fail(
                    f"session phase {phase} must list artifact {expected} once "
                    "the phase is decided"
                )
        if phase == "bootstrap" and os.path.isfile(os.path.join(state_dir, "contracts.yml")):
            value = trim_scalar(phase_artifact_value("bootstrap", "contracts.yml", lines))
            if not value:
                fail(
                    "session phase bootstrap must list artifact contracts.yml "
                    "when the contract manifest exists"
                )


def _lint_remediation_loop(lines):
    if not any(re.match(r"^  remediation_loop:", line) for line in lines):
        return
    maxv = trim_scalar(nested_value("orchestration", "remediation_loop", "max_iterations", lines))
    iters = trim_scalar(nested_value("orchestration", "remediation_loop", "iterations", lines))
    target = trim_scalar(nested_value("orchestration", "remediation_loop", "last_target", lines))
    if not re.match(r"^[0-9]+$", maxv):
        fail(
            "orchestration.remediation_loop.max_iterations must be a non-negative "
            f"integer (got: {maxv or 'unset'})"
        )
    if not re.match(r"^[0-9]+$", iters):
        fail(
            "orchestration.remediation_loop.iterations must be a non-negative "
            f"integer (got: {iters or 'unset'})"
        )
    if int(iters) > int(maxv):
        fail(
            f"orchestration.remediation_loop.iterations ({iters}) must not exceed "
            f"max_iterations ({maxv})"
        )
    if target not in ("null", "~", "implementation", "technical-plan", "test-design"):
        fail(
            "orchestration.remediation_loop.last_target must be null, implementation, "
            f"technical-plan, or test-design (got: {target})"
        )


@dataclass(frozen=True)
class _EnvelopeSummary:
    kind: str
    fields: dict[str, str]
    question_count: int
    title_found: bool = True


_MARKDOWN_ENVELOPE_FIELDS = re.compile(
    r"^- \*\*(Schema|Agent|Phase|Status|Gate):\*\*\s*`?(.+?)`?\s*$"
)
_LEGACY_YAML_ENVELOPE_FIELDS = re.compile(
    r"^  (schema_version|agent|phase|status|gate_recommendation):\s*(.+)$"
)
_LEGACY_YAML_FIELD_NAMES = {
    "schema_version": "schema",
    "gate_recommendation": "gate",
}


def _summarize_markdown_envelope(lines):
    fields = {}
    question_count = 0
    in_questions = False
    title_found = False

    for line in lines:
        if line == "# Subagent Question Envelope":
            title_found = True
            continue
        match = _MARKDOWN_ENVELOPE_FIELDS.match(line)
        if match:
            fields[match.group(1).lower()] = match.group(2).strip("` ")
            continue
        if line == "## Questions":
            in_questions = True
            continue
        if in_questions and line.startswith("## "):
            in_questions = False
            continue
        if in_questions and re.match(r"^###\s+\S", line):
            question_count += 1

    return _EnvelopeSummary("markdown", fields, question_count, title_found)


def _summarize_legacy_yaml_envelope(lines):
    if not any(re.match(r"^subagent-question-envelope:", line) for line in lines):
        return _EnvelopeSummary("legacy-yaml", {}, 0)
    fields = {}
    in_env = False
    in_questions = False
    question_count = 0
    for line in lines:
        if re.match(r"^subagent-question-envelope:", line):
            in_env = True
            continue
        if in_env and re.match(r"^\S", line):
            in_env = False
        if not in_env:
            continue
        match = _LEGACY_YAML_ENVELOPE_FIELDS.match(line)
        if match:
            key = _LEGACY_YAML_FIELD_NAMES.get(match.group(1), match.group(1))
            fields[key] = match.group(2).strip('" ')
        if re.match(r"^  questions:", line):
            in_questions = True
            continue
        if in_questions and re.match(r"^\s+- ", line):
            question_count += 1
            continue
        if in_questions and re.match(r"^\s+[^-]", line):
            break
    return _EnvelopeSummary("legacy-yaml", fields, question_count)


def _read_envelope_summary(artifact_path):
    lines = text.read_lines(artifact_path)
    if artifact_path.endswith(".md"):
        return _summarize_markdown_envelope(lines)
    if artifact_path.endswith(".yml"):
        return _summarize_legacy_yaml_envelope(lines)
    return _EnvelopeSummary("unsupported", {}, 0)


def _resolve_pending_envelope_path(session_dir, artifact_path):
    if os.path.isabs(artifact_path):
        return artifact_path
    if artifact_path.startswith(".aicontext/"):
        current = Path(os.path.abspath(session_dir))
        workspace = next((parent.parent for parent in (current, *current.parents) if parent.name == ".aicontext"), None)
        if workspace is None:
            return ""
        return os.path.join(workspace, artifact_path)
    return os.path.join(session_dir, artifact_path)


def _pending_delegation_has_open_questions(state_lines, session_dir):
    artifact_path = trim_scalar(pending_delegation_value("envelope_artifact_path", state_lines))
    if not artifact_path or artifact_path == "null":
        return False
    artifact_path = _resolve_pending_envelope_path(session_dir, artifact_path)
    if not os.path.isfile(artifact_path):
        return False
    summary = _read_envelope_summary(artifact_path)
    return summary.title_found and summary.question_count > 0


def _lint_envelope_artifact(artifact_path, expected_agent, expected_phase):
    if not os.path.isfile(artifact_path):
        fail(f"envelope artifact not found: {artifact_path}")
    summary = _read_envelope_summary(artifact_path)
    msgs = []
    if summary.kind == "unsupported":
        msgs.append("unsupported_format")
    if not summary.title_found:
        msgs.append("bad_title")

    schema = summary.fields.get("schema")
    agent = summary.fields.get("agent")
    phase = summary.fields.get("phase")
    status = summary.fields.get("status")
    gate = summary.fields.get("gate")

    if not schema:
        msgs.append("missing_schema")
    if agent != expected_agent:
        msgs.append("agent_mismatch")
    if phase != expected_phase:
        msgs.append("phase_mismatch")
    if status != "needs_user_input":
        msgs.append("bad_status")
    if gate != "paused":
        msgs.append("bad_gate")
    if summary.question_count == 0:
        msgs.append("missing_questions")

    mapping = {
        "unsupported_format": "envelope artifact must use .md or legacy .yml format",
        "bad_title": "Markdown envelope artifact must start with '# Subagent Question Envelope'",
        "agent_mismatch": "envelope artifact agent does not match pending_delegation.agent",
        "phase_mismatch": "envelope artifact phase does not match pending_delegation.phase",
        "bad_status": "envelope artifact status must be needs_user_input",
        "bad_gate": "envelope artifact gate_recommendation must be paused",
        "missing_schema": "envelope artifact missing schema_version",
        "missing_questions": "envelope artifact must contain at least one question",
    }
    for msg in msgs:
        if msg in mapping:
            fail(mapping[msg])


def _lint_pending_delegation(lines, session_dir):
    if not pending_delegation_active(lines):
        return
    current_phase = trim_scalar(_top_scalar("current_phase", lines))
    phase = trim_scalar(pending_delegation_value("phase", lines))
    agent = trim_scalar(pending_delegation_value("agent", lines))
    round_ = trim_scalar(pending_delegation_value("round", lines))
    envelope_artifact_path = trim_scalar(
        pending_delegation_value("envelope_artifact_path", lines)
    )
    phase_status = trim_scalar(nested_value("phases", current_phase, "status", lines))
    gate_status = trim_scalar(nested_value("gates", current_phase, "status", lines))

    if phase != current_phase:
        fail("pending delegation phase must match current_phase")
    if not agent or agent == "null":
        fail("pending delegation must declare agent")
    if not re.match(r"^[1-9][0-9]*$", round_):
        fail("pending delegation round must be a positive integer")
    if not envelope_artifact_path or envelope_artifact_path == "null":
        fail("pending delegation must declare envelope_artifact_path")
    resolved_envelope = _resolve_pending_envelope_path(session_dir, envelope_artifact_path)
    if not _pending_delegation_has_open_questions(lines, session_dir):
        fail(
            "pending delegation envelope artifact must contain "
            "subagent-question-envelope with non-empty questions"
        )
    if phase_status != "blocked":
        fail(f"state phase {current_phase} must be blocked while pending delegation exists")
    if gate_status != "paused":
        fail(f"state gate {current_phase} must be paused while pending delegation exists")

    _lint_envelope_artifact(resolved_envelope, agent, phase)


def _validate_yaml_syntax(file):
    try:
        with open(file) as handle:
            yaml.safe_load(handle)
    except yaml.YAMLError as error:
        problem = getattr(error, "problem", None) or "invalid YAML syntax"
        mark = getattr(error, "problem_mark", None)
        if mark is not None:
            problem = f"{problem} at line {mark.line + 1}, column {mark.column + 1}"
        fail(f"session state is not valid YAML: {problem}")


def lint_session_state(file):
    require_file(file)
    _validate_yaml_syntax(file)

    require_pattern(r"^schema_version:[[:space:]]*2", file, "session state must declare schema_version: 2")
    require_pattern(r"^session:", file, "session state must declare session block")
    require_pattern(r"^[[:space:]]+id:[[:space:]]*[^[:space:]]+", file, "session must declare id")
    require_pattern(r"^[[:space:]]+name:[[:space:]]*[^[:space:]]+", file, "session must declare name")
    require_pattern(r'^[[:space:]]+date:[[:space:]]*"?[0-9]{8}"?', file, "session must declare date in YYYYMMDD format")
    require_pattern(r"^[[:space:]]+created_at:[[:space:]]*[^[:space:]]+", file, "session must declare created_at")
    require_pattern(r"^[[:space:]]+updated_at:[[:space:]]*[^[:space:]]+", file, "session must declare updated_at")
    require_pattern(r"^status:[[:space:]]*(active|paused|complete|cancelled)", file, "session status must be active, paused, complete, or cancelled")
    require_pattern(r"^track:[[:space:]]*(simple|moderate|complex|exhaustive|smart)", file, "session must declare a valid track")
    require_pattern(r"^track_classification:", file, "session state must declare track_classification")
    require_pattern(r"^[[:space:]]+decided_by:[[:space:]]*[^[:space:]]+", file, "track_classification must declare decided_by")
    require_pattern(r"^[[:space:]]+decided_at:[[:space:]]*[^[:space:]]+", file, "track_classification must declare decided_at")
    require_pattern(r"^[[:space:]]+rationale:[[:space:]]*[^[:space:]]+", file, "track_classification must declare rationale")
    require_pattern(r"^[[:space:]]+signals:", file, "track_classification must declare signals")
    require_pattern(r"^current_phase:[[:space:]]*(bootstrap|discovery|functional-spec|spec-validation|technical-plan|test-design|implementation|spec-verification|retro)", file, "session current_phase is not a known SDD phase")
    require_pattern(r"^phases:", file, "session state must declare phases")
    require_pattern(r"^gates:", file, "session state must declare gates")
    require_pattern(r"^specs:", file, "session state must declare specs[]")
    require_pattern(r"^orchestration:", file, "session state must declare orchestration")
    require_pattern(r"^[[:space:]]+workspace_preflight:", file, "session orchestration must declare workspace_preflight")
    require_pattern(r"^[[:space:]]+pending_delegation:", file, "session orchestration must declare pending_delegation")
    require_pattern(r"^decisions:", file, "session state must declare decisions")

    lines = text.read_lines(file)
    track_value = trim_scalar(_top_scalar("track", lines))
    current_phase = trim_scalar(_top_scalar("current_phase", lines))
    created_at = trim_scalar(_indented_scalar("created_at", lines))
    updated_at = trim_scalar(_indented_scalar("updated_at", lines))
    decided_at = trim_scalar(_indented_scalar("decided_at", lines))

    validate_current_timestamp_scalar(created_at, "session.created_at")
    validate_current_timestamp_scalar(updated_at, "session.updated_at")
    validate_current_timestamp_scalar(decided_at, "track_classification.decided_at")

    for phase in STANDARD_PHASES:
        if not require_section_item("phases", phase, lines):
            fail(f"session phases must include {phase}")
        _require_nested_pattern(
            "phases", phase, "status",
            "pending|in-progress|complete|skipped|blocked", lines,
            f"session phase {phase} must declare a valid status",
        )
        phase_status = trim_scalar(nested_value("phases", phase, "status", lines))
        if phase_status == "complete":
            phase_completed_at = trim_scalar(nested_value("phases", phase, "completed_at", lines))
            validate_current_timestamp_scalar(phase_completed_at, f"phases.{phase}.completed_at")
        if not require_section_item("gates", phase, lines):
            fail(f"session gates must include {phase}")
        _require_nested_pattern(
            "gates", phase, "status",
            "pending|pass|fail|conditional-pass|paused|skipped", lines,
            f"session gate {phase} must declare a valid status",
        )
        _require_decided_gate_evidence(phase, lines)

    validate_decisions_timestamps(lines)

    if not require_section_item("phases", current_phase, lines):
        fail(f"session current_phase {current_phase} is missing from phases")
    if not require_section_item("gates", current_phase, lines):
        fail(f"session current_phase {current_phase} is missing from gates")

    state_dir = os.path.realpath(os.path.dirname(file) or ".")
    _validate_track_phase_contract(lines, track_value)
    _validate_session_artifacts(lines, state_dir)
    _validate_session_specs(lines, state_dir)
    _lint_pending_delegation(lines, os.path.dirname(file))
    _lint_remediation_loop(lines)


def lint_spec_package(file):
    require_file(file)
    require_pattern(r"^schema_version:[[:space:]]*[0-9]+", file, "spec must declare schema_version")
    require_pattern(r"^# .+", file, "spec must have a title heading")
    require_pattern(r"^## Purpose", file, "spec must include Purpose section")
    require_pattern(r"^## Scope", file, "spec must include Scope section")
    require_pattern(r"^## Out Of Scope", file, "spec must include Out Of Scope section")
    require_pattern(r"^## Acceptance Criteria", file, "spec must include Acceptance Criteria section")
    require_pattern(r"^## Edge Cases", file, "spec must include Edge Cases section")
    require_pattern(r"^## Error Scenarios", file, "spec must include Error Scenarios section")
    require_pattern(r"^## Risks And Assumptions", file, "spec must include Risks And Assumptions section")
    require_pattern(r"AC-[0-9]+", file, "spec must have at least one acceptance criterion (AC-N)")
    reject_pattern(r"\[AIDEV_TODO\]", file, "spec must not contain pending placeholders")


def _check_backlog_publication(file):
    lines = text.read_lines(file)
    errors = []
    state = {"have_id": False, "id": "", "kind": "", "decision": "", "sync": "", "iurl": "", "inum": ""}

    def flush():
        if not state["have_id"]:
            return
        _id, kind, decision = state["id"], state["kind"], state["decision"]
        sync, iurl, inum = state["sync"], state["iurl"], state["inum"]
        if decision == "":
            errors.append(f"sdd-lint: backlog: item {_id} is missing publish_decision")
        elif decision not in ("pending", "approved", "declined", "not-applicable"):
            errors.append(f"sdd-lint: backlog: item {_id} has invalid publish_decision: {decision}")
        if decision == "approved":
            if kind in ("unchanged", "removed"):
                errors.append(
                    f"sdd-lint: backlog: item {_id} is publish_decision: approved but "
                    f"change_kind: {kind} maps to no GitHub action"
                )
            else:
                if sync != "synced":
                    shown = "unset" if sync == "" else sync
                    errors.append(
                        f"sdd-lint: backlog: item {_id} was approved for publish but "
                        f"sync_status is {shown} (expected synced)"
                    )
                if iurl == "" and inum == "":
                    errors.append(
                        f"sdd-lint: backlog: item {_id} was approved for publish but "
                        "has no issue_url/issue_number evidence"
                    )

    for line in lines:
        if re.match(r"^\s*-\s+id:", line):
            flush()
            value = re.sub(r"^\s*-\s+id:\s*", "", line)
            value = re.sub(r"\s+$", "", value)
            state.update(have_id=True, id=value, kind="", decision="", sync="", iurl="", inum="")
            continue
        if re.match(r"^\s+change_kind:", line):
            state["kind"] = re.sub(r"\s+$", "", re.sub(r"^\s+change_kind:\s*", "", line))
            continue
        if re.match(r"^\s+publish_decision:", line):
            state["decision"] = re.sub(r"\s+$", "", re.sub(r"^\s+publish_decision:\s*", "", line))
            continue
        if re.match(r"^\s+sync_status:", line):
            state["sync"] = re.sub(r"\s+$", "", re.sub(r"^\s+sync_status:\s*", "", line))
            continue
        if re.match(r"^\s+issue_url:", line):
            value = re.sub(r"\s+$", "", re.sub(r"^\s+issue_url:\s*", "", line))
            state["iurl"] = "" if value == "null" else value
            continue
        if re.match(r"^\s+issue_number:", line):
            value = re.sub(r"\s+$", "", re.sub(r"^\s+issue_number:\s*", "", line))
            state["inum"] = "" if value == "null" else value
            continue
    flush()

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        fail("backlog publish decisions are not evidenced for one or more approved items")


def lint_backlog(file):
    require_file(file)
    require_pattern(r"^schema_version:[[:space:]]*2", file, "backlog must declare schema_version: 2")
    require_pattern(r"^session:[[:space:]]*[^[:space:]]+", file, "backlog must declare session")
    require_pattern(r"^source:[[:space:]]*[^[:space:]]*sessions/[^[:space:]]+", file, "backlog must declare a session source path")
    require_pattern(r"^backlog_items:", file, "backlog must declare backlog_items")
    require_pattern(r"^[[:space:]]+- id:[[:space:]]*[^[:space:]]+", file, "backlog item must declare id")
    require_pattern(r"^[[:space:]]+type:[[:space:]]*(user-story|bug|spike)", file, "backlog item type must be user-story, bug, or spike")
    require_pattern(r"^[[:space:]]+title:[[:space:]]*[^[:space:]]+", file, "backlog item must declare title")
    require_pattern(r"^[[:space:]]+source_spec:[[:space:]]*[^[:space:]]+", file, "backlog item must declare source_spec")
    require_pattern(r"^[[:space:]]+change_kind:[[:space:]]*(new|modified|unchanged|removed)", file, "backlog item change_kind must be new, modified, unchanged, or removed")
    require_pattern(r"^[[:space:]]+github:", file, "backlog item must declare github block")
    require_pattern(r"^[[:space:]]+publish_decision:[[:space:]]*(pending|approved|declined|not-applicable)", file, "backlog item must declare publish_decision (pending|approved|declined|not-applicable)")
    reject_pattern(r"\[AIDEV_TODO\]", file, "backlog must not contain pending placeholders")
    _check_backlog_publication(file)


def lint_trace(file):
    require_file(file)
    require_pattern(r"^# SDD Trace", file, "trace must start with # SDD Trace")
    require_pattern(r"^## Session", file, "trace must include Session section")
    require_pattern(r"^## Implementation Trace", file, "trace must include Implementation Trace section")
    require_pattern(r"^## Verification Trace", file, "trace must include Verification Trace section")

    lines = text.read_lines(file)
    heading = re.compile(r"^## .*Trace\s*$")
    known = re.compile(
        r"^## (Input Contract|Acceptance Criteria|Backlog|Technical Plan|Test Design|"
        r"Implementation|Verification|PR / Review) Trace\s*$"
    )
    for line in lines:
        if heading.match(line) and not known.match(line):
            fail(f"trace contains unknown section: {line}")


_TRACE_SECTION_PHASE = {
    "Session": "functional-spec",
    "Input Contract Trace": "spec-validation",
    "Acceptance Criteria Trace": "functional-spec",
    "Backlog Trace": "spec-validation",
    "Technical Plan Trace": "technical-plan",
    "Test Design Trace": "test-design",
    "Implementation Trace": "implementation",
    "Verification Trace": "spec-verification",
    "PR / Review Trace": "spec-verification",
}


def lint_trace_gate(file, current_phase=""):
    lint_trace(file)

    if not current_phase:
        reject_pattern(r"\[AIDEV_TODO\]", file, "trace-gate must not contain pending placeholders")
        return

    current_order = phase_order(current_phase)
    if current_order == 999:
        fail(f"trace-gate: unknown current phase: {current_phase}")

    lines = text.read_lines(file)
    section = ""
    gated = False
    seen = []
    offending = []
    for line in lines:
        if line.startswith("## "):
            section = re.sub(r"\s+$", "", line[3:])
            ph = _TRACE_SECTION_PHASE.get(section, "")
            gated = ph != "" and phase_order(ph) <= current_order
            continue
        if gated and "[AIDEV_TODO]" in line:
            if section not in seen:
                seen.append(section)
                offending.append(section)

    if offending:
        joined = ", ".join(offending)
        fail(
            f"trace-gate: unresolved [AIDEV_TODO] in sections due by phase "
            f"'{current_phase}': {joined}"
        )


def lint_research(file):
    require_file(file)
    require_pattern(r"^# Research", file, "research must start with # Research")
    require_pattern(r"^## Problem Context", file, "research must include Problem Context")
    require_pattern(r"^## Research Conclusions", file, "research must include Research Conclusions")
    require_pattern(r"^## Sources", file, "research must include Sources")
    require_pattern(r"^## Source Confirmation Log", file, "research must include Source Confirmation Log")
    reject_pattern(r"\[AIDEV_TODO\]", file, "research must not contain pending placeholders")


def lint_tech_plan(file):
    require_file(file)
    require_pattern(r"^# Tech Plan", file, "tech plan must start with # Tech Plan")
    require_pattern(r"^## Adviser Guidance", file, "tech plan must include Adviser Guidance")
    require_pattern(r"^## Codebase Grounding", file, "tech plan must include Codebase Grounding")
    require_pattern(r"^## Design Decisions", file, "tech plan must include Design Decisions")
    require_pattern(r"^## Implementation Plan", file, "tech plan must include Implementation Plan")
    require_pattern(r"^### Task ", file, "tech plan must include at least one task subsection")
    require_pattern(r"^## Verification Gates", file, "tech plan must include Verification Gates")
    require_pattern(r"^### Gate: ", file, "tech plan must include at least one verification gate subsection")
    require_pattern(r"^## AC Coverage", file, "tech plan must include AC Coverage")
    require_pattern(
        r"^(?:\|[[:space:]]*AC[[:space:]]*\|[[:space:]]*Tasks[[:space:]]*\|[[:space:]]*Gates[[:space:]]*\||\|[[:space:]]*AC[[:space:]]*#[[:space:]]*\|[[:space:]]*Acceptance Criterion[[:space:]]*\|[[:space:]]*Gate[[:space:]]*\|[[:space:]]*Verification[[:space:]]*\|)",
        file,
        "tech plan AC Coverage must have supported columns",
    )
    require_pattern(
        r"^(?:\|[[:space:]]*AC-[0-9]+[[:space:]]*\|.*Task[[:space:]]+[0-9]+.*\|.*Gate:[[:space:]]*[^|[:space:]][^|]*\||\|[[:space:]]*[0-9]+[[:space:]]*\|[[:space:]]*[^|[:space:]][^|]*\|[[:space:]]*[^|[:space:]][^|]*\|[[:space:]]*[^|[:space:]][^|]*\|)",
        file,
        "tech plan AC Coverage must map an AC to task(s) and gate(s)",
    )
    reject_pattern(r"\[AIDEV_TODO\]", file, "tech plan must not contain pending placeholders")


def _trim(value):
    return re.sub(r"^\s+|\s+$", "", value)


def _markdown_table(lines, heading):
    try:
        start = lines.index(heading)
    except ValueError:
        return []
    header = []
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## ") or line.startswith("### "):
            if header:
                break
            continue
        if not line.startswith("|"):
            if header and rows:
                break
            continue
        columns = [_trim(value) for value in line.strip().strip("|").split("|")]
        if not header:
            header = columns
            continue
        if all(re.fullmatch(r"[-: ]+", value) for value in columns):
            continue
        if len(columns) < len(header):
            columns += [""] * (len(header) - len(columns))
        rows.append({header[index]: columns[index] for index in range(len(header))})
    return rows


def lint_code(file):
    require_file(file)

    require_pattern(r"^# Implementation Journal — [^[:space:]].*$", file, "code journal must start with # Implementation Journal — {session_slug}")
    require_pattern(r"^> Tech plan:[[:space:]]*`[^`]+`[[:space:]]*$", file, "code journal must declare tech plan in backticks")
    require_pattern(r"^> Started:[[:space:]]*[^[:space:]].*$", file, "code journal must declare started date")
    require_pattern(r"^> Status:[[:space:]]*[^[:space:]].*$", file, "code journal must declare overall status")

    lines = text.read_lines(file)
    has_backlog_links = any(re.match(r"^## Backlog Links", line) for line in lines)
    has_ci_handoffs = any(re.match(r"^## CI Handoffs", line) for line in lines)

    require_pattern(r"^## Repositories", file, "code journal must include Repositories section")
    require_pattern(r"^## Task Progress", file, "code journal must include Task Progress section")
    require_pattern(r"^## Implementation Evidence", file, "code journal must include Implementation Evidence section")
    require_pattern(r"^## Key Decisions", file, "code journal must include Key Decisions section")
    require_pattern(r"^## Phase Status", file, "code journal must include Phase Status section")

    order = {
        "## Repositories": 1,
        "## Backlog Links": 2,
        "## Task Progress": 3,
        "## Implementation Evidence": 4,
        "## Key Decisions": 5,
        "## CI Handoffs": 6,
        "## Phase Status": 7,
    }
    last = 0
    for line in lines:
        if line.startswith("## ") and line in order:
            if order[line] <= last:
                fail("code journal sections must follow the template order")
            last = order[line]

    require_pattern(r"^\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*GitHub Repo[[:space:]]*\|[[:space:]]*Branch[[:space:]]*\|[[:space:]]*Issue[[:space:]]*\|[[:space:]]*PR[[:space:]]*\|[[:space:]]*Status[[:space:]]*\|", file, "code journal Repositories table must have columns: Repo, GitHub Repo, Branch, Issue, PR, Status")
    if has_backlog_links:
        require_pattern(r"^\|[[:space:]]*Backlog ID[[:space:]]*\|[[:space:]]*Parent Issue[[:space:]]*\|[[:space:]]*Technical Issue[[:space:]]*\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*Link Type[[:space:]]*\|[[:space:]]*Status[[:space:]]*\|[[:space:]]*Notes[[:space:]]*\|", file, "code journal Backlog Links table must have columns: Backlog ID, Parent Issue, Technical Issue, Repo, Link Type, Status, Notes")
    require_pattern(r"^\|[[:space:]]*#[[:space:]]*\|[[:space:]]*Task[[:space:]]*\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*Status[[:space:]]*\|[[:space:]]*Phase[[:space:]]*\|", file, "code journal Task Progress table must have expected columns")
    require_pattern(r"^\|[[:space:]]*Evidence ID[[:space:]]*\|[[:space:]]*Task IDs[[:space:]]*\|[[:space:]]*Linked ACs[[:space:]]*\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*Files / Commands[[:space:]]*\|[[:space:]]*Result[[:space:]]*\|", file, "code journal Implementation Evidence table must have expected columns")
    require_pattern(r"^\|[[:space:]]*Decision[[:space:]]*\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*Rationale[[:space:]]*\|[[:space:]]*Alternatives[[:space:]]*\|", file, "code journal Key Decisions table must have expected columns")
    if has_ci_handoffs:
        require_pattern(r"^\|[[:space:]]*Exec Phase[[:space:]]*\|[[:space:]]*Repo[[:space:]]*\|[[:space:]]*Action[[:space:]]*\|[[:space:]]*PR Comment[[:space:]]*\|[[:space:]]*Artifact[[:space:]]*\|[[:space:]]*Status[[:space:]]*\|", file, "code journal CI Handoffs table must have expected columns")
    require_pattern(r"^\|[[:space:]]*Phase[[:space:]]*\|[[:space:]]*Status[[:space:]]*\|[[:space:]]*Notes[[:space:]]*\|", file, "code journal Phase Status table must have expected columns")

    if has_backlog_links:
        invalid = _code_backlog_links_invalid(lines)
        if invalid:
            fail(f"code journal Backlog Links value is invalid: {invalid}")

    if not _code_phase_status_has_five(lines):
        fail("code journal Phase Status table must include the five template phases in order")

    invalid_mandatory = _code_mandatory_phase_status(lines)
    if invalid_mandatory:
        fail(f"code journal mandatory phases 3-5 cannot be n/a or skipped: {invalid_mandatory}")

    overall_status = _code_overall_status(lines)
    if overall_status in ("complete", "complete-with-follow-ups"):
        invalid_complete = _code_complete_phase_status(lines)
        if invalid_complete:
            fail(f"code journal complete status requires all Phase Status rows 1-5 to be done: {invalid_complete}")
        require_pattern(
            r"^\|[[:space:]]*EVID-CODE-[0-9]+[[:space:]]*\|",
            file,
            "complete code journal must include at least one implementation evidence row",
        )

    if _code_task_row_count(lines) <= 0:
        fail("code journal must include at least one task progress row with valid status")
    invalid_task = _code_invalid_task_status(lines)
    if invalid_task:
        fail(f"code journal task status is invalid: {invalid_task}")
    missing_task_note = _code_task_status_missing_note(lines)
    if missing_task_note:
        fail(f"code journal {missing_task_note} requires a concrete Notes value")
    invalid_evidence = _code_invalid_evidence_id(lines)
    if invalid_evidence:
        fail(f"code journal evidence id is invalid: {invalid_evidence}")

    reject_pattern(r"\[AIDEV_TODO\]", file, "code journal must not contain pending placeholders")


def _code_backlog_links_invalid(lines):
    in_links = False
    for line in lines:
        if re.match(r"^## Backlog Links\s*$", line):
            in_links = True
            continue
        if in_links and line.startswith("## "):
            in_links = False
        if in_links and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*Backlog ID\s*\|", line):
                continue
            cols = line.split("|")
            if len(cols) < 9:
                continue
            link_type = _trim(cols[5])
            status = _trim(cols[6])
            if not re.match(r"^(sub-issue|fallback-reference|n/a)$", link_type):
                return "link_type=" + link_type
            if not re.match(r"^(linked|already-linked|fallback-reference|blocked|n/a)$", status):
                return "status=" + status
    return ""


def _code_phase_status_has_five(lines):
    expected = ["1 — Delivery Setup", "2 — Coding", "3 — PaaS Config", "4 — Validation", "5 — Commit"]
    next_expected = 0
    in_ps = False
    for line in lines:
        if re.match(r"^## Phase Status\s*$", line):
            in_ps = True
            continue
        if in_ps and line.startswith("## "):
            in_ps = False
        if in_ps and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*Phase\s*\|", line):
                continue
            cols = line.split("|")
            if len(cols) < 4:
                continue
            phase = _trim(cols[1])
            if next_expected < len(expected) and phase == expected[next_expected]:
                next_expected += 1
    return next_expected >= 5


def _code_mandatory_phase_status(lines):
    in_ps = False
    for line in lines:
        if re.match(r"^## Phase Status\s*$", line):
            in_ps = True
            continue
        if in_ps and line.startswith("## "):
            in_ps = False
        if in_ps and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*Phase\s*\|", line):
                continue
            cols = line.split("|")
            if len(cols) < 4:
                continue
            phase = _trim(cols[1])
            status = _trim(cols[2]).lower()
            if re.match(r"^[3-5] — ", phase) and status in ("n/a", "skipped"):
                return f"{phase}={status}"
    return ""


def _code_overall_status(lines):
    for line in lines:
        if re.match(r"^> Status:", line):
            value = re.sub(r"^> Status:\s*", "", line)
            value = value.replace("`", "")
            value = re.sub(r"^\s+|\s+$", "", value)
            return value.lower()
    return ""


def _code_complete_phase_status(lines):
    in_ps = False
    for line in lines:
        if re.match(r"^## Phase Status\s*$", line):
            in_ps = True
            continue
        if in_ps and line.startswith("## "):
            in_ps = False
        if in_ps and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*Phase\s*\|", line):
                continue
            cols = line.split("|")
            if len(cols) < 4:
                continue
            phase = _trim(cols[1])
            status = _trim(cols[2]).lower()
            if re.match(r"^[1-5] — ", phase) and status != "done":
                return f"{phase}={status}"
    return ""


def _code_task_row_count(lines):
    in_tasks = False
    count = 0
    for line in lines:
        if re.match(r"^## Task Progress\s*$", line):
            in_tasks = True
            continue
        if in_tasks and line.startswith("## "):
            in_tasks = False
        if in_tasks and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*#", line):
                continue
            cols = line.split("|")
            if len(cols) < 6:
                continue
            task_id = _trim(cols[1])
            status = _trim(cols[4])
            if task_id != "" and re.match(r"^(pending|done|partial|blocked|failed-validation|deferred|n/a|accepted-risk)$", status):
                count += 1
    return count


def _code_invalid_task_status(lines):
    in_tasks = False
    for line in lines:
        if re.match(r"^## Task Progress\s*$", line):
            in_tasks = True
            continue
        if in_tasks and line.startswith("## "):
            in_tasks = False
        if in_tasks and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*#", line):
                continue
            cols = line.split("|")
            if len(cols) < 6:
                continue
            status = _trim(cols[4])
            if not re.match(r"^(pending|done|partial|blocked|failed-validation|deferred|n/a|accepted-risk)$", status):
                return status
    return ""


def _code_task_status_missing_note(lines):
    in_tasks = False
    for line in lines:
        if re.match(r"^## Task Progress\s*$", line):
            in_tasks = True
            continue
        if in_tasks and line.startswith("## "):
            in_tasks = False
        if in_tasks and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*#", line):
                continue
            cols = line.split("|")
            if len(cols) < 6:
                continue
            task_id = _trim(cols[1])
            status = _trim(cols[4])
            note = _trim(cols[6]) if len(cols) >= 8 else ""
            if task_id != "" and status in ("deferred", "n/a", "accepted-risk") and note == "":
                return f"Task Progress row {task_id} with status={status}"
    return ""


def _code_invalid_evidence_id(lines):
    in_evidence = False
    for line in lines:
        if re.match(r"^## Implementation Evidence\s*$", line):
            in_evidence = True
            continue
        if in_evidence and line.startswith("## "):
            in_evidence = False
        if in_evidence and line.startswith("|"):
            if re.match(r"^\|\s*-+", line) or re.match(r"^\|\s*Evidence ID", line):
                continue
            cols = line.split("|")
            if len(cols) < 7:
                continue
            evidence_id = _trim(cols[1])
            if evidence_id != "" and evidence_id != "n/a" and not re.match(r"^EVID-CODE-[0-9]+$", evidence_id):
                return evidence_id
    return ""


def lint_test_plan(file):
    require_file(file)
    require_pattern(r"^# SDD Test Plan", file, "test plan must start with # SDD Test Plan")
    require_pattern(r"^## Test Strategy", file, "test plan must include Test Strategy")
    require_pattern(r"^## Acceptance Criteria Coverage", file, "test plan must include Acceptance Criteria Coverage")
    require_pattern(r"^## Test Matrix", file, "test plan must include Test Matrix")
    require_pattern(r"^## Execution Evidence Plan", file, "test plan must include Execution Evidence Plan")
    require_pattern(r"AC-[0-9]+", file, "test plan must include AC IDs")
    require_pattern(r"TEST-[0-9]+", file, "test plan must include TEST IDs")
    require_pattern(
        r"^\|[[:space:]]*TEST-[0-9]+[[:space:]]*\|",
        file,
        "test plan Test Matrix must include at least one TEST row",
    )
    lines = text.read_lines(file)
    coverage = _markdown_table(lines, "## Acceptance Criteria Coverage")
    matrix = _markdown_table(lines, "## Test Matrix")
    coverage_links: dict[str, set[str]] = {}
    for row in coverage:
        ac_id = row.get("AC ID", "")
        if not re.fullmatch(r"AC-[0-9]+", ac_id):
            continue
        covering = row.get("Covering Tests", "")
        tests = set(re.findall(r"TEST-[0-9]+", covering))
        if not tests and "gap" not in covering.lower():
            fail(f"test plan coverage for {ac_id} must name tests or an accepted gap")
        coverage_links[ac_id] = tests
    if not coverage_links:
        fail("test plan Acceptance Criteria Coverage must include at least one AC row")

    matrix_links: dict[str, set[str]] = {}
    for row in matrix:
        test_id = row.get("Test ID", "")
        if not re.fullmatch(r"TEST-[0-9]+", test_id):
            continue
        linked_acs = set(re.findall(r"AC-[0-9]+", row.get("Linked ACs", "")))
        if not linked_acs:
            fail(f"test plan Test Matrix row must link at least one AC: {test_id}")
        matrix_links[test_id] = linked_acs

    evidence_links: dict[str, set[str]] = {}
    for row in _markdown_table(lines, "## Execution Evidence Plan"):
        evidence_id = row.get("Evidence ID", "")
        if not re.fullmatch(r"EVID-TEST-[0-9]+", evidence_id):
            continue
        evidence_links[evidence_id] = set(
            re.findall(r"TEST-[0-9]+", row.get("Linked Tests", ""))
        )
    for test_id in matrix_links:
        evidence_id = f"EVID-TEST-{test_id.split('-')[-1]}"
        if evidence_id not in evidence_links:
            fail(f"test plan is missing execution evidence row: {evidence_id}")
        if test_id not in evidence_links[evidence_id]:
            fail(f"test plan evidence row {evidence_id} must link {test_id}")

    for ac_id, test_ids in coverage_links.items():
        for test_id in test_ids:
            if test_id not in matrix_links:
                fail(f"test plan coverage references missing Test Matrix row: {test_id}")
            if ac_id not in matrix_links[test_id]:
                fail(f"test plan link is missing from Test Matrix: {ac_id} -> {test_id}")
    for test_id, ac_ids in matrix_links.items():
        for ac_id in ac_ids:
            if test_id not in coverage_links.get(ac_id, set()):
                fail(f"test plan link is missing from AC coverage: {test_id} -> {ac_id}")
    reject_pattern(r"\[AIDEV_TODO\]", file, "test plan must not contain pending placeholders")


def lint_verification(file):
    require_file(file)
    require_pattern(r"^# SDD Verification", file, "verification must start with # SDD Verification")
    require_pattern(r"^## Verification Summary", file, "verification must include Verification Summary")
    require_pattern(r"^## Acceptance Criteria Verification", file, "verification must include Acceptance Criteria Verification")
    require_pattern(r"^## Evidence Reviewed", file, "verification must include Evidence Reviewed")
    require_pattern(r"^## Gate Decision", file, "verification must include Gate Decision")
    require_pattern(r"^## Review", file, "verification must include Review")
    require_pattern(r"^### Contract Review", file, "verification review must include Contract Review")
    require_pattern(r"^### Findings", file, "verification review must include Findings")
    require_pattern(r"^### Combined Gate Decision", file, "verification review must include Combined Gate Decision")
    require_pattern(r"AC-[0-9]+", file, "verification must reference AC IDs")
    require_pattern(r"EVID-[A-Z0-9-]+", file, "verification must reference evidence IDs")
    require_pattern(
        r"^\|[[:space:]]*AC-[0-9]+[[:space:]]*\|[^|]*\|[^|]*EVID-[A-Z0-9-]+",
        file,
        "verification AC table must include at least one row with evidence",
    )
    require_pattern(r"REVIEW-[0-9]+", file, "verification review must reference a review finding ID")
    reject_pattern(r"\[AIDEV_TODO\]", file, "verification must not contain pending placeholders")


def lint_retro(file):
    require_file(file)
    require_pattern(r"^# SDD Retro", file, "retro must start with # SDD Retro")
    require_pattern(r"^## Outcome Summary", file, "retro must include Outcome Summary")
    require_pattern(r"^## Observations", file, "retro must include Observations")
    require_pattern(r"^## Compounding Ledger", file, "retro must include Compounding Ledger")
    require_pattern(r"^## Spec Consolidation", file, "retro must include Spec Consolidation")
    require_pattern(r"^## Closure Decision", file, "retro must include Closure Decision")
    reject_pattern(r"\[AIDEV_TODO\]", file, "retro must not contain pending placeholders")


def lint_changes(file):
    require_file(file)
    require_pattern(r'"schema_version"[[:space:]]*:[[:space:]]*[12]', file, "changes.json must declare schema_version: 1 or 2")
    require_pattern(r'"changes"[[:space:]]*:', file, "changes.json must declare changes array")

    if text.grep_q(r'"session_id"', file):
        require_pattern(r'"session_id"[[:space:]]*:', file, "changes entry must declare session_id")
        require_pattern(r'"session_slug"[[:space:]]*:', file, "changes entry must declare session_slug")
        require_pattern(r'"date"[[:space:]]*:', file, "changes entry must declare date")
        require_pattern(r'"timestamp"[[:space:]]*:', file, "changes entry must declare timestamp")
        require_pattern(r'"change_type"[[:space:]]*:', file, "changes entry must declare change_type")
        require_pattern(r'"change_type"[[:space:]]*:[[:space:]]*"(created|updated|deleted)"', file, "change_type must be created, updated, or deleted")
        require_pattern(r'"spec_version"[[:space:]]*:', file, "changes entry must declare spec_version")
        require_pattern(r'"previous_version"[[:space:]]*:', file, "changes entry must declare previous_version")
        require_pattern(r'"model"[[:space:]]*:', file, "changes entry must declare model")
        require_pattern(r'"user"[[:space:]]*:', file, "changes entry must declare user")
        require_pattern(r'"change_note"[[:space:]]*:', file, "changes entry must declare change_note")
        require_pattern(r'"change_note_path"[[:space:]]*:', file, "changes entry must declare change_note_path")

        if text.grep_q(r'"schema_version"[[:space:]]*:[[:space:]]*2', file):
            require_pattern(r'"agent"[[:space:]]*:', file, "changes entry (schema v2) must declare agent")
            require_pattern(r'"assistant"[[:space:]]*:', file, "changes entry (schema v2) must declare assistant")
            require_pattern(r'"commit"[[:space:]]*:', file, "changes entry (schema v2) must declare commit")
            require_pattern(r'"version_ref"[[:space:]]*:', file, "changes entry (schema v2) must declare version_ref")
            require_pattern(r'"participants"[[:space:]]*:', file, "changes entry (schema v2) must declare participants array")
        else:
            if not text.grep_q(r'"agent"[[:space:]]*:', file):
                print(
                    f"sdd-lint: warning: {file}: schema v1 entry missing "
                    "agent/assistant/commit — upgrade to schema_version: 2",
                    file=sys.stderr,
                )

    lines = text.read_lines(file)
    first = lines[0] if lines else ""
    last = lines[-1] if lines else ""
    if not re.match(r"^\s*\{", first):
        fail("changes.json must start with {")
    if not re.search(r"\}\s*$", last):
        fail("changes.json must end with }")


def report_metrics(file):
    require_file(file)
    lines = text.read_lines(file)
    track = trim_scalar(_top_scalar("track", lines))
    session_id = trim_scalar(_indented_scalar("id", lines))
    print(f"sdd-metrics: session={session_id or 'unknown'} track={track or 'unknown'}")

    def unquote(v):
        return re.sub(r"^[\s'\"]+|[\s'\"]+$", "", v)

    in_metrics = False
    phase = started = completed = invocations = rounds = ""
    total_invocations = total_rounds = phase_count = 0
    out = []

    def flush_entry():
        nonlocal phase, started, completed, invocations, rounds
        nonlocal total_invocations, total_rounds, phase_count
        if phase != "":
            out.append(
                "sdd-metrics: phase=%s started=%s completed=%s invocations=%s question_rounds=%s"
                % (
                    phase,
                    "-" if started == "" else started,
                    "-" if completed == "" else completed,
                    "0" if invocations == "" else invocations,
                    "0" if rounds == "" else rounds,
                )
            )
            total_invocations += 0 if invocations == "" else int(_int_or_zero(invocations))
            total_rounds += 0 if rounds == "" else int(_int_or_zero(rounds))
            phase_count += 1
        phase = started = completed = invocations = rounds = ""

    for line in lines:
        if re.match(r"^metrics:", line):
            in_metrics = True
            continue
        if in_metrics and re.match(r"^\S", line):
            flush_entry()
            in_metrics = False
        if in_metrics and re.match(r"^\s*-\s+phase:", line):
            flush_entry()
            phase = unquote(re.sub(r"^\s*-\s+phase:\s*", "", line))
            continue
        if in_metrics and re.match(r"^\s+started_at:", line):
            started = unquote(re.sub(r"^\s+started_at:\s*", "", line))
            continue
        if in_metrics and re.match(r"^\s+completed_at:", line):
            completed = unquote(re.sub(r"^\s+completed_at:\s*", "", line))
            continue
        if in_metrics and re.match(r"^\s+specialist_invocations:", line):
            invocations = unquote(re.sub(r"^\s+specialist_invocations:\s*", "", line))
            continue
        if in_metrics and re.match(r"^\s+question_rounds:", line):
            rounds = unquote(re.sub(r"^\s+question_rounds:\s*", "", line))
            continue
    flush_entry()
    out.append(
        "sdd-metrics: totals phases=%d specialist_invocations=%d question_rounds=%d"
        % (phase_count, total_invocations, total_rounds)
    )
    for line in out:
        print(line)


def _int_or_zero(value):
    try:
        return int(value)
    except ValueError:
        return 0


def lint_contracts(file):
    require_file(file)
    directory = os.path.realpath(os.path.dirname(file) or ".")
    require_pattern(r"^schema_version:[[:space:]]*1", file, "contracts must declare schema_version: 1")
    require_pattern(r"^contracts:", file, "contracts must declare contracts array")

    lines = text.read_lines(file)
    ids = []
    for contract_id, contract_path, contract_sha256 in parse_contract_entries(lines):
        contract_id = trim_scalar(contract_id)
        contract_path = trim_scalar(contract_path)
        contract_sha256 = trim_scalar(contract_sha256)
        if contract_id == "" and contract_path == "" and contract_sha256 == "":
            continue
        if not contract_id:
            fail("contract entry must declare id")
        if contract_id in ids:
            fail(f"contract id must be unique: {contract_id}")
        ids.append(contract_id)
        if not contract_path:
            fail(f"contract must declare path: {contract_id}")
        if ".." in contract_path:
            fail(f"contract path must not contain '..': {contract_path}")
        if not contract_path.startswith("contracts/"):
            fail(f"contract path must be inside 'contracts/' subdirectory: {contract_path}")
        if not os.path.isfile(os.path.join(directory, contract_path)):
            fail(f"contract path not found: {contract_path}")
        if is_nullish(contract_sha256):
            fail(f"contract must declare sha256: {contract_id}")


def lint_contract_trace(contracts_file, trace_file):
    require_file(contracts_file)
    require_file(trace_file)
    contract_ids = [
        trim_scalar(contract_id)
        for contract_id, _path, _sha256 in parse_contract_entries(
            text.read_lines(contracts_file)
        )
        if trim_scalar(contract_id)
    ]
    if not contract_ids:
        return

    rows: dict[str, str] = {}
    in_section = False
    for line in text.read_lines(trace_file):
        if line == "## Input Contract Trace":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|"):
            continue
        columns = [trim_scalar(value) for value in line.strip().strip("|").split("|")]
        if columns and columns[0] not in ("Contract ID", "---"):
            rows[columns[0]] = line

    for contract_id in contract_ids:
        row = rows.get(contract_id, "")
        if not row:
            fail(f"contract trace is missing contract id: {contract_id}")
        if not re.search(r"(?<![A-Z0-9-])AC-[0-9]+(?![0-9])", row):
            fail(f"contract trace has no affected AC for: {contract_id}")


def _extract_ac_ids(files):
    ids = set()
    rx = re.compile(r"AC-[0-9]+")
    for f in files:
        try:
            for line in text.read_lines(f):
                ids.update(rx.findall(line))
        except OSError:
            continue
    return sorted(ids)


def _coverage_check_artifact(ac, artifact, label):
    if not os.path.isfile(artifact):
        return True
    rx = re.compile(r"(^|[^A-Z0-9])" + re.escape(ac) + r"([^0-9]|$)")
    if not any(rx.search(line) for line in text.read_lines(artifact)):
        print(f"sdd-lint: coverage: {ac} missing in {label}", file=sys.stderr)
        return False
    return True


def _coverage_check_trace_section(ac, trace_file, heading, label):
    if not os.path.isfile(trace_file):
        return True
    in_section = False
    section_lines = []
    for line in text.read_lines(trace_file):
        if line == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            section_lines.append(line)
    rx = re.compile(r"(^|[^A-Z0-9])" + re.escape(ac) + r"([^0-9]|$)")
    if not any(rx.search(line) for line in section_lines):
        print(f"sdd-lint: coverage: {ac} missing in {label}", file=sys.stderr)
        return False
    return True


def _coverage_check_verification_evidence(ac, verification):
    if not os.path.isfile(verification):
        return True
    evid = re.compile(r"EVID-[A-Z0-9-]+")
    found = False
    window = 0
    ok = False
    for line in text.read_lines(verification):
        if ac in line:
            found = True
            window = 6
        if found and window > 0:
            if evid.search(line):
                ok = True
                break
            window -= 1
            if window == 0:
                found = False
    if not ok:
        print(
            f"sdd-lint: coverage: {ac} in verification artifact has no nearby "
            "EVID- reference",
            file=sys.stderr,
        )
        return False
    return True


def _coverage_check_backlog_source_spec(backlog, session_dir):
    if not os.path.isfile(backlog):
        return True
    specs = []
    ss = ""
    kind = ""
    have_ss = False
    for line in text.read_lines(backlog):
        if re.match(r"^\s*-\s+id:", line):
            if have_ss and kind != "removed":
                specs.append(ss)
            ss = ""
            kind = ""
            have_ss = False
            continue
        if re.match(r"^\s+source_spec:", line):
            ss = re.sub(r"^\s+source_spec:\s*", "", line)
            have_ss = True
            continue
        if re.match(r"^\s+change_kind:", line):
            kind = re.sub(r"\s+$", "", re.sub(r"^\s+change_kind:\s*", "", line))
            continue
    if have_ss and kind != "removed":
        specs.append(ss)

    rc = True
    for spec_rel in specs:
        spec_rel = trim_scalar(spec_rel)
        if spec_rel == "":
            continue
        if not os.path.isfile(os.path.join(session_dir, spec_rel)):
            print(f"sdd-lint: coverage: backlog source_spec not found: {spec_rel}", file=sys.stderr)
            rc = False
    return rc


def lint_coverage(directory, state_file_override="", trace_path_override=""):
    if not os.path.isdir(directory):
        fail(f"session directory not found: {directory}")
    state_file = state_file_override or os.path.join(directory, "sdd-state.yml")
    if not os.path.isfile(state_file):
        fail(f"session state not found: {state_file}")

    state_lines = text.read_lines(state_file)
    track = trim_scalar(_top_scalar("track", state_lines))

    def phase_due(phase):
        return trim_scalar(nested_value("phases", phase, "status", state_lines)) in (
            "in-progress",
            "complete",
        )

    def registered_artifact(basename):
        stored = trim_scalar(artifact_value(basename, state_lines))
        if is_nullish(stored):
            return os.path.join(directory, basename)
        try:
            return state.resolve_state_artifact(directory, stored)
        except ValueError as err:
            fail(str(err))

    trace_path = trace_path_override or registered_artifact("trace.md")
    tech_plan_path = registered_artifact("tech-plan.md")
    test_plan_path = registered_artifact("test-plan.md")
    code_path = registered_artifact("code.md")
    verification_path = registered_artifact("verification.md")
    backlog_path = registered_artifact("backlog-plan.yml")

    specs = []
    specs_missing = False
    for spec_path, spec_scope, _ in parse_state_specs(state_lines):
        spec_path = trim_scalar(spec_path)
        spec_scope = trim_scalar(spec_scope) or "session"
        if spec_path == "":
            continue
        try:
            full = state.resolve_scoped_path(directory, spec_scope, spec_path)
        except ValueError as err:
            print(f"sdd-lint: coverage: {err}", file=sys.stderr)
            specs_missing = True
            continue
        if os.path.isfile(full):
            specs.append(full)
        else:
            print(
                f"sdd-lint: coverage: spec path not found: {spec_scope}:{spec_path}",
                file=sys.stderr,
            )
            specs_missing = True

    if len(specs) == 0:
        if (
            trim_scalar(_top_scalar("current_phase", state_lines)) == "retro"
            and _canonical_spec_deletion_recorded(state_lines)
        ):
            return
        if track in ("simple", "moderate", "complex", "smart"):
            return
        fail("coverage: no specs found in session state")

    if specs_missing:
        raise LintFailure(None, 1)

    ac_ids = _extract_ac_ids(specs)
    if not ac_ids:
        fail("coverage: no AC-N IDs found in specs")

    rc = True
    for ac in ac_ids:
        if ac == "":
            continue
        if not _coverage_check_artifact(ac, trace_path, "trace artifact"):
            rc = False
        if phase_due("technical-plan") and os.path.isfile(tech_plan_path) and not _coverage_check_trace_section(
            ac, trace_path, "## Technical Plan Trace", "Technical Plan Trace"
        ):
            rc = False
        if phase_due("test-design"):
            if not _coverage_check_artifact(ac, test_plan_path, "test-plan artifact"):
                rc = False
            if os.path.isfile(test_plan_path) and not _coverage_check_trace_section(
                ac, trace_path, "## Test Design Trace", "Test Design Trace"
            ):
                rc = False
        if phase_due("implementation") and os.path.isfile(code_path) and not _coverage_check_trace_section(
            ac, trace_path, "## Implementation Trace", "Implementation Trace"
        ):
            rc = False
        if phase_due("spec-verification"):
            if not _coverage_check_artifact(ac, verification_path, "verification artifact"):
                rc = False
            if os.path.isfile(verification_path) and not _coverage_check_trace_section(
                ac, trace_path, "## Verification Trace", "Verification Trace"
            ):
                rc = False
            if not _coverage_check_verification_evidence(ac, verification_path):
                rc = False

    if not _coverage_check_backlog_source_spec(backlog_path, directory):
        rc = False

    if not rc:
        raise LintFailure(None, 1)


_DISPATCH = {
    "session": lint_session_state,
    "spec-package": lint_spec_package,
    "backlog": lint_backlog,
    "trace": lint_trace,
    "research": lint_research,
    "tech-plan": lint_tech_plan,
    "code": lint_code,
    "test-plan": lint_test_plan,
    "verification": lint_verification,
    "retro": lint_retro,
    "changes": lint_changes,
    "contracts": lint_contracts,
    "metrics": report_metrics,
    "coverage": lint_coverage,
}


def run_mode(mode, target, phase):
    if mode == "trace-gate":
        lint_trace_gate(target, phase)
    else:
        _DISPATCH[mode](target)
