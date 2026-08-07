"""Internal request rendering and manifest materialization for sdd-state."""
from __future__ import annotations

import os
import re
import shlex
import tempfile
from datetime import datetime, timezone
from typing import Any

import yaml

from . import handoffs, state, text, yamlscan
from .cli import ToolError


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = handoffs.HANDOFF_ASSETS_DIR
INVOCATION_TEMPLATE = os.path.join(ASSETS_DIR, "invocation.md")
_ENVELOPE_FIELD = re.compile(
    r"^- \*\*(Schema|Delegation|Agent|Topic|Phase|Status|Gate):\*\*\s*`?(.+?)`?\s*$"
)
_RETRY_START = "<!-- aidev-sdd-retry:start -->"
_RETRY_END = "<!-- aidev-sdd-retry:end -->"

_OPTION_HELP = {
    "artifact": "`--artifact NAME KIND SCOPE PATH` adds an optional artifact.",
    "spec": "`--spec NAME SCOPE PATH RELATION` adds and classifies a spec artifact.",
    "replace-spec": "`--replace-spec NAME OLD_SCOPE OLD_PATH` makes a declared spec replace an existing registry entry.",
    "contract-map": "`--contract-map CONTRACT SPEC AC-CSV` maps contract/spec/AC IDs without changing AC prose.",
    "remove-spec": "`--remove-spec SCOPE PATH` drops an existing draft registry entry.",
    "delete-spec": "`--delete-spec REGISTERED_SCOPE REGISTERED_PATH PACKAGE` declares a canonical package already removed by Retro.",
    "blocker": "For blocked status, repeat `--blocker ARTIFACT BLOCK-ID`; the ID must exist in that artifact.",
}


def _fail(message: str) -> None:
    raise ToolError(message)


def _fenced_text(value: str) -> list[str]:
    delimiter = "```"
    while delimiter in value:
        delimiter += "`"
    return [f"{delimiter}text", value, delimiter]


def _current_phase(session_dir: str) -> str:
    for line in text.read_lines(state.state_file_of(session_dir)):
        if line.startswith("current_phase:"):
            return yamlscan.trim_scalar(line.split(":", 1)[1])
    return ""


def _load_profile(session_dir: str, expected_phase: str) -> dict[str, Any]:
    current = _current_phase(session_dir)
    if current != expected_phase:
        _fail(f"expected phase {expected_phase}, current_phase is {current}")
    try:
        return handoffs.load_phase_profile(expected_phase)
    except ValueError as err:
        _fail(str(err))


def _require_active_delegated_phase(session_dir: str, expected_phase: str) -> dict[str, Any]:
    profile = _load_profile(session_dir, expected_phase)
    records = text.read_lines(state.state_file_of(session_dir))
    if yamlscan.pending_delegation_active(records):
        _fail("resume the current pending delegation before starting or submitting a handoff")
    phase_status = yamlscan.trim_scalar(
        yamlscan.nested_value("phases", expected_phase, "status", records)
    )
    gate_status = yamlscan.trim_scalar(
        yamlscan.nested_value("gates", expected_phase, "status", records)
    )
    if phase_status != "in-progress" or gate_status != "pending":
        _fail(
            f"handoff requires {expected_phase} phase=in-progress and gate=pending "
            f"(got phase={phase_status or 'unset'}, gate={gate_status or 'unset'})"
        )
    return profile


def _safe_handoffs_root(session_dir: str) -> str:
    session_root = os.path.realpath(session_dir)
    handoffs_root = os.path.realpath(os.path.join(session_dir, "handoffs"))
    try:
        contained = os.path.commonpath((session_root, handoffs_root)) == session_root
    except ValueError:
        contained = False
    if not contained:
        _fail("session handoffs directory escapes the session root")
    return handoffs_root


def _safe_request_path(session_dir: str, phase: str, create: bool) -> str:
    handoffs_root = _safe_handoffs_root(session_dir)
    requests_dir = os.path.join(session_dir, "handoffs", "requests")
    if create:
        os.makedirs(requests_dir, exist_ok=True)
    requests_root = os.path.realpath(requests_dir)
    if os.path.commonpath((handoffs_root, requests_root)) != handoffs_root:
        _fail("handoff requests directory escapes handoffs/")
    lexical_path = handoffs.request_path(session_dir, phase)
    if os.path.islink(lexical_path):
        _fail("handoff request must not be a symlink")
    path = os.path.realpath(lexical_path)
    if os.path.commonpath((requests_root, path)) != requests_root:
        _fail("handoff request path escapes requests/")
    return path


