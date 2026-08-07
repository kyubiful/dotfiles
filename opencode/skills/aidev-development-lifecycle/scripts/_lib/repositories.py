"""Workspace-bounded repository and session-path resolution."""
from __future__ import annotations

from pathlib import Path

from .commands import DEFAULT_TIMEOUT, run_command
from .errors import SetupError
from .models import JournalData, ExistingArtifacts, RepoContext, TechPlan
from .text import repo_names, under


def _is_git_checkout(path: Path) -> bool:
    return (path / ".git").is_dir() or (path / ".git").is_file()


def git_remote_repo(path: Path, timeout: float) -> str:
    output = run_command(
        ["git", "remote", "get-url", "origin"], cwd=path, timeout=timeout
    ).strip()
    value = output.removesuffix(".git").rstrip("/")
    if value.startswith("git@") and ":" in value:
        value = value.split(":", 1)[1]
    elif "/" in value:
        value = value.split("://", 1)[-1]
        value = value.split("/", 1)[-1] if "/" in value else value
    parts = value.split("/")
    if len(parts) < 2:
        raise SetupError(f"cannot derive owner/repo from origin remote in {path}: {output}")
    return "/".join(parts[-2:])


def git_branch(path: Path, timeout: float) -> str:
    return run_command(["git", "branch", "--show-current"], cwd=path, timeout=timeout).strip()


def git_dirty(path: Path, timeout: float) -> bool:
    return bool(run_command(["git", "status", "--porcelain"], cwd=path, timeout=timeout))


def _candidate_repo_paths(workspace: Path, target: str) -> list[Path]:
    """Return only the prescribed checkout: ``<workspace>/repos/<target>``."""
    repos_root = (workspace / "repos").resolve()
    target_path = Path(target)
    if target_path.is_absolute():
        return []
    path = (repos_root / target_path).resolve()
    if not under(path, repos_root):
        return []
    if path.is_dir() and _is_git_checkout(path):
        return [path]
    return []


def resolve_repositories(
    plan: TechPlan,
    workspace: Path,
    journal: JournalData,
    delivery_mode: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[RepoContext]:
    targets: list[str] = []
    for task in plan.tasks:
        for target in repo_names(task.repo):
            if target not in targets:
                targets.append(target)
    contexts: list[RepoContext] = []
    for target in targets:
        existing = journal.repositories.get(target, ExistingArtifacts())
        context = RepoContext(target_repo=target, existing=existing)
        candidates = _candidate_repo_paths(workspace, target)
        expected_remote = target if "/" in target else ""
        if expected_remote:
            matching: list[Path] = []
            for candidate in candidates:
                try:
                    if git_remote_repo(candidate, timeout) == expected_remote:
                        matching.append(candidate)
                except SetupError:
                    continue
            if matching:
                candidates = matching
        if len(candidates) == 0:
            context.blockers.append(
                f"no git checkout for {target} found at {workspace / 'repos' / target}"
            )
            contexts.append(context)
            continue
        if len(candidates) > 1:
            context.blockers.append(
                "ambiguous git checkout for "
                f"{target}: {', '.join(str(candidate) for candidate in candidates)}"
            )
            contexts.append(context)
            continue

        path = candidates[0].resolve()
        if not under(path, workspace):
            context.blockers.append(f"repository path is outside workspace: {path}")
            contexts.append(context)
            continue
        context.local_path = str(path)
        try:
            context.current_branch = git_branch(path, timeout)
            context.dirty = git_dirty(path, timeout)
        except SetupError as exc:
            context.blockers.append(str(exc))
            contexts.append(context)
            continue
        if not context.current_branch:
            context.blockers.append(f"repository is in detached HEAD state: {path}")
        try:
            context.github_repo = git_remote_repo(path, timeout)
        except SetupError as exc:
            if delivery_mode == "github-delivery":
                context.blockers.append(str(exc))
        if expected_remote and context.github_repo and context.github_repo != expected_remote:
            context.blockers.append(
                f"origin for {target} is {context.github_repo}, expected {expected_remote}"
            )
        contexts.append(context)
    return contexts


def session_path(plan_path: Path, explicit: str | None, *, for_apply: bool) -> Path | None:
    """Resolve the explicitly trusted framework session independently of repos.

    ``workspace`` is the trust root for application checkouts only. Framework
    sessions may be mounted or symlinked elsewhere by the host runtime, so an
    explicit ``--session-path`` is its own trust anchor.
    """
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if for_apply and not path.is_dir():
            raise SetupError(f"session path does not exist: {path}")
        return path
    parent = plan_path.parent
    if (parent / "backlog-plan.yml").is_file() or parent.name.startswith("20"):
        return parent
    if for_apply:
        raise SetupError(
            "apply requires --session-path unless the tech plan is inside a session directory"
        )
    return None


def journal_display_path(plan_path: Path, session_path: Path | None) -> str:
    if session_path is not None:
        try:
            relative = plan_path.relative_to(session_path)
            return str(relative)
        except ValueError:
            pass
    return plan_path.name
