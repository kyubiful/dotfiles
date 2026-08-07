"""Backlog-plan parsing and parent issue resolution."""
from __future__ import annotations

import re
from pathlib import Path

from .models import BacklogCandidate, ParentResolution, TechPlan
from .text import parse_issue_url, scalar


def _parse_backlog_yaml(path: Path) -> tuple[list[BacklogCandidate], list[str], list[str]]:
    """Parse the stable schema-v2 backlog projection without a YAML dependency."""
    if not path.is_file():
        return [], [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [], [f"cannot read backlog plan {path}: {exc}"]

    schema = ""
    for line in lines:
        match = re.match(r"^schema_version:\s*(.*)$", line)
        if match:
            schema = scalar(match.group(1))
            break
    errors: list[str] = []
    if schema != "2":
        errors.append(f"{path}: expected schema_version: 2")

    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_github = False
    for line in lines:
        item_match = re.match(r"^\s{2}-\s+id:\s*(.*)$", line)
        if item_match:
            if current is not None:
                items.append(current)
            current = {
                "id": scalar(item_match.group(1)),
                "publish_decision": "",
                "issue_url": "",
                "issue_number": "",
                "sync_status": "",
            }
            in_github = False
            continue
        if current is None:
            continue
        field_match = re.match(r"^(\s+)([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not field_match:
            continue
        indent = len(field_match.group(1).replace("\t", "    "))
        key = field_match.group(2)
        value = scalar(field_match.group(3))
        if indent == 4:
            in_github = key == "github"
            if key == "publish_decision":
                current[key] = value
        elif indent >= 6 and in_github:
            if key in {"issue_url", "issue_number", "sync_status"}:
                current[key] = value
    if current is not None:
        items.append(current)

    candidates: list[BacklogCandidate] = []
    unpublished: list[str] = []
    for item in items:
        identifier = item.get("id", "unknown")
        parsed = parse_issue_url(item.get("issue_url", ""))
        eligible = (
            item.get("publish_decision") == "approved"
            and item.get("sync_status") == "synced"
            and parsed is not None
        )
        if not eligible:
            unpublished.append(identifier)
            continue
        repo, number = parsed
        candidates.append(
            BacklogCandidate(
                backlog_id=identifier,
                issue_url=item["issue_url"],
                issue_number=number,
                repo=repo,
                source=f"backlog-plan:{path.name}",
            )
        )
    return candidates, unpublished, errors


def resolve_parent(
    plan: TechPlan, session_path: Path | None, backlog_path: Path | None
) -> ParentResolution:
    candidates = list(plan.backlog_candidates)
    unpublished: list[str] = []
    errors: list[str] = []
    yaml_path = backlog_path
    if yaml_path is None and session_path is not None:
        yaml_path = session_path / "backlog-plan.yml"
    if yaml_path is not None:
        yaml_candidates, yaml_unpublished, yaml_errors = _parse_backlog_yaml(yaml_path)
        candidates.extend(yaml_candidates)
        unpublished.extend(yaml_unpublished)
        errors.extend(yaml_errors)

    unique: dict[str, BacklogCandidate] = {}
    for candidate in candidates:
        existing = unique.get(candidate.issue_url)
        if existing is None:
            unique[candidate.issue_url] = candidate
        elif existing.backlog_id == "n/a" and candidate.backlog_id != "n/a":
            unique[candidate.issue_url] = candidate
    resolved = list(unique.values())
    if errors:
        return ParentResolution(
            status="blocked",
            candidates=resolved,
            unpublished_items=unpublished,
            source_errors=errors,
        )
    if len(resolved) == 1:
        return ParentResolution(
            status="resolved",
            candidate=resolved[0],
            candidates=resolved,
            unpublished_items=unpublished,
        )
    if len(resolved) > 1:
        return ParentResolution(
            status="ambiguous",
            candidates=resolved,
            unpublished_items=unpublished,
        )
    return ParentResolution(status="not-applicable", unpublished_items=unpublished)
