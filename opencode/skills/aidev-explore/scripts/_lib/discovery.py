"""Repository discovery: git repos at the workspace root, its children, and repos/ children."""
from __future__ import annotations

import os


def _is_repo(candidate: str) -> bool:
    dot_git = os.path.join(candidate, ".git")
    return os.path.isdir(dot_git) or os.path.isfile(dot_git)


def discover(workspace: str) -> list[str]:
    found: list[str] = []

    if _is_repo(workspace):
        found.append(workspace)

    for child in _sorted_dirs(workspace):
        if _is_repo(child):
            found.append(child)

    repos_dir = os.path.join(workspace, "repos")
    if os.path.isdir(repos_dir):
        for child in _sorted_dirs(repos_dir):
            if _is_repo(child):
                found.append(child)

    return sorted(set(found))


def _sorted_dirs(parent: str) -> list[str]:
    try:
        entries = sorted(os.listdir(parent))
    except OSError:
        return []
    dirs = []
    for name in entries:
        full = os.path.join(parent, name)
        if os.path.isdir(full):
            dirs.append(full)
    return dirs
