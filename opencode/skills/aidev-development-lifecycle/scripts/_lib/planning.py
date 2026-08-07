"""Build per-repository delivery plans and serializable inspect data."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .errors import SetupError
from .models import ParentResolution, RepoContext, RepoPlan, Task, TechPlan
from .tech_plan import issue_body as _build_issue_body
from .text import normalise_repo_name, repo_basename, repo_names


def _repo_matches(left: str, right: str) -> bool:
    return normalise_repo_name(left) == normalise_repo_name(right) or repo_basename(left) == repo_basename(right)


def _scope_summary(tasks: list[Task]) -> str:
    titles = [task.title for task in tasks]
    if len(titles) == 1:
        return titles[0]
    if len(titles) == 2:
        return f"{titles[0]} and {titles[1]}"
    return f"{titles[0]} and {len(titles) - 1} related tasks"


def _kind_label_for(target: str, specifications: list[str]) -> str:
    exact: dict[str, str] = {}
    global_labels: list[str] = []
    for specification in specifications:
        if "=" in specification:
            repo, label = specification.split("=", 1)
            exact[normalise_repo_name(repo)] = label.strip()
        else:
            global_labels.append(specification.strip())
    label = exact.get(normalise_repo_name(target), "")
    if not label:
        label = exact.get(repo_basename(target), "")
    if not label and len(global_labels) == 1:
        label = global_labels[0]
    return label


def _validate_kind_label(label: str) -> str:
    if not label:
        return ""
    if not label.startswith("kind/") or label == "kind/story":
        raise SetupError(
            f"invalid technical issue label {label!r}; provide one kind/* label other than kind/story"
        )
    return label


def issue_body(tasks: list[Task], gates: list[Any]) -> str:
    return _build_issue_body(tasks, gates)


# Kept as a compatibility alias for callers of the original monolithic script.
_issue_body = issue_body


def build_repo_plans(
    plan: TechPlan,
    contexts: list[RepoContext],
    delivery_mode: str,
    kind_label_specs: list[str],
) -> list[RepoPlan]:
    result: list[RepoPlan] = []
    for context in contexts:
        tasks = [
            task
            for task in plan.tasks
            if any(_repo_matches(repo, context.target_repo) for repo in repo_names(task.repo))
        ]
        gates = [gate for gate in plan.gates if _repo_matches(gate.repo, context.target_repo)]
        blockers = list(context.blockers)
        label = ""
        if delivery_mode == "github-delivery":
            try:
                label = _validate_kind_label(
                    _kind_label_for(context.target_repo, kind_label_specs)
                )
            except SetupError as exc:
                blockers.append(str(exc))
            if not label:
                blockers.append(
                    f"no kind/* label mapping supplied for {context.target_repo}; use --kind-label"
                )
        result.append(
            RepoPlan(
                context=context,
                tasks=tasks,
                gates=gates,
                issue_title=f"{plan.title}: {_scope_summary(tasks)}",
                issue_body=issue_body(tasks, gates),
                kind_label=label or "n/a",
                blockers=blockers,
            )
        )
    return result


def parent_dict(parent: ParentResolution) -> dict[str, Any]:
    return {
        "status": parent.status,
        "candidate": asdict(parent.candidate) if parent.candidate else None,
        "candidates": [asdict(candidate) for candidate in parent.candidates],
        "unpublished_items": parent.unpublished_items,
        "source_errors": parent.source_errors,
    }


def plan_dict(plan: TechPlan) -> dict[str, Any]:
    return {
        "path": plan.path,
        "title": plan.title,
        "tasks": [
            {
                "id": task.task_id,
                "title": task.title,
                "repo": task.repo,
                "module": task.module,
                "backlog_item": task.backlog_item,
                "dependencies": task.dependencies,
                "where": task.where,
                "details": task.details,
                "exit_criteria": task.exit_criteria,
                "line_range": [task.start_line, task.end_line],
            }
            for task in plan.tasks
        ],
        "gates": [
            {
                "repo": gate.repo,
                "task_refs": gate.task_refs,
                "technical_checks": gate.checks,
                "line_range": [gate.start_line, gate.end_line],
            }
            for gate in plan.gates
        ],
        "execution_order": [asdict(phase) for phase in plan.execution_order],
        "critical_path": plan.critical_path,
        "parallelizable": plan.parallelizable,
        "backlog_candidates": [asdict(candidate) for candidate in plan.backlog_candidates],
    }


def repo_plan_dict(repo_plan: RepoPlan) -> dict[str, Any]:
    context = repo_plan.context
    planned_actions: list[str] = []
    if context.local_path and not repo_plan.blockers:
        if repo_plan.kind_label == "n/a":
            planned_actions = [
                "verify local checkout",
                "record current branch",
                "refresh Phase 1 journal",
            ]
        else:
            planned_actions = [
                "reconcile technical issue",
                "reconcile parent backlog relationship",
                "reconcile working branch",
                "reconcile draft pull request",
            ]
    return {
        "target_repo": context.target_repo,
        "local_repo_path": context.local_path or None,
        "github_repo": context.github_repo or None,
        "current_branch": context.current_branch or None,
        "working_tree_dirty": context.dirty,
        "tasks": [task.task_id for task in repo_plan.tasks],
        "gates": [gate.repo for gate in repo_plan.gates],
        "issue_title": repo_plan.issue_title,
        "issue_body": repo_plan.issue_body,
        "kind_label": repo_plan.kind_label,
        "existing_artifacts": asdict(context.existing),
        "planned_actions": planned_actions,
        "blockers": repo_plan.blockers,
    }
