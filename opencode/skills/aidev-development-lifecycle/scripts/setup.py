#!/usr/bin/env python3
"""Thin executable for deterministic Phase 1 lifecycle setup.

Implementation lives in the sibling ``_lib`` package.  The selected imports
below preserve the parser-oriented compatibility surface used by existing
callers while keeping command-line orchestration out of this file.
"""
from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _lib.backlog import resolve_parent  # noqa: E402
from _lib.cli import build_parser, main  # noqa: E402
from _lib.commands import DEFAULT_TIMEOUT, json_command, run_command  # noqa: E402
from _lib.errors import CommandError, SetupError  # noqa: E402
from _lib.journal import (  # noqa: E402
    load_journal,
    load_journal_from_text,
    render_journal,
    write_journal,
)
from _lib.models import (  # noqa: E402
    BacklogCandidate,
    ExecutionPhase,
    ExistingArtifacts,
    Gate,
    JournalData,
    ParentResolution,
    RepoContext,
    RepoOutcome,
    RepoPlan,
    Task,
    TechPlan,
)
from _lib.orchestration import apply_repo, run_apply, run_inspect  # noqa: E402
from _lib.planning import _issue_body, build_repo_plans  # noqa: E402
from _lib.repositories import resolve_repositories  # noqa: E402
from _lib.tech_plan import parse_tech_plan  # noqa: E402


__all__ = [
    "BacklogCandidate",
    "CommandError",
    "DEFAULT_TIMEOUT",
    "ExecutionPhase",
    "ExistingArtifacts",
    "Gate",
    "JournalData",
    "ParentResolution",
    "RepoContext",
    "RepoOutcome",
    "RepoPlan",
    "SetupError",
    "Task",
    "TechPlan",
    "apply_repo",
    "build_parser",
    "build_repo_plans",
    "json_command",
    "load_journal",
    "load_journal_from_text",
    "main",
    "parse_tech_plan",
    "render_journal",
    "resolve_parent",
    "resolve_repositories",
    "run_apply",
    "run_command",
    "run_inspect",
    "write_journal",
]


if __name__ == "__main__":
    raise SystemExit(main())
