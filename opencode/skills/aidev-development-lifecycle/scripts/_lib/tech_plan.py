"""Fence-aware parsing for Markdown tech plans."""
from __future__ import annotations

import re
from pathlib import Path

from .errors import SetupError
from .models import (
    BacklogCandidate,
    ExecutionPhase,
    Gate,
    Task,
    TechPlan,
)
from .text import (
    find_heading,
    headings,
    normalise_repo_name,
    parse_issue_url,
    parse_table,
    repo_names,
    section_bounds,
    without_fenced_lines,
)


TASK_HEADING_RE = re.compile(r"^Task\s+([^:]+?)\s*:\s*(.+)$", re.IGNORECASE)
GATE_HEADING_RE = re.compile(
    r"^Gate:\s*(.+?)(?:\s+\(after\s+Tasks?\s+(.+?)\))?\s*$",
    re.IGNORECASE,
)
FIELD_RE = re.compile(r"^\s*-\s+\*\*([^*]+)\*\*:\s*(.*)$")
CHECKBOX_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+(.*)$")

EXCLUDED_CHECK_HINTS = (
    "acceptance criteria",
    "functional",
    "user journey",
    "e2e",
    "end-to-end",
    "manual",
    "visual",
    "screenshot",
    "vcp",
    "browser",
    "click through",
    "click-through",
    "ux ",
    "user-facing",
)
UNBOUNDED_CHECK_HINTS = (
    "watch",
    "interactive",
    "long-lived",
    "foreground process",
    "run the server",
    "start the server",
    "npm run dev",
    "yarn dev",
    "pnpm dev",
    "npm start",
    "yarn start",
    "pnpm start",
    "cargo watch",
    "--continuous",
    "docker compose up",
)
TECHNICAL_CHECK_HINTS = (
    "build",
    "compile",
    "test",
    "lint",
    "typecheck",
    "type check",
    "static analysis",
    "format",
    "coverage",
    "regression",
    "dependency audit",
    "security scan",
)


def _plan_title(heading_list: list[tuple[int, int, str]]) -> str:
    for _, level, title in heading_list:
        if level == 1:
            value = re.sub(r"^Tech\s+Plan\s*:\s*", "", title, flags=re.IGNORECASE)
            value = re.sub(r"^[A-Z][A-Z0-9_-]*-\d+\s*:\s*", "", value)
            return value.strip()
    raise SetupError("tech plan must contain a level-one title heading")


def _field_value(fields: dict[str, str], *names: str) -> str:
    for name in names:
        value = fields.get(name.casefold())
        if value:
            return value.strip()
    return ""


def _parse_dependencies(value: str) -> list[str]:
    value = value.strip()
    if not value or value.casefold() in {"n/a", "none", "-"}:
        return []
    values = re.split(r"[,;]", value)
    result: list[str] = []
    for item in values:
        item = re.sub(r"^\s*Tasks?\s+", "", item.strip(), flags=re.IGNORECASE)
        if item:
            result.append(item)
    return result


def _task_from_block(
    lines: list[str], start: int, end: int, heading_title: str
) -> Task:
    match = TASK_HEADING_RE.match(heading_title)
    if not match:
        raise SetupError(f"invalid task heading at line {start + 1}: {heading_title}")
    task_id = match.group(1).strip()
    title = match.group(2).strip()
    fields: dict[str, str] = {}
    active_field = ""
    for line in without_fenced_lines(lines[start + 1 : end]):
        field_match = FIELD_RE.match(line)
        if field_match:
            active_field = field_match.group(1).strip().casefold()
            fields[active_field] = field_match.group(2).strip()
            continue
        if active_field and line.startswith(("  ", "\t")) and line.strip():
            fields[active_field] = f"{fields[active_field]}\n{line.strip()}".strip()

    repo = _field_value(fields, "repo", "repository")
    if not repo:
        raise SetupError(f"Task {task_id} is missing its Repo field (line {start + 1})")
    repositories = repo_names(repo)
    if not repositories:
        raise SetupError(f"Task {task_id} has no valid repository name (line {start + 1})")
    exit_criteria = [
        match.group(1).strip()
        for line in without_fenced_lines(lines[start:end])
        if (match := CHECKBOX_RE.match(line))
    ]
    if task_id == "":
        raise SetupError(f"task at line {start + 1} has an empty stable ID")
    return Task(
        task_id=task_id,
        title=title,
        repo=", ".join(repositories),
        module=_field_value(fields, "module"),
        backlog_item=_field_value(fields, "backlog item") or "n/a",
        dependencies=_parse_dependencies(_field_value(fields, "depends on")),
        where=_field_value(fields, "where"),
        details=_field_value(fields, "how", "details"),
        exit_criteria=exit_criteria,
        markdown="\n".join(lines[start:end]).strip(),
        start_line=start + 1,
        end_line=end,
    )


def _is_excluded_check(value: str) -> bool:
    lower = value.casefold()
    return any(hint in lower for hint in EXCLUDED_CHECK_HINTS) or any(
        hint in lower for hint in UNBOUNDED_CHECK_HINTS
    )


def _is_technical_check(value: str) -> bool:
    lower = value.casefold()
    if _is_excluded_check(value):
        return False
    if re.search(r"`[^`]+`", value):
        return True
    return any(hint in lower for hint in TECHNICAL_CHECK_HINTS)