def _safe_base_request_path(session_dir: str, phase: str, create: bool) -> str:
    handoffs_root = _safe_handoffs_root(session_dir)
    requests_dir = os.path.join(session_dir, "handoffs", "requests")
    if create:
        os.makedirs(requests_dir, exist_ok=True)
    requests_root = os.path.realpath(requests_dir)
    if os.path.commonpath((handoffs_root, requests_root)) != handoffs_root:
        _fail("handoff requests directory escapes handoffs/")
    lexical_path = handoffs.base_request_path(session_dir, phase)
    if os.path.islink(lexical_path):
        _fail("handoff request base must not be a symlink")
    path = os.path.realpath(lexical_path)
    if os.path.commonpath((requests_root, path)) != requests_root:
        _fail("handoff request base path escapes requests/")
    return path


def _atomic_write(path: str, content: str) -> None:
    directory = os.path.dirname(path)
    fd, temporary = tempfile.mkstemp(prefix=".handoff-write-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def stage_request(path: str, content: str) -> str:
    fd, temporary = tempfile.mkstemp(
        prefix=".handoff-request-", dir=os.path.dirname(path), text=True
    )
    with os.fdopen(fd, "w") as handle:
        handle.write(content.rstrip() + "\n")
    return temporary


def _workspace_relative(session_dir: str, path: str) -> str:
    workspace = state.workspace_root_of_session(session_dir)
    session = os.path.abspath(session_dir)
    deliverables = os.path.join(workspace, ".aicontext", "deliverables")
    absolute = os.path.abspath(path)
    resolved = os.path.realpath(path)
    try:
        lexical_contained = os.path.commonpath((workspace, absolute)) == workspace
        session_contained = (
            os.path.commonpath((os.path.realpath(session), resolved))
            == os.path.realpath(session)
        )
        deliverables_contained = (
            os.path.commonpath((os.path.realpath(deliverables), resolved))
            == os.path.realpath(deliverables)
        )
    except ValueError:
        lexical_contained = session_contained = deliverables_contained = False
    if lexical_contained:
        return os.path.relpath(absolute, workspace)
    if session_contained:
        return os.path.relpath(
            os.path.join(session, os.path.relpath(resolved, os.path.realpath(session))),
            workspace,
        )
    if deliverables_contained:
        return os.path.relpath(
            os.path.join(
                deliverables,
                os.path.relpath(resolved, os.path.realpath(deliverables)),
            ),
            workspace,
        )
    if not lexical_contained:
        _fail(f"path must be inside the current workspace: {path}")
    return os.path.relpath(absolute, workspace)


def _lexical_workspace_relative(session_dir: str, path: str) -> str:
    workspace = state.workspace_root_of_session(session_dir)
    value = path if os.path.isabs(path) else os.path.join(workspace, path)
    return _workspace_relative(session_dir, value)


def _bullets(session_dir: str, items: list[list[str]] | None, empty: str = "- (none)") -> str:
    if not items:
        return empty
    return "\n".join(
        f"- `{_lexical_workspace_relative(session_dir, path)}`: {note}"
        for path, note in items
    )


def _policies(profile: dict[str, Any], session_dir: str, values: list[list[str]] | None) -> str:
    policies = {key: value for key, value in (values or [])}
    if profile["phase"] == "implementation" and "delivery_mode" not in policies:
        track = ""
        for line in text.read_lines(state.state_file_of(session_dir)):
            if line.startswith("track:"):
                track = yamlscan.trim_scalar(line.split(":", 1)[1])
                break
        policies["delivery_mode"] = "local-only" if track == "simple" else "github-delivery"
    if not policies:
        return "- (none)"
    return "\n".join(f"- {key}: {value}" for key, value in policies.items())


def _manifest_options(profile: dict[str, Any]) -> str:
    fixed = [
        "Fixed artifacts already included; do not redeclare their names or paths:",
        *(
            f"- `{name}`: kind `{artifact['kind']}`, scope `{artifact['scope']}`, "
            f"path `{artifact['path']}`"
            for name, artifact in profile["artifacts"].items()
        ),
    ]
    optional = [
        _OPTION_HELP[name]
        for name in profile["allowed_flags"]
        if name in _OPTION_HELP
    ]
    optional.extend(str(item) for item in profile.get("manifest_notes", []))
    if not optional:
        return "\n".join(fixed)
    return "\n".join(
        [*fixed, "", "Additional flags allowed for this phase:", *(f"- {line}" for line in optional)]
    )


def _submission_command(profile: dict[str, Any], session: str, expected_phase: str) -> str:
    command = (
        "python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py "
        f"submit-handoff {shlex.quote(session)} "
        f"--expect-phase {shlex.quote(expected_phase)} --status ready"
    )
    required_flags = profile.get("required_command_flags", [])
    if required_flags:
        command += " " + " ".join(required_flags)
    return command


def _base_request(
    session_dir: str,
    expected_phase: str,
    need: str,
    context: list[list[str]] | None,
    policy: list[list[str]] | None,
) -> str:
    if not need:
        _fail("create-handoff requires --need")
    if not os.path.isfile(INVOCATION_TEMPLATE):
        _fail("handoff invocation template not found")
    with open(INVOCATION_TEMPLATE) as handle:
        template = handle.read()
    profile = _require_active_delegated_phase(session_dir, expected_phase)
    session = _workspace_relative(session_dir, session_dir)
    command = _submission_command(profile, session, expected_phase)
    request = template.format(
        agent=profile["agent"],
        phase=profile["phase"],
        need=need.strip(),
        session=session,
        context=_bullets(session_dir, context),
        policy=_policies(profile, session_dir, policy),
        manifest_command=command,
        manifest_options=_manifest_options(profile),
    )
    if request.count("## Successful handoff") != 1:
        _fail("generated request must contain exactly one successful handoff section")
    return request


def create_request(
    session_dir: str,
    expected_phase: str,
    need: str,
    context: list[list[str]] | None,
    policy: list[list[str]] | None,
) -> str:
    path = _safe_request_path(session_dir, expected_phase, create=True)
    base_path = _safe_base_request_path(session_dir, expected_phase, create=True)
    content = _base_request(
        session_dir,
        expected_phase,
        need,
        context,
        policy,
    )
    _atomic_write(base_path, content)
    _atomic_write(path, content)
    return _workspace_relative(session_dir, path)


def _top_level_line_offsets(content: str, value: str) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    fence_character = ""
    fence_length = 0
    offset = 0
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        fence = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence_character:
            if (
                fence
                and fence.group(1)[0] == fence_character
                and len(fence.group(1)) >= fence_length
                and re.fullmatch(rf"{re.escape(fence_character)}{{{fence_length},}}", stripped)
            ):
                fence_character = ""
                fence_length = 0
        elif fence:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
        elif stripped == value:
            offsets.append((offset, offset + len(line)))
        offset += len(line)
    return offsets


def _retry_packet(findings: list[str]) -> str:
    out = [
        _RETRY_START,
        "## Validation Remediation",
        "",
        "The previous handoff failed deterministic validation. Correct the findings below, preserve the earlier request context, and submit a new handoff only after the owned artifact is repaired.",
        "",
        "### Findings",
        "",
    ]
    for index, finding in enumerate(findings, start=1):
        out.extend(
            [
                f"#### Finding {index}",
                "",
                *_fenced_text(finding.strip()),
                "",
            ]
        )
    out.extend(
        [
            "Re-read the persisted artifacts named in this request, fix only the reported findings, and run the generated submit command again.",
            _RETRY_END,
        ]
    )
    return "\n".join(out)


def _with_retry_packet(content: str, findings: list[str], label: str) -> str:
    successful = _top_level_line_offsets(content, "## Successful handoff")
    if len(successful) != 1:
        _fail(f"{label} must contain exactly one top-level successful handoff section")
    marker_start, _marker_end = successful[0]
    starts = _top_level_line_offsets(content, _RETRY_START)
    ends = _top_level_line_offsets(content, _RETRY_END)
    if bool(starts) != bool(ends) or len(starts) > 1 or len(ends) > 1:
        _fail(f"retry-handoff {label} contains malformed validation remediation")

    prefix = content[:marker_start]
    if starts:
        start, _start_end = starts[0]
        _end_start, end = ends[0]
        if start >= marker_start or end > marker_start or content[end:marker_start].strip():
            _fail(f"retry-handoff {label} remediation section must precede successful handoff")
        prefix = content[:start]

    return prefix.rstrip() + "\n\n" + _retry_packet(findings) + "\n\n" + content[marker_start:]


def build_retry_request(
    session_dir: str,
    expected_phase: str,
    findings: list[str] | None,
) -> tuple[str, str, str, str]:
    _require_active_delegated_phase(session_dir, expected_phase)
    if not findings or any(not finding.strip() for finding in findings):
        _fail("retry-handoff requires at least one non-empty --finding")
    request_path = _safe_request_path(session_dir, expected_phase, create=False)
    if not os.path.isfile(request_path):
        _fail("retry-handoff requires an existing request")
    base_path = _safe_base_request_path(session_dir, expected_phase, create=False)
    if not os.path.isfile(base_path):
        _fail("retry-handoff requires an existing request base")

    request = "\n".join(text.read_lines(request_path)).rstrip() + "\n"
    base = "\n".join(text.read_lines(base_path)).rstrip() + "\n"
    return (
        request_path,
        _with_retry_packet(request, findings, "request"),
        base_path,
        _with_retry_packet(base, findings, "request base"),
    )


def _section(lines: list[str], heading: str) -> list[str]:
    try:
        start = lines.index(heading)
    except ValueError:
        _fail(f"question envelope is missing {heading}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def _validate_question_envelope(
    fields: dict[str, str],
    lines: list[str],
    expected_agent: str,
    expected_phase: str,
    expected_delegation: str,
) -> None:
    if not lines or lines[0] != "# Subagent Question Envelope":
        _fail("question envelope must start with '# Subagent Question Envelope'")
    if fields.get("schema") != "1.0":
        _fail("question envelope schema must be 1.0")
    if fields.get("agent") != expected_agent:
        _fail("question envelope agent does not match the phase owner")
    if fields.get("phase") != expected_phase:
        _fail("question envelope phase does not match the current phase")
    if fields.get("delegation") != expected_delegation:
        _fail("question envelope delegation ID does not match the pending delegation")
    if fields.get("status") != "needs_user_input" or fields.get("gate") != "paused":
        _fail("question envelope must have needs_user_input status and paused gate")
    questions = _section(lines, "## Questions")
    _section(lines, "## Checkpoint")
    _section(lines, "## Resume Contract")
    if not any(re.match(r"^###\s+`?([^`\s]+)`?\s*$", line) for line in questions):
        _fail("question envelope must declare at least one question")


def validate_question_envelope(
    envelope_path: str,
    expected_agent: str,
    expected_phase: str,
    expected_delegation: str,
) -> None:
    lines = text.read_lines(envelope_path)
    fields: dict[str, str] = {}
    for line in lines:
        match = _ENVELOPE_FIELD.match(line)
        if match:
            fields[match.group(1).lower()] = match.group(2).strip("` ")
    _validate_question_envelope(
        fields,
        lines,
        expected_agent,
        expected_phase,
        expected_delegation,
    )


def _resolve_pending_envelope(session_dir: str) -> tuple[str, dict[str, str], list[str]]:
    records = text.read_lines(state.state_file_of(session_dir))
    pending = yamlscan.trim_scalar(
        yamlscan.pending_delegation_value("envelope_artifact_path", records)
    )
    if not pending:
        _fail("resume-handoff requires an active pending_delegation")
    try:
        if os.path.isabs(pending):
            resolved = os.path.realpath(pending)
        elif pending.startswith(".aicontext/"):
            resolved = state.resolve_scoped_path(session_dir, "workspace", pending)
        else:
            resolved = state.resolve_scoped_path(session_dir, "session", pending)
    except ValueError as err:
        _fail(str(err))
    root = os.path.realpath(os.path.join(session_dir, "delegations"))
    session_root = os.path.realpath(session_dir)
    try:
        root_is_contained = os.path.commonpath((session_root, root)) == session_root
        contained = os.path.commonpath((root, resolved)) == root
    except ValueError:
        root_is_contained = contained = False
    if not root_is_contained or not contained or not os.path.isfile(resolved):
        _fail("pending delegation envelope must exist inside session delegations/")
    lines = text.read_lines(resolved)
    fields: dict[str, str] = {}
    for line in lines:
        match = _ENVELOPE_FIELD.match(line)
        if match:
            fields[match.group(1).lower()] = match.group(2).strip("` ")
    return resolved, fields, lines


def _resume_packet(
    session_dir: str,
    expected_phase: str,
    answers: list[list[str]] | None,
) -> tuple[str, str]:
    profile = _load_profile(session_dir, expected_phase)
    envelope_path, fields, lines = _resolve_pending_envelope(session_dir)
    records = text.read_lines(state.state_file_of(session_dir))
    if not yamlscan.pending_delegation_active(records):
        _fail("resume-handoff requires an active pending_delegation")
    pending_agent = yamlscan.trim_scalar(yamlscan.pending_delegation_value("agent", records))
    pending_phase = yamlscan.trim_scalar(yamlscan.pending_delegation_value("phase", records))
    pending_id = yamlscan.trim_scalar(yamlscan.pending_delegation_value("delegation_id", records))
    phase_status = yamlscan.trim_scalar(
        yamlscan.nested_value("phases", expected_phase, "status", records)
    )
    gate_status = yamlscan.trim_scalar(
        yamlscan.nested_value("gates", expected_phase, "status", records)
    )
    if pending_phase != profile["phase"] or phase_status != "blocked" or gate_status != "paused":
        _fail("pending delegation must block the current phase and pause its gate")
    _validate_question_envelope(
        fields,
        lines,
        profile["agent"],
        profile["phase"],
        pending_id,
    )
    if pending_agent != profile["agent"]:
        _fail("pending delegation agent does not match phase profile")

    questions = _section(lines, "## Questions")
    checkpoint = _section(lines, "## Checkpoint")
    resume_contract = _section(lines, "## Resume Contract")
    question_ids = [
        match.group(1)
        for line in questions
        if (match := re.match(r"^###\s+`?([^`\s]+)`?\s*$", line))
    ]
    answer_map: dict[str, tuple[str, str]] = {}
    for question_id, selected, answer in answers or []:
        if question_id in answer_map:
            _fail(f"duplicate resume answer: {question_id}")
        if not re.fullmatch(r"(?:none|[A-Za-z0-9][A-Za-z0-9._-]*)", selected):
            _fail(f"resume selected option is invalid: {question_id}")
        if not answer.strip():
            _fail(f"resume answer must not be empty: {question_id}")
        answer_map[question_id] = (selected, answer)
    unknown = sorted(set(answer_map) - set(question_ids))
    missing = sorted(set(question_ids) - set(answer_map))
    if unknown:
        _fail("resume answers contain unknown question IDs: " + ", ".join(unknown))
    if missing:
        _fail("resume answers are missing question IDs: " + ", ".join(missing))

    out = [
        "## Resume Context",
        "",
        "This request is self-contained. The original question envelope was removed after these answers were validated.",
        "",
        f"- **Delegation:** `{pending_id}`",
        f"- **Agent:** `{profile['agent']}`",
        f"- **Phase:** `{profile['phase']}`",
        "",
        "### User answers",
        "",
    ]
    answered_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for question_id in question_ids:
        selected, answer = answer_map[question_id]
        out.extend(
            [
                f"#### `{question_id}`",
                "",
                f"- **Selected option:** `{selected}`",
                "- **Answer:**",
                *_fenced_text(answer),
                "- **Answered by:** `user`",
                f"- **Answered at:** `{answered_at}`",
                "",
            ]
        )
    out.extend(
        [
            "### Original questions",
            "",
            *questions[1:],
            "",
            "### Checkpoint",
            "",
            *checkpoint[1:],
            "",
            "### Resume contract",
            "",
            *resume_contract[1:],
            "",
            "Resume the paused delegation without restarting. Apply every answer to the owned artifact, validate the checkpoint, and continue from Resume from.",
        ]
    )
    return "\n".join(out).rstrip() + "\n", envelope_path


def build_resumed_request(
    session_dir: str,
    expected_phase: str,
    answers: list[list[str]] | None,
) -> tuple[str, str, str]:
    path = _safe_request_path(session_dir, expected_phase, create=False)
    if not os.path.isfile(path):
        _fail("resume-handoff requires an existing request")
    base_path = _safe_base_request_path(session_dir, expected_phase, create=False)
    if not os.path.isfile(base_path):
        _fail("resume-handoff requires an existing request base")
    packet, envelope = _resume_packet(session_dir, expected_phase, answers)
    base = "\n".join(text.read_lines(base_path)).rstrip() + "\n"
    marker = "## Successful handoff"
    if base.count(marker) != 1:
        _fail("generated request base must contain exactly one successful handoff section")
    request = base.replace(marker, packet + "\n" + marker, 1)
    return path, request, envelope


def _require_allowed(profile: dict[str, Any], used: set[str]) -> None:
    allowed = set(profile["allowed_flags"])
    unsupported = sorted(used - allowed)
    if unsupported:
        _fail(
            f"phase {profile['phase']} does not allow flags: "
            + ", ".join("--" + item for item in unsupported)
        )


def manifest_payload(args: Any, profile: dict[str, Any]) -> dict[str, Any]:
    used: set[str] = set()
    artifacts = {name: dict(value) for name, value in profile["artifacts"].items()}
    fixed_artifact_names = set(artifacts)
    for name, kind, scope, path in args.artifact or []:
        used.add("artifact")
        if name in artifacts:
            if name in fixed_artifact_names:
                _fail(f"--artifact must not redeclare fixed artifact: {name}")
            _fail(f"duplicate artifact name: {name}")
        artifacts[name] = {"kind": kind, "scope": scope, "path": path}

    specs = []
    for name, scope, path, relation in args.spec or []:
        used.add("spec")
        if name in artifacts:
            _fail(f"duplicate artifact name: {name}")
        artifacts[name] = {"kind": "spec", "scope": scope, "path": path}
        specs.append({"artifact": name, "relation": relation})

    replacements = {}
    for name, scope, path in args.replace_spec or []:
        used.add("replace-spec")
        if name in replacements:
            _fail(f"duplicate spec replacement: {name}")
        replacements[name] = {"scope": scope, "path": path}
    for item in specs:
        if item["artifact"] in replacements:
            item["replaces"] = replacements.pop(item["artifact"])
    if replacements:
        _fail("--replace-spec names undeclared specs: " + ", ".join(sorted(replacements)))

    mappings = []
    for contract, spec, ac_csv in args.contract_map or []:
        used.add("contract-map")
        mappings.append(
            {"contract": contract, "spec": spec, "acs": [item.strip() for item in ac_csv.split(",") if item.strip()]}
        )
    removals = []
    for scope, path in args.remove_spec or []:
        used.add("remove-spec")
        removals.append({"scope": scope, "path": path})
    deletions = []
    for scope, registered_path, package in args.delete_spec or []:
        used.add("delete-spec")
        deletions.append({"registered": {"scope": scope, "path": registered_path}, "package": package})
    blockers = []
    for artifact, blocker_id in args.blocker or []:
        used.add("blocker")
        blockers.append({"artifact": artifact, "id": blocker_id})

    _require_allowed(profile, used)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "phase": profile["phase"],
        "status": args.status,
        "artifacts": artifacts,
        "blocker_refs": blockers,
    }
    if specs:
        payload["specs"] = specs
    if removals:
        payload["spec_removals"] = removals
    if deletions:
        payload["spec_deletions"] = deletions
    if mappings:
        payload["contract_mappings"] = mappings
    return payload


def submit_manifest(args: Any) -> str:
    profile = _require_active_delegated_phase(args.session, args.expect_phase)
    payload = manifest_payload(args, profile)
    handoff_dir = _safe_handoffs_root(args.session)
    final_path = os.path.join(handoff_dir, f"{args.expect_phase}-handoff.yml")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{args.expect_phase}-handoff-", suffix=".yml", dir=handoff_dir, text=True
    )
    try:
        with os.fdopen(fd, "w") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)
        handoffs.load_manifest(args.session, temporary)
        os.replace(temporary, final_path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise
    return _workspace_relative(args.session, final_path)
