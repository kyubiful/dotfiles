"""GitHub, branch, and draft-PR reconciliation."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from .commands import json_command, run_command, write_temp_text
from .errors import CommandError, SetupError
from .models import BacklogCandidate, ParentResolution, RepoContext, RepoPlan
from .repositories import git_branch
from .text import issue_ref, parse_issue_url


def require_gh() -> None:
    if shutil.which("gh") is None:
        raise SetupError("gh CLI is not installed or not available on PATH")


def gh_issue_view(repo: str, reference: str | int, timeout: float) -> dict[str, Any]:
    return json_command(
        [
            "gh",
            "issue",
            "view",
            str(reference),
            "-R",
            repo,
            "--json",
            "state,body,labels,url,number,title",
        ],
        timeout=timeout,
    )


def gh_issue_list_exact(repo: str, title: str, timeout: float) -> list[dict[str, Any]]:
    output = json_command(
        [
            "gh",
            "issue",
            "list",
            "-R",
            repo,
            "--state",
            "open",
            "--limit",
            "50",
            "--search",
            f'"{title}" in:title',
            "--json",
            "number,title,url,labels,state",
        ],
        timeout=timeout,
    )
    return [item for item in output if item.get("title") == title]


def label_names(issue: dict[str, Any]) -> list[str]:
    return [
        str(label.get("name", ""))
        for label in issue.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    ]


def is_backlog_projection(issue: dict[str, Any]) -> bool:
    labels = {label.casefold() for label in label_names(issue)}
    title = str(issue.get("title", "")).casefold()
    return "kind/story" in labels or title.startswith("user story:")


def issue_number_from_url(url: str) -> int:
    parsed = parse_issue_url(url)
    if not parsed:
        raise SetupError(f"GitHub issue URL is invalid: {url}")
    return parsed[1]


def reconcile_issue(
    repo_plan: RepoPlan, *, timeout: float
) -> tuple[dict[str, Any], str, str, str]:
    context = repo_plan.context
    existing_reference = context.existing.issue
    issue: dict[str, Any] | None = None
    issue_status = ""
    label_note = "none"
    if existing_reference:
        parsed_existing = issue_ref(existing_reference)
        if parsed_existing is None:
            raise SetupError(
                f"journal issue reference is invalid for {context.target_repo}: {existing_reference}"
            )
        existing_repo, number = parsed_existing
        if existing_repo and existing_repo != context.github_repo:
            raise SetupError(
                f"journal issue {existing_reference} belongs to {existing_repo}, expected {context.github_repo}"
            )
        issue = gh_issue_view(context.github_repo, number, timeout)
        if str(issue.get("state", "")).casefold() == "closed":
            raise SetupError(f"journal technical issue is closed: {issue.get('url', existing_reference)}")
        if is_backlog_projection(issue):
            issue = None
        else:
            issue_status = "reused"

    if issue is None and not existing_reference:
        matches = gh_issue_list_exact(context.github_repo, repo_plan.issue_title, timeout)
        technical_matches = [item for item in matches if not is_backlog_projection(item)]
        if len(technical_matches) > 1:
            raise SetupError(
                f"multiple open technical issues have the desired title in {context.github_repo}: "
                + ", ".join(str(item.get("url")) for item in technical_matches)
            )
        if technical_matches:
            issue = gh_issue_view(context.github_repo, technical_matches[0]["number"], timeout)
            issue_status = "reused"

    if issue is None:
        if repo_plan.kind_label == "n/a":
            raise SetupError(f"no technical kind label is available for {context.target_repo}")
        body_file = write_temp_text(repo_plan.issue_body)
        try:
            output = run_command(
                [
                    "gh",
                    "issue",
                    "create",
                    "-R",
                    context.github_repo,
                    "--title",
                    repo_plan.issue_title,
                    "--body-file",
                    body_file,
                    "--label",
                    repo_plan.kind_label,
                ],
                timeout=timeout,
            )
        finally:
            try:
                os.unlink(body_file)
            except OSError:
                pass
        url_match = re.search(r"https://github\.com/[^\s]+/issues/\d+", output)
        if not url_match:
            raise SetupError(f"gh issue create did not return an issue URL: {output}")
        issue = gh_issue_view(context.github_repo, url_match.group(0), timeout)
        issue_status = "created"

    current_body = str(issue.get("body") or "")
    if current_body.rstrip() != repo_plan.issue_body.rstrip():
        body_file = write_temp_text(repo_plan.issue_body)
        try:
            run_command(
                [
                    "gh",
                    "issue",
                    "edit",
                    str(issue["number"]),
                    "-R",
                    context.github_repo,
                    "--body-file",
                    body_file,
                ],
                timeout=timeout,
            )
        finally:
            try:
                os.unlink(body_file)
            except OSError:
                pass
        issue_status = "updated" if issue_status == "reused" else issue_status

    labels = label_names(issue)
    technical_labels = [
        label for label in labels if label.startswith("kind/") and label != "kind/story"
    ]
    if technical_labels:
        if repo_plan.kind_label != "n/a" and technical_labels[0] != repo_plan.kind_label:
            label_note = f"preserved existing label {technical_labels[0]}"
    elif repo_plan.kind_label != "n/a":
        run_command(
            [
                "gh",
                "issue",
                "edit",
                str(issue["number"]),
                "-R",
                context.github_repo,
                "--add-label",
                repo_plan.kind_label,
            ],
            timeout=timeout,
        )
        issue_status = "updated" if issue_status == "reused" else issue_status

    verified = gh_issue_view(context.github_repo, issue["number"], timeout)
    if str(verified.get("state", "")).casefold() != "open":
        raise SetupError(f"technical issue is not open after reconciliation: {verified.get('url')}")
    if str(verified.get("body") or "").rstrip() != repo_plan.issue_body.rstrip():
        raise SetupError(f"technical issue body verification failed: {verified.get('url')}")
    verified_labels = label_names(verified)
    if repo_plan.kind_label != "n/a" and not any(
        label == repo_plan.kind_label or label.startswith("kind/") for label in verified_labels
    ):
        raise SetupError(f"technical issue label verification failed: {verified.get('url')}")
    return verified, str(issue_status or "reused"), label_note, str(verified["url"])


def gh_issue_parent(repo: str, number: int, timeout: float) -> dict[str, Any] | None:
    try:
        data = json_command(
            [
                "gh",
                "issue",
                "view",
                str(number),
                "-R",
                repo,
                "--json",
                "parent,url",
            ],
            timeout=timeout,
        )
    except CommandError:
        return None
    parent = data.get("parent")
    return parent if isinstance(parent, dict) else None


def _managed_comment_body(
    existing: str, marker: str, target_repo: str, issue_url: str
) -> str:
    line = f"Technical implementation issue for {target_repo}: {issue_url}"
    if marker not in existing:
        return f"{marker}\n\n{line}\n"
    lines = existing.splitlines()
    output: list[str] = []
    replaced = False
    for current in lines:
        if re.match(rf"^Technical implementation issue for {re.escape(target_repo)}:\s*", current):
            if not replaced:
                output.append(line)
                replaced = True
            continue
        output.append(current)
    if not replaced:
        output.append(line)
    return "\n".join(output).rstrip() + "\n"


def _fallback_parent_reference(
    parent: BacklogCandidate,
    target_repo: str,
    technical_issue_url: str,
    session_slug: str,
    timeout: float,
) -> None:
    marker = f"<!-- aidev-technical-issues:{session_slug} -->"
    comments = json_command(
        [
            "gh",
            "api",
            f"repos/{parent.repo}/issues/{parent.issue_number}/comments",
        ],
        timeout=timeout,
    )
    managed = next(
        (
            comment
            for comment in comments
            if isinstance(comment, dict) and marker in str(comment.get("body", ""))
        ),
        None,
    )
    current = str(managed.get("body", "")) if managed else ""
    body = _managed_comment_body(current, marker, target_repo, technical_issue_url)
    if managed:
        run_command(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{parent.repo}/issues/comments/{managed['id']}",
                "-f",
                f"body={body}",
            ],
            timeout=timeout,
        )
    else:
        run_command(
            [
                "gh",
                "issue",
                "comment",
                str(parent.issue_number),
                "-R",
                parent.repo,
                "--body",
                body,
            ],
            timeout=timeout,
        )
    verified_comments = json_command(
        [
            "gh",
            "api",
            f"repos/{parent.repo}/issues/{parent.issue_number}/comments",
        ],
        timeout=timeout,
    )
    if not any(
        isinstance(comment, dict)
        and marker in str(comment.get("body", ""))
        and technical_issue_url in str(comment.get("body", ""))
        for comment in verified_comments
    ):
        raise SetupError("fallback parent reference verification failed")


def reconcile_parent_link(
    issue: dict[str, Any],
    context: RepoContext,
    parent: ParentResolution,
    session_slug: str,
    timeout: float,
) -> tuple[str, str, str, str, str]:
    if parent.status == "not-applicable":
        return "n/a", "n/a", "n/a", "none", "n/a"
    if parent.status == "blocked":
        return "n/a", "blocked", "n/a", "; ".join(parent.source_errors), "n/a"
    if parent.status == "ambiguous":
        candidates = ", ".join(candidate.issue_url for candidate in parent.candidates)
        return "n/a", "blocked", "n/a", f"multiple parent backlog issues: {candidates}", "n/a"
    if parent.candidate is None:
        return "n/a", "blocked", "n/a", "parent resolution has no candidate", "n/a"

    candidate = parent.candidate
    parent_display = f"{candidate.repo}#{candidate.issue_number}"
    technical_url = str(issue["url"])
    existing_parent = gh_issue_parent(context.github_repo, int(issue["number"]), timeout)
    if existing_parent:
        existing_url = str(existing_parent.get("url", ""))
        if existing_url == candidate.issue_url:
            return "sub-issue", "already-linked", parent_display, "none", candidate.backlog_id
        return (
            "sub-issue",
            "blocked",
            parent_display,
            f"technical issue already has a different parent: {existing_url}",
            candidate.backlog_id,
        )

    try:
        run_command(
            [
                "gh",
                "issue",
                "edit",
                str(candidate.issue_number),
                "-R",
                candidate.repo,
                "--add-sub-issue",
                technical_url,
            ],
            timeout=timeout,
        )
        verified_parent = gh_issue_parent(context.github_repo, int(issue["number"]), timeout)
        if verified_parent and str(verified_parent.get("url", "")) == candidate.issue_url:
            return "sub-issue", "linked", parent_display, "none", candidate.backlog_id
    except CommandError:
        pass

    _fallback_parent_reference(
        candidate, context.target_repo, technical_url, session_slug, timeout
    )
    return (
        "fallback-reference",
        "fallback-reference",
        parent_display,
        "native sub-issue linking unavailable; managed non-closing reference created",
        candidate.backlog_id,
    )


def branch_exists(path: Path, branch: str, timeout: float) -> bool:
    local = run_command(
        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
        cwd=path,
        timeout=timeout,
        check=False,
    )
    if local:
        return True
    remote = run_command(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=path,
        timeout=timeout,
        check=False,
    )
    return bool(remote) and "fatal:" not in remote.casefold()


def checkout_branch(path: Path, branch: str, timeout: float) -> None:
    if not re.match(r"^[A-Za-z0-9._/-]+$", branch) or ".." in branch:
        raise SetupError(f"unsafe branch name from journal: {branch}")
    current = git_branch(path, timeout)
    if current == branch:
        return
    local_exists = bool(
        run_command(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            cwd=path,
            timeout=timeout,
            check=False,
        )
    )
    if local_exists:
        run_command(["git", "switch", branch], cwd=path, timeout=timeout)
        return
    remote_output = run_command(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=path,
        timeout=timeout,
        check=False,
    )
    remote_exists = bool(remote_output) and "fatal:" not in remote_output.casefold()
    if remote_exists:
        run_command(
            ["git", "switch", "--track", "-c", branch, f"origin/{branch}"],
            cwd=path,
            timeout=timeout,
        )
        return
    raise SetupError(f"branch does not exist locally or on origin: {branch}")


def gh_pr_view(reference: str, repo: str, timeout: float) -> dict[str, Any]:
    return json_command(
        [
            "gh",
            "pr",
            "view",
            reference,
            "-R",
            repo,
            "--json",
            "state,isDraft,body,url,number,headRefName",
        ],
        timeout=timeout,
    )


def current_pr(path: Path, branch: str, timeout: float) -> dict[str, Any] | None:
    try:
        data = json_command(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "open",
                "--limit",
                "10",
                "--json",
                "state,isDraft,body,url,number,headRefName",
            ],
            cwd=path,
            timeout=timeout,
        )
    except CommandError:
        return None
    return data[0] if data else None


def ensure_sherpa(timeout: float) -> None:
    installed = run_command(["gh", "extension", "list"], timeout=timeout, check=False)
    if "sherpa" in installed.casefold():
        return
    run_command(
        ["gh", "extension", "install", "InditexTech/gh-sherpa"], timeout=timeout
    )


def closing_reference(body: str, repo: str, number: int) -> bool:
    qualified = re.escape(f"{repo}#{number}")
    unqualified = re.escape(f"#{number}")
    return bool(
        re.search(
            rf"\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:{qualified}|{unqualified})\b",
            body,
            re.IGNORECASE,
        )
    )


def ensure_pr_closing_link(
    pr: dict[str, Any], context: RepoContext, issue_number: int, timeout: float
) -> dict[str, Any]:
    body = str(pr.get("body") or "")
    if closing_reference(body, context.github_repo, issue_number):
        return pr
    weak = re.compile(rf"(?im)^\s*related to\s+#{issue_number}\s*$")
    if weak.search(body):
        body = weak.sub(f"Closes #{issue_number}", body)
    else:
        body = body.rstrip() + f"\n\nCloses #{issue_number}\n"
    body_file = write_temp_text(body)
    try:
        run_command(
            [
                "gh",
                "pr",
                "edit",
                str(pr["number"]),
                "-R",
                context.github_repo,
                "--body-file",
                body_file,
            ],
            timeout=timeout,
        )
    finally:
        try:
            os.unlink(body_file)
        except OSError:
            pass
    verified = gh_pr_view(str(pr["number"]), context.github_repo, timeout)
    if not closing_reference(
        str(verified.get("body") or ""), context.github_repo, issue_number
    ):
        raise SetupError(f"PR closing-link verification failed: {verified.get('url')}")
    return verified


def reconcile_branch_and_pr(
    repo_plan: RepoPlan, issue_number: int, *, timeout: float
) -> tuple[str, str, str, str]:
    context = repo_plan.context
    path = Path(context.local_path)
    existing_branch = context.existing.branch
    existing_pr = context.existing.pr
    branch_status = "reused"
    pr_status = "reused"
    pr: dict[str, Any] | None = None

    if existing_pr:
        pr = gh_pr_view(existing_pr, context.github_repo, timeout)
        if str(pr.get("state", "")).casefold() != "open":
            pr = None
        elif not bool(pr.get("isDraft", False)):
            raise SetupError(
                f"existing PR is ready for review and cannot be changed: {pr.get('url')}"
            )
        if pr and not existing_branch:
            existing_branch = str(pr.get("headRefName") or "")

    if existing_branch:
        if not branch_exists(path, existing_branch, timeout):
            if pr is not None:
                raise SetupError(
                    f"existing PR points to a branch that cannot be verified: {existing_branch}"
                )
            existing_branch = ""
        else:
            checkout_branch(path, existing_branch, timeout)

    candidate_branch = existing_branch or context.current_branch
    if pr is None and candidate_branch:
        candidate_pr = current_pr(path, candidate_branch, timeout)
        if candidate_pr is not None:
            if not bool(candidate_pr.get("isDraft", False)):
                raise SetupError(
                    f"existing PR is ready for review and cannot be changed: {candidate_pr.get('url')}"
                )
            pr = candidate_pr
            existing_branch = candidate_branch
            branch_status = "reused"
            pr_status = "reused"

    if pr is None:
        ensure_sherpa(timeout)
        if existing_branch:
            run_command(["gh", "sherpa", "create-pr", "--yes"], cwd=path, timeout=timeout)
            branch_status = "reused"
        else:
            run_command(
                ["gh", "sherpa", "create-pr", "--issue", str(issue_number), "--yes"],
                cwd=path,
                timeout=timeout,
            )
            branch_status = "created"
        branch = git_branch(path, timeout)
        if not branch:
            raise SetupError(f"gh sherpa did not leave a working branch checked out in {path}")
        pr = current_pr(path, branch, timeout)
        if pr is None:
            raise SetupError(f"no open pull request found for branch {branch} after gh sherpa")
        pr_status = "created"
    else:
        branch = git_branch(path, timeout)
        if existing_branch and branch != existing_branch:
            checkout_branch(path, existing_branch, timeout)
            branch = existing_branch

    if pr is None:
        raise SetupError("pull request reconciliation produced no pull request")
    if not bool(pr.get("isDraft", False)):
        raise SetupError(f"pull request is not draft: {pr.get('url')}")
    pr = ensure_pr_closing_link(pr, context, issue_number, timeout)
    return branch, str(pr["url"]), branch_status, pr_status
