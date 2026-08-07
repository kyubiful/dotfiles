"""Journal loading, rendering, and atomic persistence."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .errors import SetupError
from .models import ExistingArtifacts, JournalData, RepoOutcome, TechPlan
from .repositories import journal_display_path
from .text import clean_cell, normalise_repo_name, parse_table


TASK_STATUSES = {
    "pending",
    "partial",
    "blocked",
    "done",
    "failed-validation",
    "deferred",
    "n/a",
    "accepted-risk",
}
PHASE_STATUSES = {"pending", "in-progress", "done", "partial", "blocked"}
OVERALL_STATUSES = {
    "in-progress",
    "complete",
    "complete-with-follow-ups",
    "blocked",
    "failed",
}
OPEN_TASK_STATUSES = {"pending", "partial", "blocked", "failed-validation"}
TERMINAL_TASK_STATUSES = {"done", "deferred", "n/a", "accepted-risk"}


def _table_after_heading(text: str, heading: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    heading_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().casefold() == heading.casefold()
        ),
        None,
    )
    if heading_index is None:
        return []
    table: list[str] = []
    for line in lines[heading_index + 1 :]:
        if line.startswith("## "):
            break
        if line.strip().startswith("|"):
            table.append(line)
        elif table and line.strip():
            break
    return parse_table(table)


def load_journal(path: Path | None) -> JournalData:
    if path is None or not path.is_file():
        return JournalData()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"cannot read journal {path}: {exc}") from exc
    return load_journal_from_text(text)


def load_journal_from_text(text: str) -> JournalData:
    if not text:
        return JournalData()
    repositories: dict[str, ExistingArtifacts] = {}

    def artifact_value(value: str) -> str:
        cleaned = clean_cell(value)
        return "" if cleaned.casefold() in {"", "n/a", "none", "null", "-"} else cleaned

    for row in _table_after_heading(text, "## Repositories"):
        repo = normalise_repo_name(row.get("repo", ""))
        if repo:
            repositories[repo] = ExistingArtifacts(
                issue=artifact_value(row.get("issue", "")),
                branch=artifact_value(row.get("branch", "")),
                pr=artifact_value(row.get("pr", "")),
                github_repo=artifact_value(row.get("github repo", "")),
            )
    task_rows: dict[str, dict[str, str]] = {}
    for row in _table_after_heading(text, "## Task Progress"):
        task_id = clean_cell(row.get("#", ""))
        if task_id:
            task_rows[task_id] = row
    phase_rows: dict[str, dict[str, str]] = {}
    for row in _table_after_heading(text, "## Phase Status"):
        phase = clean_cell(row.get("phase", ""))
        if phase:
            phase_rows[phase] = row
    overall_status = ""
    for line in text.splitlines():
        if line.startswith("> Status:"):
            overall_status = line.split(":", 1)[1].strip()
            break
    return JournalData(
        repositories=repositories,
        task_rows=task_rows,
        phase_rows=phase_rows,
        overall_status=overall_status,
    )


def _markdown_cell(value: Any) -> str:
    value = str(value)
    return value.replace("|", "\\|").replace("\n", " ").strip() or "n/a"


def _replace_table_rows(
    text: str,
    heading: str,
    header: list[str],
    rows: list[list[str]],
) -> str:
    lines = text.splitlines()
    heading_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().casefold() == heading.casefold()
        ),
        None,
    )
    if heading_index is None:
        raise SetupError(f"journal is missing {heading}")
    table_start = next(
        (
            index
            for index in range(heading_index + 1, len(lines))
            if lines[index].strip().startswith("|")
        ),
        None,
    )
    if table_start is None:
        raise SetupError(f"journal {heading} has no table")
    table_end = table_start
    while table_end < len(lines) and lines[table_end].strip().startswith("|"):
        table_end += 1
    rendered = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("-" * max(3, len(column)) for column in header) + "|",
    ]
    rendered.extend(
        "| " + " | ".join(_markdown_cell(value) for value in row) + " |"
        for row in rows
    )
    return "\n".join(lines[:table_start] + rendered + lines[table_end:]) + "\n"


def _replace_overall_status(text: str, overall_status: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("> Status:"):
            lines[index] = f"> Status: {overall_status}"
            return "\n".join(lines) + "\n"
    raise SetupError("journal is missing > Status:")


def _checkpoint_error(message: str) -> SetupError:
    return SetupError(f"journal checkpoint: {message}")


def apply_journal_checkpoint(path: Path, payload: dict[str, Any]) -> JournalData:
    """Apply and verify one lifecycle journal checkpoint atomically.

    ``payload`` supports ``task_updates`` (list of task_id/status/notes), one
    ``phase_update`` (phase/status/notes), and an optional ``overall_status``.
    The operation updates only Task Progress, Phase Status, and the front-matter
    status; phase-specific evidence and narrative remain preserved in the journal.
    """
    if not path.is_file():
        raise _checkpoint_error(f"journal not found: {path}")
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _checkpoint_error(f"cannot read {path}: {exc}") from exc
    journal = load_journal_from_text(source)
    if not journal.task_rows or not journal.phase_rows:
        raise _checkpoint_error("journal must contain Task Progress and Phase Status rows")

    updates = payload.get("task_updates", [])
    if not isinstance(updates, list):
        raise _checkpoint_error("task_updates must be a list")
    updated_task_ids: set[str] = set()
    for update in updates:
        if not isinstance(update, dict):
            raise _checkpoint_error("each task update must be an object")
        task_id = clean_cell(update.get("task_id", ""))
        status = clean_cell(update.get("status", "")).casefold()
        if not task_id or task_id not in journal.task_rows:
            raise _checkpoint_error(f"unknown task ID: {task_id or '<blank>'}")
        if task_id in updated_task_ids:
            raise _checkpoint_error(f"duplicate task update: {task_id}")
        if status not in TASK_STATUSES:
            raise _checkpoint_error(f"invalid status for task {task_id}: {status or '<blank>'}")
        notes = clean_cell(update.get("notes", ""))
        if status in {"deferred", "n/a", "accepted-risk"} and not notes:
            raise _checkpoint_error(f"task {task_id} requires notes for status {status}")
        journal.task_rows[task_id]["status"] = status
        journal.task_rows[task_id]["notes"] = notes or "n/a"
        updated_task_ids.add(task_id)

    phase_update = payload.get("phase_update")
    if not isinstance(phase_update, dict):
        raise _checkpoint_error("phase_update must be an object")
    phase = clean_cell(phase_update.get("phase", ""))
    phase_status = clean_cell(phase_update.get("status", "")).casefold()
    phase_notes = clean_cell(phase_update.get("notes", ""))
    if phase not in journal.phase_rows:
        raise _checkpoint_error(f"unknown phase: {phase or '<blank>'}")
    if phase_status not in PHASE_STATUSES:
        raise _checkpoint_error(f"invalid status for {phase}: {phase_status or '<blank>'}")
    if not phase_notes:
        raise _checkpoint_error(f"{phase} requires checkpoint notes")
    journal.phase_rows[phase]["status"] = phase_status
    journal.phase_rows[phase]["notes"] = phase_notes

    task_statuses = {
        task_id: clean_cell(row.get("status", "")).casefold()
        for task_id, row in journal.task_rows.items()
    }
    if phase_status == "done" and phase in {"2 — Coding", "4 — Validation", "5 — Commit"}:
        open_tasks = sorted(
            task_id for task_id, status in task_statuses.items() if status in OPEN_TASK_STATUSES
        )
        if open_tasks:
            raise _checkpoint_error(
                f"cannot mark {phase} done while Task Progress remains open: {', '.join(open_tasks)}"
            )

    overall_status = payload.get("overall_status")
    if phase == "5 — Commit" and phase_status == "done" and overall_status is None:
        raise _checkpoint_error("5 — Commit requires an overall status when marked done")
    if overall_status is not None:
        overall_status = clean_cell(overall_status).casefold()
        if overall_status not in OVERALL_STATUSES:
            raise _checkpoint_error(f"invalid overall status: {overall_status or '<blank>'}")
        if overall_status == "complete" and any(
            status != "done" for status in task_statuses.values()
        ):
            raise _checkpoint_error("complete requires every task to be done")
        if overall_status == "complete-with-follow-ups" and any(
            status not in TERMINAL_TASK_STATUSES for status in task_statuses.values()
        ):
            raise _checkpoint_error(
                "complete-with-follow-ups requires every task to have a terminal disposition"
            )
        if overall_status == "complete-with-follow-ups" and not any(
            status in {"deferred", "n/a", "accepted-risk"}
            for status in task_statuses.values()
        ):
            raise _checkpoint_error(
                "complete-with-follow-ups requires at least one follow-up disposition"
            )

    task_header = ["#", "Task", "Repo", "Status", "Phase", "Notes"]
    task_rows = [
        [
            task_id,
            row.get("task", ""),
            row.get("repo", ""),
            row.get("status", ""),
            row.get("phase", ""),
            row.get("notes", ""),
        ]
        for task_id, row in journal.task_rows.items()
    ]
    content = _replace_table_rows(source, "## Task Progress", task_header, task_rows)
    phase_header = ["Phase", "Status", "Notes"]
    phase_rows = [
        [phase_name, row.get("status", ""), row.get("notes", "")]
        for phase_name, row in journal.phase_rows.items()
    ]
    content = _replace_table_rows(content, "## Phase Status", phase_header, phase_rows)
    if overall_status is not None:
        content = _replace_overall_status(content, overall_status)
    write_journal(path, content)

    verified = load_journal(path)
    for task_id in updated_task_ids:
        if verified.task_rows.get(task_id, {}).get("status", "").casefold() != task_statuses[task_id]:
            raise _checkpoint_error(f"verification failed for task {task_id}")
    phase_row = verified.phase_rows.get(phase, {})
    if phase_row.get("status", "").casefold() != phase_status:
        raise _checkpoint_error(f"verification failed for {phase}")
    if overall_status is not None and verified.overall_status.casefold() != overall_status:
        raise _checkpoint_error("verification failed for overall status")
    return verified


def _existing_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().casefold() == heading.casefold()
        ),
        None,
    )
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _default_evidence_section() -> str:
    return (
        "## Implementation Evidence\n\n"
        "<!-- Populated only from completed or partially completed Phase 2 reports. -->\n\n"
        "| Evidence ID | Task IDs | Linked ACs | Repo | Files / Commands | Result |\n"
        "|-------------|----------|------------|------|------------------|--------|"
    )


def _default_decisions_section() -> str:
    return (
        "## Key Decisions\n\n"
        "<!-- Non-obvious implementation choices, tagged by repo. -->\n\n"
        "| Decision | Repo | Rationale | Alternatives |\n"
        "|----------|------|-----------|-------------|"
    )


def _default_iterations_section() -> str:
    return (
        "## Continuation Iterations\n\n"
        "<!-- Leave empty for an initial delivery. -->\n\n"
        "| Iteration | Requested Change | Strategy | Evidence Baseline | Phase Dispositions | Validation Scope | Escalation / Blocker |\n"
        "|-----------|------------------|----------|-------------------|--------------------|------------------|----------------------|"
    )


def _default_handoffs_section() -> str:
    return (
        "## CI Handoffs\n\n"
        "<!-- One row per CI trigger between coding phases. -->\n\n"
        "| Exec Phase | Repo | Action | PR Comment | Artifact | Status |\n"
        "|------------|------|--------|------------|----------|--------|"
    )


def _phase_status(outcomes: list[RepoOutcome], delivery_mode: str) -> tuple[str, str]:
    if not outcomes:
        return "blocked", "no target repository setup was produced"
    if any(outcome.status == "blocked" or outcome.blockers for outcome in outcomes):
        return "blocked", "one or more repositories require user action"
    if any(outcome.backlog_link_status == "blocked" for outcome in outcomes):
        return "blocked", "backlog parent relationship requires user action"
    return "done", (
        "verified one Phase 1 execution context per target repository; "
        f"delivery_mode={delivery_mode}"
    )


def render_journal(
    *,
    plan: TechPlan,
    session_slug: str,
    session_path: Path,
    delivery_mode: str,
    outcomes: list[RepoOutcome],
    existing_text: str = "",
    sdd_state_exists: bool = False,
) -> str:
    phase1, phase1_notes = _phase_status(outcomes, delivery_mode)
    journal_data = load_journal_from_text(existing_text)
    previous_overall = journal_data.overall_status
    overall = (
        "blocked"
        if phase1 == "blocked"
        else previous_overall
        if previous_overall in {"in-progress", "complete", "complete-with-follow-ups", "failed"}
        else "in-progress"
    )
    tech_plan_display = journal_display_path(Path(plan.path), session_path)
    lines = [
        f"# Implementation Journal — {session_slug}",
        "",
        f"> Tech plan: `{tech_plan_display}`",
        f"> Delivery mode: {delivery_mode}",
        f"> Started: {dt.date.today().isoformat()}",
        f"> Status: {overall}",
        "",
        "## Repositories",
        "",
        "<!-- The local checkout path is runtime-only and is intentionally not persisted. -->",
        "",
        "| Repo | GitHub Repo | Branch | Issue | PR | Status |",
        "|------|-------------|--------|-------|----|--------|",
    ]
    for outcome in outcomes:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    outcome.target_repo,
                    outcome.github_repo if delivery_mode == "github-delivery" else "n/a",
                    outcome.branch,
                    outcome.issue_url if delivery_mode == "github-delivery" else "n/a",
                    outcome.pr_url if delivery_mode == "github-delivery" else "n/a",
                    outcome.status,
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Backlog Links",
            "",
            "<!-- Parent references are non-closing relationships. -->",
            "",
            "| Backlog ID | Parent Issue | Technical Issue | Repo | Link Type | Status | Notes |",
            "|------------|--------------|-----------------|------|-----------|--------|-------|",
        ]
    )
    for outcome in outcomes:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    outcome.backlog_id,
                    outcome.parent_issue,
                    outcome.issue_url,
                    outcome.target_repo,
                    outcome.link_type,
                    outcome.backlog_link_status,
                    outcome.backlog_link_notes,
                )
            )
            + " |"
        )

    phase_by_task: dict[str, str] = {}
    for execution_phase in plan.execution_order:
        for task_ref in execution_phase.task_refs:
            phase_by_task[task_ref] = execution_phase.phase
    lines.extend(
        [
            "",
            "## Task Progress",
            "",
            "| # | Task | Repo | Status | Phase | Notes |",
            "|---|------|------|--------|-------|-------|",
        ]
    )
    for task in plan.tasks:
        previous = journal_data.task_rows.get(task.task_id, {})
        status = previous.get("status", "pending") or "pending"
        notes = previous.get("notes", "n/a") or "n/a"
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    task.task_id,
                    task.title,
                    task.repo,
                    status,
                    phase_by_task.get(task.task_id, "n/a"),
                    notes,
                )
            )
            + " |"
        )

    preserved_sections = [
        _existing_section(existing_text, "## Implementation Evidence")
        or _default_evidence_section(),
        _existing_section(existing_text, "## Key Decisions") or _default_decisions_section(),
        _existing_section(existing_text, "## Continuation Iterations")
        or _default_iterations_section(),
        _existing_section(existing_text, "## CI Handoffs") or _default_handoffs_section(),
    ]
    lines.extend(["", "", "\n\n".join(preserved_sections), "", "## Phase Status", ""])
    lines.extend(["| Phase | Status | Notes |", "|-------|--------|-------|"])
    lines.append(f"| 1 — Delivery Setup | {phase1} | {_markdown_cell(phase1_notes)} |")
    phase_defaults = {
        "2 — Coding": ("pending", "waiting for Phase 1 gate"),
        "3 — PaaS Config": ("pending", "waiting for Phase 2"),
        "4 — Validation": ("pending", "waiting for implementation"),
        "5 — Commit": ("pending", "waiting for validation"),
    }
    for phase, (default_status, default_notes) in phase_defaults.items():
        previous = journal_data.phase_rows.get(phase, {})
        status = clean_cell(previous.get("status", "")) or default_status
        notes = clean_cell(previous.get("notes", "")) or default_notes
        lines.append(f"| {phase} | {_markdown_cell(status)} | {_markdown_cell(notes)} |")
    if sdd_state_exists:
        lines.extend(
            [
                "",
                "<!-- Proposed SDD state update: artifacts.code_journal = code.md. "
                "This script does not mutate sdd-state.yml. -->",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_journal(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        raise SetupError(f"cannot write journal {path}: {exc}") from exc
