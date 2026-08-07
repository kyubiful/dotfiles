"""Deterministic trace views derived from canonical phase artifacts."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import yaml

from . import state, yamlscan


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    kind: str
    scope: str
    path: str
    resolved: str


def _cell(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).replace("|", "\\|")


def _read(path: str) -> list[str]:
    with open(path) as handle:
        return handle.read().splitlines()


def _section_exists(lines: list[str], name: str) -> bool:
    return f"## {name}" in lines


def _replace_section(lines: list[str], name: str, body: list[str]) -> list[str]:
    heading = f"## {name}"
    try:
        start = lines.index(heading)
    except ValueError:
        return lines
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    replacement = [heading, "", *body]
    if end < len(lines):
        replacement.append("")
    return lines[:start] + replacement + lines[end:]


def _table(lines: list[str], heading: str) -> list[dict[str, str]]:
    try:
        start = lines.index(heading)
    except ValueError:
        return []
    header: list[str] = []
    rows: list[dict[str, str]] = []
    for line in lines[start + 1:]:
        if line.startswith("## ") or line.startswith("### "):
            if header:
                break
            continue
        if not line.startswith("|"):
            if header and rows:
                break
            continue
        cols = [_cell(value) for value in line.strip().strip("|").split("|")]
        if not header:
            header = cols
            continue
        if all(re.fullmatch(r"[-: ]+", value) for value in cols):
            continue
        if len(cols) < len(header):
            cols += [""] * (len(header) - len(cols))
        rows.append({header[i]: cols[i] for i in range(len(header))})
    return rows


def _artifact(artifacts: dict[str, ArtifactRef], kind: str) -> ArtifactRef | None:
    return next((item for item in artifacts.values() if item.kind == kind), None)


def _extract_acceptance_criteria(path: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in _read(path):
        match = re.match(r"^\s*(?:[-*]|\|)?\s*(AC-[0-9]+)\s*[:|]\s*(.*?)(?:\|\s*)?$", line)
        if not match or match.group(1) in seen:
            continue
        criterion = match.group(2).strip()
        if criterion and not re.fullmatch(r"[-: ]+", criterion):
            out.append((match.group(1), criterion))
            seen.add(match.group(1))
    return out


def _spec_trace_rows(
    session_dir: str,
    state_records: list[str],
) -> tuple[list[str], list[str]]:
    rows: list[str] = []
    sources: list[str] = []
    for spec_path, spec_scope, _relation in yamlscan.parse_state_specs(state_records):
        path = yamlscan.trim_scalar(spec_path)
        scope = yamlscan.trim_scalar(spec_scope) or "session"
        if not path:
            continue
        resolved = state.resolve_scoped_path(session_dir, scope, path)
        display = path if scope == "session" else f"workspace:{path}"
        sources.append(display)
        for ac_id, criterion in _extract_acceptance_criteria(resolved):
            rows.append(
                f"| {_cell(ac_id)} | {_cell(criterion)} | {_cell(display)} | Derived from source spec. |"
            )
    return rows, sources


def _contract_entries(contracts_path: str) -> dict[str, str]:
    if not os.path.isfile(contracts_path):
        return {}
    return {
        yamlscan.trim_scalar(contract_id): yamlscan.trim_scalar(contract_path)
        for contract_id, contract_path, _sha256 in yamlscan.parse_contract_entries(
            _read(contracts_path)
        )
        if yamlscan.trim_scalar(contract_id)
    }


def _contract_body(
    contracts_path: str,
    mappings: list[tuple[str, str, tuple[str, ...]]],
) -> list[str]:
    contracts = _contract_entries(contracts_path)
    by_contract: dict[str, tuple[set[str], set[str]]] = {
        contract_id: (set(), set()) for contract_id in contracts
    }
    for contract_id, source, acs in mappings:
        mapped_acs, sources = by_contract.setdefault(contract_id, (set(), set()))
        mapped_acs.update(acs)
        sources.add(source)

    rows = []
    for contract_id, contract_path in contracts.items():
        acs, sources = by_contract.get(contract_id, (set(), set()))
        affected = ", ".join(sorted(acs)) or "[AIDEV_TODO]"
        evidence = (
            f"Mapped in {', '.join(sorted(sources))}."
            if sources
            else "[AIDEV_TODO]"
        )
        rows.append(
            f"| {_cell(contract_id)} | {_cell(contract_path)} | {affected} | {_cell(evidence)} |"
        )
    return [
        "| Contract ID | Path | Affected ACs | Evidence |",
        "|---|---|---|---|",
        *(rows or ["| N/A | N/A | N/A | No input contracts. |"]),
    ]


def upsert_contract_mapping(
    trace_path: str,
    contracts_path: str,
    contract_id: str,
    source: str,
    acs: tuple[str, ...],
) -> None:
    """Add a late contract mapping while preserving existing deterministic rows."""
    lines = _read(trace_path)
    if not _section_exists(lines, "Input Contract Trace"):
        raise ValueError("active trace template has no Input Contract Trace section")
    contracts = _contract_entries(contracts_path)
    if contract_id not in contracts:
        raise ValueError(f"contract not found in contracts.yml: {contract_id}")

    existing: dict[str, tuple[set[str], str]] = {}
    for row in _table(lines, "## Input Contract Trace"):
        current = row.get("Contract ID", "")
        if current not in contracts or current == "N/A":
            continue
        existing[current] = (
            set(re.findall(r"AC-[0-9]+", row.get("Affected ACs", ""))),
            row.get("Evidence", ""),
        )

    mapped_acs, evidence = existing.get(contract_id, (set(), ""))
    mapped_acs.update(acs)
    mapping_note = f"Mapped in {source}."
    if evidence in ("", "N/A", "[AIDEV_TODO]"):
        evidence = mapping_note
    elif source not in evidence:
        evidence = f"{evidence}; {mapping_note}"
    existing[contract_id] = (mapped_acs, evidence)

    body = [
        "| Contract ID | Path | Affected ACs | Evidence |",
        "|---|---|---|---|",
    ]
    for current, contract_path in contracts.items():
        current_acs, current_evidence = existing.get(current, (set(), ""))
        body.append(
            f"| {_cell(current)} | {_cell(contract_path)} | "
            f"{_cell(', '.join(sorted(current_acs)) or '[AIDEV_TODO]')} | "
            f"{_cell(current_evidence or '[AIDEV_TODO]')} |"
        )
    lines = _replace_section(
        lines,
        "Input Contract Trace",
        body,
    )
    with open(trace_path, "w") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def _backlog_body(artifact: ArtifactRef) -> list[str]:
    with open(artifact.resolved) as handle:
        data = yaml.safe_load(handle) or {}
    rows = []
    for item in data.get("backlog_items") or []:
        github = item.get("github") or {}
        issue = github.get("issue_url") or github.get("issue_number") or "N/A"
        project = github.get("project_number") or "N/A"
        sync = github.get("sync_status") or "not-published"
        decision = item.get("publish_decision") or "pending"
        rows.append(
            "| %s | %s | %s | %s | %s | publish_decision=%s |"
            % tuple(
                _cell(value)
                for value in (
                    item.get("id"), item.get("source_spec"), issue, project, sync, decision
                )
            )
        )
    return [
        "| Backlog ID | Source Spec | GitHub Issue | Project | Sync Status | Notes |",
        "|---|---|---|---|---|---|",
        *(rows or ["| N/A | N/A | N/A | N/A | not-applicable | No backlog items. |"]),
    ]


def _tech_plan_body(artifact: ArtifactRef) -> list[str]:
    lines = _read(artifact.resolved)
    coverage = _table(lines, "## AC Coverage")
    ac_by_task: dict[str, set[str]] = {}
    for row in coverage:
        acs = re.findall(r"AC-[0-9]+", " ".join(row.values()))
        tasks_value = next((v for k, v in row.items() if k.lower() == "tasks"), "")
        for task_num in re.findall(r"Task\s+([0-9]+)", tasks_value):
            ac_by_task.setdefault(task_num, set()).update(acs)

    tasks: list[tuple[str, str, str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        match = re.match(r"^### Task ([0-9]+):\s*(.+)$", line)
        if match:
            if current:
                tasks.append((current["id"], current["title"], current.get("repo", ""), current.get("what", "")))
            current = {"id": match.group(1), "title": match.group(2)}
            continue
        if not current:
            continue
        field = re.match(r"^- \*\*(Repo|What)\*\*:\s*(.*)$", line)
        if field:
            current[field.group(1).lower()] = field.group(2)
    if current:
        tasks.append((current["id"], current["title"], current.get("repo", ""), current.get("what", "")))

    rows = []
    for task_id, title, repo, what in tasks:
        acs = ", ".join(sorted(ac_by_task.get(task_id, set()))) or "N/A"
        rows.append(
            f"| Task {task_id} | {_cell(acs)} | {_cell(repo)} | {_cell(what or title)} | planned |"
        )
    return [
        "| Work Item | Linked ACs | Repository | Planned Change | Status |",
        "|---|---|---|---|---|",
        *(rows or ["| N/A | N/A | N/A | See tech-plan.md | planned |"]),
    ]


def _test_plan_body(artifact: ArtifactRef) -> list[str]:
    lines = _read(artifact.resolved)
    rows = _table(lines, "## Test Matrix")
    rendered = []
    linked_acs: set[str] = set()
    for row in rows:
        test_id = row.get("Test ID", "")
        if not re.fullmatch(r"TEST-[0-9]+", test_id):
            continue
        linked_acs.update(re.findall(r"AC-[0-9]+", row.get("Linked ACs", "")))
        rendered.append(
            f"| {_cell(test_id)} | {_cell(row.get('Linked ACs'))} | {_cell(row.get('Level'))} "
            f"| {_cell('EVID-TEST-' + test_id.split('-')[-1])} | planned |"
        )
    for row in _table(lines, "## Acceptance Criteria Coverage"):
        ac_id = row.get("AC ID", "")
        covering = row.get("Covering Tests", "")
        if (
            re.fullmatch(r"AC-[0-9]+", ac_id)
            and ac_id not in linked_acs
            and "gap" in covering.lower()
        ):
            rendered.append(
                f"| N/A | {_cell(ac_id)} | accepted-gap | N/A | accepted-gap |"
            )
    return [
        "| Test ID | Linked ACs | Level | Expected Evidence | Status |",
        "|---|---|---|---|---|",
        *rendered,
    ]


def _implementation_body(artifact: ArtifactRef) -> list[str]:
    rows = _table(_read(artifact.resolved), "## Implementation Evidence")
    rendered = []
    for row in rows:
        evidence = row.get("Evidence ID", "")
        if not evidence or evidence == "n/a":
            continue
        rendered.append(
            f"| {_cell(evidence)} | {_cell(row.get('Linked ACs'))} | "
            f"{_cell(row.get('Files / Commands'))} | {_cell(row.get('Result'))} | "
            f"Tasks: {_cell(row.get('Task IDs'))}; Repo: {_cell(row.get('Repo'))} |"
        )
    return [
        "| Evidence ID | Linked ACs | Files / Commands | Result | Notes |",
        "|---|---|---|---|---|",
        *rendered,
    ]


def _verification_bodies(artifact: ArtifactRef) -> tuple[list[str], list[str]]:
    lines = _read(artifact.resolved)
    ac_rows = _table(lines, "## Acceptance Criteria Verification")
    verification = []
    all_acs: list[str] = []
    for row in ac_rows:
        ac_id = row.get("AC ID", "")
        if not re.fullmatch(r"AC-[0-9]+", ac_id):
            continue
        all_acs.append(ac_id)
        verification.append(
            f"| {_cell(ac_id)} | {_cell(row.get('Evidence Reviewed'))} | "
            f"{_cell(row.get('Status'))} | {_cell(row.get('Notes'))} |"
        )

    body = "\n".join(lines)
    prs = list(dict.fromkeys(re.findall(r"https://github\.com/[^\s|)]+/pull/[0-9]+", body)))
    review_rows = _table(lines, "### Combined Gate Decision")
    review_status = "reviewed"
    if review_rows:
        fields = {row.get("Field", ""): row.get("Value", "") for row in review_rows}
        review_status = fields.get("Combined decision") or fields.get("Review decision") or review_status
    findings = _table(lines, "### Findings")
    blocking = sum(
        1
        for row in findings
        if row.get("Severity", "").lower() not in ("", "none")
        and row.get("Status", "").lower() not in ("closed", "resolved")
    )
    pr_rows = [
        f"| {_cell(pr)} | {_cell(', '.join(all_acs) or 'N/A')} | {_cell(review_status)} "
        f"| {blocking} | Derived from verification.md. |"
        for pr in prs
    ]
    if not pr_rows:
        pr_rows = [
            f"| N/A | {_cell(', '.join(all_acs) or 'N/A')} | {_cell(review_status)} "
            f"| {blocking} | No pull request recorded. |"
        ]
    return (
        [
            "| AC ID | Verification Evidence | Status | Notes |",
            "|---|---|---|---|",
            *verification,
        ],
        [
            "| PR | Linked ACs | Review Status | Blocking Findings | Notes |",
            "|---|---|---|---|---|",
            *pr_rows,
        ],
    )


def render_trace(
    trace_path: str,
    session_dir: str,
    phase: str,
    artifacts: dict[str, ArtifactRef],
    state_records: list[str],
    displayed_phase: str,
    contract_mappings: tuple[object, ...] = (),
) -> None:
    lines = _read(trace_path)
    session_id = ""
    track = ""
    for line in state_records:
        if re.match(r"^\s+id:", line) and not session_id:
            session_id = yamlscan.trim_scalar(re.sub(r"^\s+id:\s*", "", line))
        if line.startswith("track:"):
            track = yamlscan.trim_scalar(re.sub(r"^track:\s*", "", line))
    spec_rows, sources = _spec_trace_rows(session_dir, state_records)
    contracts = os.path.join(session_dir, "contracts.yml")
    if phase == "functional-spec" and _section_exists(lines, "Input Contract Trace"):
        mappings = []
        for mapping in contract_mappings:
            artifact = artifacts[mapping.spec]
            source = (
                artifact.path
                if artifact.scope == "session"
                else f"workspace:{artifact.path}"
            )
            mappings.append((mapping.contract, source, mapping.acs))
        lines = _replace_section(
            lines,
            "Input Contract Trace",
            _contract_body(contracts, mappings),
        )
    if phase != "discovery" and _section_exists(lines, "Session"):
        lines = _replace_section(
            lines,
            "Session",
            [
                "| Field | Value |",
                "|---|---|",
                f"| Session | {_cell(session_id)} |",
                f"| Track | {_cell(track)} |",
                f"| Source spec | {_cell(', '.join(sources) or 'N/A')} |",
                f"| Current phase | {_cell(displayed_phase)} |",
            ],
        )

    if phase == "functional-spec":
        if _section_exists(lines, "Acceptance Criteria Trace"):
            lines = _replace_section(
                lines,
                "Acceptance Criteria Trace",
                [
                    "| AC ID | Acceptance Criterion | Source Spec | Notes |",
                    "|---|---|---|---|",
                    *spec_rows,
                ],
            )
        backlog = _artifact(artifacts, "backlog")
        if backlog and _section_exists(lines, "Backlog Trace"):
            lines = _replace_section(lines, "Backlog Trace", _backlog_body(backlog))
    elif phase == "technical-plan":
        artifact = _artifact(artifacts, "technical-plan")
        if artifact:
            lines = _replace_section(lines, "Technical Plan Trace", _tech_plan_body(artifact))
    elif phase == "test-design":
        artifact = _artifact(artifacts, "test-plan")
        if artifact:
            lines = _replace_section(lines, "Test Design Trace", _test_plan_body(artifact))
    elif phase == "implementation":
        artifact = _artifact(artifacts, "code-journal")
        if artifact:
            lines = _replace_section(lines, "Implementation Trace", _implementation_body(artifact))
    elif phase == "spec-verification":
        artifact = _artifact(artifacts, "verification")
        if artifact:
            verification, prs = _verification_bodies(artifact)
            lines = _replace_section(lines, "Verification Trace", verification)
            lines = _replace_section(lines, "PR / Review Trace", prs)
    elif phase == "retro" and _section_exists(lines, "Acceptance Criteria Trace"):
        lines = _replace_section(
            lines,
            "Acceptance Criteria Trace",
            [
                "| AC ID | Acceptance Criterion | Source Spec | Notes |",
                "|---|---|---|---|",
                *(spec_rows or ["| N/A | N/A | N/A | No active specs remain. |"]),
            ],
        )

    with open(trace_path, "w") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