def _gate_checks(section_lines: list[str]) -> list[str]:
    section_lines = without_fenced_lines(section_lines)
    technical_line = None
    for index, line in enumerate(section_lines):
        if re.search(r"\*\*Technical checks:\*\*", line, re.IGNORECASE):
            technical_line = index
            break
    if technical_line is None:
        return []
    checks: list[str] = []
    for line in section_lines[technical_line + 1 :]:
        match = re.match(r"^\s*-\s+(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if _is_technical_check(value):
            checks.append(f"- {value}")
    return checks


def _parse_task_refs(value: str) -> list[str]:
    value = re.sub(r"\bTasks?\b", "", value, flags=re.IGNORECASE)
    values = re.split(r"[,;&]", value)
    result: list[str] = []
    for item in values:
        item = item.strip().strip(".()")
        if not item:
            continue
        match = re.search(r"(?:[A-Za-z][A-Za-z0-9_.-]*|\d+)", item)
        if match:
            result.append(match.group(0))
    return result


def _parse_gate(
    lines: list[str], start: int, end: int, heading_title: str
) -> Gate:
    match = GATE_HEADING_RE.match(heading_title)
    if not match:
        raise SetupError(f"invalid gate heading at line {start + 1}: {heading_title}")
    repo = normalise_repo_name(match.group(1).strip())
    task_refs = _parse_task_refs(match.group(2) or "")
    return Gate(
        repo=repo,
        task_refs=task_refs,
        checks=_gate_checks(lines[start + 1 : end]),
        start_line=start + 1,
        end_line=end,
    )


def _parse_backlog_sources(
    lines: list[str], heading_list: list[tuple[int, int, str]], plan_path: Path
) -> list[BacklogCandidate]:
    index = find_heading(heading_list, "Backlog Sources", level=2)
    if index is None:
        return []
    start, end = section_bounds(lines, heading_list, index, 2)
    rows = parse_table(lines[start + 1 : end])
    candidates: list[BacklogCandidate] = []
    for row in rows:
        issue = row.get("github issue", "")
        parsed = parse_issue_url(issue)
        if not parsed:
            continue
        repo, number = parsed
        candidates.append(
            BacklogCandidate(
                backlog_id=row.get("backlog id", "n/a") or "n/a",
                issue_url=issue,
                issue_number=number,
                repo=repo,
                source=f"tech-plan:{plan_path.name}",
            )
        )
    return candidates


def _parse_execution_order(
    lines: list[str], heading_list: list[tuple[int, int, str]]
) -> tuple[list[ExecutionPhase], str, str]:
    index = find_heading(heading_list, "Execution Order", level=2)
    if index is None:
        return [], "", ""
    start, end = section_bounds(lines, heading_list, index, 2)
    rows = parse_table(lines[start + 1 : end])
    phases: list[ExecutionPhase] = []
    for row in rows:
        phase = row.get("phase", "").strip()
        if not phase:
            continue
        phases.append(
            ExecutionPhase(
                phase=phase,
                task_refs=_parse_task_refs(row.get("tasks", "")),
                notes=row.get("notes", "").strip(),
            )
        )
    critical = ""
    parallel = ""
    for line in lines[start:end]:
        match = re.match(r"^\*\*([^*]+)\*\*:\s*(.*)$", line.strip())
        if not match:
            continue
        key = match.group(1).casefold()
        if key == "critical path":
            critical = match.group(2).strip()
        elif key == "parallelizable":
            parallel = match.group(2).strip()
    return phases, critical, parallel


def parse_tech_plan(path: str | Path) -> TechPlan:
    plan_path = Path(path).expanduser().resolve()
    if not plan_path.is_file():
        raise SetupError(f"tech plan not found: {plan_path}")
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"cannot read tech plan {plan_path}: {exc}") from exc
    lines = text.splitlines()
    heading_list = headings(lines)
    title = _plan_title(heading_list)

    tasks: list[Task] = []
    seen_ids: set[str] = set()
    for index, (line_index, level, heading_title) in enumerate(heading_list):
        if level != 3 or not heading_title.casefold().startswith("task "):
            continue
        _, end = section_bounds(lines, heading_list, index, 3)
        task = _task_from_block(lines, line_index, end, heading_title)
        if task.task_id in seen_ids:
            raise SetupError(f"duplicate task ID {task.task_id} (line {task.start_line})")
        seen_ids.add(task.task_id)
        tasks.append(task)
    if not tasks:
        raise SetupError("tech plan contains no ### Task sections")

    gates: list[Gate] = []
    for index, (line_index, level, heading_title) in enumerate(heading_list):
        if level != 3 or not heading_title.casefold().startswith("gate:"):
            continue
        _, end = section_bounds(lines, heading_list, index, 3)
        gates.append(_parse_gate(lines, line_index, end, heading_title))

    execution, critical, parallel = _parse_execution_order(lines, heading_list)
    return TechPlan(
        path=str(plan_path),
        title=title,
        tasks=tasks,
        gates=gates,
        execution_order=execution,
        critical_path=critical,
        parallelizable=parallel,
        backlog_candidates=_parse_backlog_sources(lines, heading_list, plan_path),
    )


def issue_body(tasks: list[Task], gates: list[Gate]) -> str:
    """Render the technical issue body from task Markdown and gate checks."""
    sections = [task.markdown for task in tasks]
    checks: list[str] = []
    for gate in gates:
        for check in gate.checks:
            if check not in checks:
                checks.append(check)
    if checks:
        sections.append("## Definition of Done\n\n" + "\n".join(checks))
    return "\n\n".join(section.strip() for section in sections if section.strip()).strip() + "\n"
