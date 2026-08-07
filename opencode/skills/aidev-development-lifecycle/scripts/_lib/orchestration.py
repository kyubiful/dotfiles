"""Inspect/apply workflows for deterministic Phase 1 setup."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .backlog import resolve_parent
from .errors import SetupError
from .github import (
    closing_reference,
    gh_issue_view,
    gh_pr_view,
    is_backlog_projection,
    label_names,
    reconcile_branch_and_pr,
    reconcile_issue,
    reconcile_parent_link,
    require_gh,
)
from .journal import load_journal, render_journal, write_journal
from .models import (
    ParentResolution,
    RepoOutcome,
    RepoPlan,
    TechPlan,
)
from .planning import (
    build_repo_plans,
    parent_dict,
    plan_dict,
    repo_plan_dict,
)
from .repositories import resolve_repositories, session_path
from .tech_plan import parse_tech_plan
from .text import issue_ref, slugify


def _inspect_github_state(
    repo_plans: list[RepoPlan], timeout: float
) -> tuple[dict[str, Any], list[str]]:
    states: dict[str, Any] = {}
    blockers: list[str] = []
    require_gh()
    for repo_plan in repo_plans:
        context = repo_plan.context
        if not context.github_repo or repo_plan.blockers:
            continue
        state: dict[str, Any] = {}
        issue_number: int | None = None
        if context.existing.issue:
            try:
                issue = gh_issue_view(context.github_repo, context.existing.issue, timeout)
                issue_number = int(issue["number"])
                state["issue"] = {
                    "url": issue.get("url"),
                    "number": issue.get("number"),
                    "state": issue.get("state"),
                    "is_backlog_projection": is_backlog_projection(issue),
                    "body_matches": str(issue.get("body") or "").rstrip()
                    == repo_plan.issue_body.rstrip(),
                    "labels": label_names(issue),
                }
                if is_backlog_projection(issue):
                    blockers.append(
                        f"journal issue for {context.target_repo} is a backlog projection; it will not be adopted"
                    )
            except SetupError as exc:
                blockers.append(str(exc))
        if context.existing.pr:
            try:
                pr = gh_pr_view(context.existing.pr, context.github_repo, timeout)
                state["pr"] = {
                    "url": pr.get("url"),
                    "state": pr.get("state"),
                    "is_draft": pr.get("isDraft"),
                    "head_branch": pr.get("headRefName"),
                    "closing_link_present": (
                        closing_reference(
                            str(pr.get("body") or ""),
                            context.github_repo,
                            issue_number,
                        )
                        if issue_number is not None
                        else None
                    ),
                }
                if str(pr.get("state", "")).casefold() == "open" and not pr.get("isDraft"):
                    blockers.append(f"existing PR is ready for review: {pr.get('url')}")
            except SetupError as exc:
                blockers.append(str(exc))
        states[context.target_repo] = state
    return states, blockers


def _outcome_from_local(repo_plan: RepoPlan) -> RepoOutcome:
    context = repo_plan.context
    return RepoOutcome(
        target_repo=context.target_repo,
        local_path=context.local_path,
        github_repo=context.github_repo,
        branch=context.current_branch or "n/a",
        status="local-only",
        issue_status="n/a",
        branch_status="reused",
        pr_status="n/a",
        selected_kind_label="n/a",
        backlog_id="n/a",
        parent_issue="n/a",
        link_type="n/a",
        backlog_link_status="n/a",
        backlog_link_notes="local-only delivery mode",
    )


def _blocked_outcome(repo_plan: RepoPlan, blockers: Iterable[str]) -> RepoOutcome:
    """Preserve journaled artifact references when a reconciliation is blocked."""
    context = repo_plan.context
    existing_issue = context.existing.issue or "n/a"
    issue_number: int | None = None
    parsed_issue = issue_ref(context.existing.issue) if context.existing.issue else None
    if parsed_issue:
        issue_number = parsed_issue[1]
    return RepoOutcome(
        target_repo=context.target_repo,
        local_path=context.local_path,
        github_repo=context.github_repo or context.existing.github_repo,
        branch=context.existing.branch or context.current_branch or "n/a",
        issue_url=existing_issue,
        issue_number=issue_number,
        pr_url=context.existing.pr or "n/a",
        status="blocked",
        issue_status="blocked",
        branch_status="blocked",
        pr_status="blocked",
        blockers=list(blockers),
    )


def apply_repo(
    repo_plan: RepoPlan,
    parent: ParentResolution,
    session_slug: str,
    timeout: float,
) -> RepoOutcome:
    context = repo_plan.context
    if repo_plan.blockers:
        return _blocked_outcome(repo_plan, repo_plan.blockers)
    if not context.current_branch:
        return _blocked_outcome(repo_plan, ["no working branch is checked out"])

    issue: dict[str, Any] | None = None
    outcome = RepoOutcome(
        target_repo=context.target_repo,
        local_path=context.local_path,
        github_repo=context.github_repo,
        selected_kind_label=repo_plan.kind_label,
    )
    try:
        issue, issue_status, label_note, issue_url = reconcile_issue(
            repo_plan, timeout=timeout
        )
        outcome.issue_status = issue_status
        outcome.issue_url = issue_url
        outcome.issue_number = int(issue["number"])
        outcome.label_note = label_note
        (
            outcome.link_type,
            outcome.backlog_link_status,
            outcome.parent_issue,
            outcome.backlog_link_notes,
            outcome.backlog_id,
        ) = reconcile_parent_link(issue, context, parent, session_slug, timeout)
        branch, pr_url, branch_status, pr_status = reconcile_branch_and_pr(
            repo_plan, outcome.issue_number, timeout=timeout
        )
        outcome.branch = branch
        outcome.pr_url = pr_url
        outcome.branch_status = branch_status
        outcome.pr_status = pr_status
        if outcome.backlog_link_status == "blocked":
            outcome.status = "partial"
            outcome.blockers.append(outcome.backlog_link_notes)
        elif issue_status == "updated":
            outcome.status = "refreshed"
        elif issue_status == "created" or branch_status == "created" or pr_status == "created":
            outcome.status = "created"
        else:
            outcome.status = "reused"
    except SetupError as exc:
        outcome.status = "blocked" if issue is None else "partial"
        outcome.blockers.append(str(exc))
    return outcome


def _inspect_payload(
    *,
    plan: TechPlan,
    parent: ParentResolution,
    repo_plans: list[RepoPlan],
    session_path: Path | None,
    journal_path: Path | None,
    github_states: dict[str, Any] | None = None,
    extra_blockers: Iterable[str] = (),
) -> dict[str, Any]:
    blockers = list(extra_blockers)
    blockers.extend(parent.source_errors)
    for repo_plan in repo_plans:
        blockers.extend(repo_plan.blockers)
    return {
        "status": "blocked" if blockers else "ready",
        "tech_plan": plan_dict(plan),
        "parent_resolution": parent_dict(parent),
        "session_path": str(session_path) if session_path else None,
        "journal_path": str(journal_path) if journal_path else None,
        "repositories": [
            {
                **repo_plan_dict(repo_plan),
                "github_state": (github_states or {}).get(repo_plan.context.target_repo, {}),
            }
            for repo_plan in repo_plans
        ],
        "blockers": sorted(set(blockers)),
    }


def print_payload(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"status: {payload.get('status')}")
    plan = payload.get("tech_plan", {})
    print(f"tech plan: {plan.get('title')} ({plan.get('path')})")
    parent = payload.get("parent_resolution", {})
    print(f"parent backlog: {parent.get('status')}")
    for repository in payload.get("repositories", []):
        print(f"repository: {repository.get('target_repo')}")
        print(f"  checkout: {repository.get('local_repo_path') or 'unresolved'}")
        print(f"  actions: {', '.join(repository.get('planned_actions', [])) or 'none'}")
        for blocker in repository.get("blockers", []):
            print(f"  blocker: {blocker}")
    for blocker in payload.get("blockers", []):
        print(f"blocker: {blocker}")


def _load_common_inputs(
    args: argparse.Namespace,
    *,
    for_apply: bool,
) -> tuple[Path, TechPlan, Path | None, Path | None, Path | None, Any, Any, list[RepoPlan]]:
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise SetupError(f"workspace root not found: {workspace}")
    plan = parse_tech_plan(args.tech_plan)
    session = session_path(Path(plan.path), args.session_path, for_apply=for_apply)
    backlog_path = Path(args.backlog_plan).expanduser().resolve() if args.backlog_plan else None
    journal_path = session / "code.md" if session else None
    journal = load_journal(journal_path)
    parent = resolve_parent(plan, session, backlog_path)
    contexts = resolve_repositories(
        plan, workspace, journal, args.delivery_mode, args.timeout
    )
    repo_plans = build_repo_plans(plan, contexts, args.delivery_mode, args.kind_label)
    return workspace, plan, session, backlog_path, journal_path, journal, parent, repo_plans


def run_inspect(args: argparse.Namespace) -> int:
    _, plan, session, _, journal_path, _, parent, repo_plans = _load_common_inputs(
        args, for_apply=False
    )
    github_states: dict[str, Any] = {}
    extra_blockers: list[str] = []
    if args.delivery_mode == "github-delivery":
        try:
            github_states, github_blockers = _inspect_github_state(repo_plans, args.timeout)
            extra_blockers.extend(github_blockers)
        except SetupError as exc:
            extra_blockers.append(str(exc))
    payload = _inspect_payload(
        plan=plan,
        parent=parent,
        repo_plans=repo_plans,
        session_path=session,
        journal_path=journal_path,
        github_states=github_states,
        extra_blockers=extra_blockers,
    )
    print_payload(payload, args.output_format)
    return 1 if payload["status"] == "blocked" else 0


def run_apply(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise SetupError("apply is mutating; repeat with --confirm")
    _, plan, session, _, journal_path, _, parent, repo_plans = _load_common_inputs(
        args, for_apply=True
    )
    if session is None:
        raise SetupError("apply requires a session path")
    existing_text = journal_path.read_text(encoding="utf-8") if journal_path and journal_path.is_file() else ""
    if parent.source_errors:
        payload = _inspect_payload(
            plan=plan,
            parent=parent,
            repo_plans=repo_plans,
            session_path=session,
            journal_path=journal_path,
        )
        print_payload(payload, args.output_format)
        return 1
    outcomes: list[RepoOutcome] = []
    if args.delivery_mode == "local-only":
        for repo_plan in repo_plans:
            if repo_plan.blockers:
                outcomes.append(_blocked_outcome(repo_plan, repo_plan.blockers))
            elif (
                repo_plan.context.existing.branch
                and repo_plan.context.existing.branch != repo_plan.context.current_branch
            ):
                outcomes.append(
                    _blocked_outcome(
                        repo_plan,
                        [
                            "local-only re-entry found a different checked-out branch than the journal: "
                            f"{repo_plan.context.existing.branch}"
                        ],
                    )
                )
            else:
                outcomes.append(_outcome_from_local(repo_plan))
    else:
        try:
            require_gh()
        except SetupError as exc:
            outcomes = [_blocked_outcome(repo_plan, [str(exc)]) for repo_plan in repo_plans]
        else:
            for repo_plan in repo_plans:
                outcomes.append(
                    apply_repo(repo_plan, parent, slugify(session.name), args.timeout)
                )

    journal_content = render_journal(
        plan=plan,
        session_slug=session.name,
        session_path=session,
        delivery_mode=args.delivery_mode,
        outcomes=outcomes,
        existing_text=existing_text,
        sdd_state_exists=(session / "sdd-state.yml").is_file(),
    )
    if journal_path is None:
        raise SetupError("apply requires a journal path")
    write_journal(journal_path, journal_content)
    payload = {
        "status": "blocked" if any(outcome.blockers for outcome in outcomes) else "ready",
        "tech_plan": plan_dict(plan),
        "parent_resolution": parent_dict(parent),
        "session_path": str(session),
        "journal_path": str(journal_path),
        "repositories": [asdict(outcome) for outcome in outcomes],
        "journal_written": True,
        "blockers": sorted(
            {blocker for outcome in outcomes for blocker in outcome.blockers}
        ),
    }
    print_payload(payload, args.output_format)
    return 1 if payload["status"] == "blocked" else 0
