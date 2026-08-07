#!/usr/bin/env python3
"""Focused standard-library tests for the lifecycle setup parser."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "setup.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("lifecycle_setup", SCRIPT)
assert SPEC and SPEC.loader
setup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)

from _lib.repositories import _candidate_repo_paths, session_path
from _lib.github import gh_pr_view


TECH_PLAN = """# Tech Plan: US-001: Task Priority Levels

## Backlog Sources

| Backlog ID | Type | GitHub Issue | Source Spec |
|------------|------|--------------|-------------|
| US-001 | user-story | pending | specs/tasks/task-priority-levels/spec.md |

## Implementation Plan

### Task 1: Add priority data to the API

- **What**: Add priority values to task records.
- **Repo**: wsc-todoapp
- **Module**: api
- **Backlog item**: US-001
- **Where**: src/tasks.py
- **How**: Follow the existing task model pattern.
  ```markdown
  ### Task not-a-task: this is fenced content
    - **Repo**: fake-repository
    - [ ] fake criterion
  ```
- **Depends on**: n/a
- **Exit Criteria** (coder-oriented — "I'm done with this task when I've produced these artifacts"):
  - [ ] Update the model and API tests
  - [ ] Add a migration test

### Task 2: Render priority in the web client

- **What**: Display the priority on task cards.
- **Repo**: spa-todoapp
- **Backlog item**: US-001
- **Where**: src/components/TaskCard.tsx
- **How**: Reuse the existing badge component.
- **Depends on**: Task 1
- **Exit Criteria**:
  - [ ] Add component coverage

## Verification Gates

### Gate: wsc-todoapp (after Tasks 1)

**Technical checks:**
- [ ] Run `python -m pytest tests/unit` → exits 0
- [ ] Run `ruff check .` → exits 0
- [ ] Confirm no regressions in the unit suite
- [ ] Run `npm run dev` → keep the server running
- [ ] Verify the user journey manually in a browser

### Gate: spa-todoapp (after Task 2)

**Technical checks:**
- [ ] Run `npm run test -- --run` → all tests pass
- [ ] Run `npm run typecheck` → exits 0
- [ ] Take a screenshot of the completed card

## Execution Order

| Phase | Tasks | Notes |
|-------|-------|-------|
| 1 | 1 | API work unblocks the client |
| 2 | 2 | Depends on Phase 1 |

**Critical path**: Task 1 → Task 2
**Parallelizable**: none
"""

BACKLOG_PLAN = """schema_version: 2
session: 20260716-priority-levels-for-tasks
source: .aicontext/deliverables/sdd/sessions/20260716-priority-levels-for-tasks
backlog_items:
  - id: US-001
    type: user-story
    title: Add priority levels to tasks
    source_spec: specs/tasks/task-priority-levels/spec.md
    change_kind: new
    publish_decision: pending
    roadmap:
      priority: null
      size: null
      milestone: null
      project_status: candidate
      project_fields: {}
    github:
      issue_url: null
      issue_number: null
      project_number: null
      project_item_id: null
      last_synced_commit: null
      sync_status: not-published
"""


class SetupParserTests(unittest.TestCase):
    def test_repository_discovery_uses_only_repos_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            expected = workspace / "repos" / "todoapp"
            expected.joinpath(".git").mkdir(parents=True)
            fallback = workspace / "runtimes" / "coder" / "repos" / "todoapp"
            fallback.joinpath(".git").mkdir(parents=True)
            sibling = workspace / "todoapp"
            sibling.joinpath(".git").mkdir(parents=True)

            self.assertEqual(_candidate_repo_paths(workspace, "todoapp"), [expected.resolve()])

    def test_explicit_session_is_independent_of_repository_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "runtime"
            workspace.mkdir()
            session = root / "framework" / "sessions" / "topic"
            session.mkdir(parents=True)
            plan_path = session / "tech-plan.md"
            plan_path.write_text(TECH_PLAN, encoding="utf-8")

            resolved = session_path(plan_path, str(session), for_apply=True)

        self.assertEqual(resolved, session.resolve())

    def test_explicit_session_may_resolve_through_workspace_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            physical_session = root / "framework" / "sessions" / "topic"
            physical_session.mkdir(parents=True)
            plan_path = physical_session / "tech-plan.md"
            plan_path.write_text(TECH_PLAN, encoding="utf-8")
            workspace = root / "runtime"
            workspace.mkdir()
            logical_session = workspace / "session"
            logical_session.symlink_to(physical_session, target_is_directory=True)

            resolved = session_path(plan_path, str(logical_session), for_apply=True)

        self.assertEqual(resolved, physical_session.resolve())

    def test_journal_placeholders_are_not_treated_as_artifact_references(self) -> None:
        journal = setup.load_journal_from_text(
            """## Repositories

| Repo | GitHub Repo | Branch | Issue | PR | Status |
|------|-------------|--------|-------|----|--------|
| todoapp | acme/todoapp | n/a | n/a | n/a | partial |
"""
        )

        artifacts = journal.repositories["todoapp"]
        self.assertEqual(artifacts.github_repo, "acme/todoapp")
        self.assertEqual(artifacts.branch, "")
        self.assertEqual(artifacts.issue, "")
        self.assertEqual(artifacts.pr, "")

    def test_setup_reentry_preserves_task_phase_and_overall_progress(self) -> None:
        existing = """# Implementation Journal — topic

> Status: complete-with-follow-ups

## Task Progress

| # | Task | Repo | Status | Phase | Notes |
|---|------|------|--------|-------|-------|
| 1 | Add priority data to the API | wsc-todoapp | done | 1 | implemented |
| 2 | Render priority in the web client | spa-todoapp | deferred | 2 | approved follow-up |

## Implementation Evidence

| Evidence ID | Task IDs | Linked ACs | Repo | Files / Commands | Result |
|-------------|----------|------------|------|------------------|--------|
| EVID-CODE-1 | 1 | AC-1 | wsc-todoapp | task test | passed |

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1 — Delivery Setup | done | prior setup |
| 2 — Coding | done | implementation complete |
| 3 — PaaS Config | done | no changes required |
| 4 — Validation | done | checks passed |
| 5 — Commit | done | commits pushed |
"""
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            plan_path = session / "tech-plan.md"
            plan_path.write_text(TECH_PLAN, encoding="utf-8")
            plan = setup.parse_tech_plan(plan_path)
            outcomes = [
                setup.RepoOutcome(
                    target_repo="wsc-todoapp",
                    github_repo="acme/wsc-todoapp",
                    status="reused",
                    backlog_link_status="n/a",
                ),
                setup.RepoOutcome(
                    target_repo="spa-todoapp",
                    github_repo="acme/spa-todoapp",
                    status="reused",
                    backlog_link_status="n/a",
                ),
            ]
            rendered = setup.render_journal(
                plan=plan,
                session_slug="topic",
                session_path=session,
                delivery_mode="github-delivery",
                outcomes=outcomes,
                existing_text=existing,
            )

        self.assertIn("> Status: complete-with-follow-ups", rendered)
        self.assertIn("| 1 | Add priority data to the API | wsc-todoapp | done |", rendered)
        self.assertIn("| 2 | Render priority in the web client | spa-todoapp | deferred |", rendered)
        self.assertIn("| EVID-CODE-1 | 1 | AC-1 |", rendered)
        self.assertIn("| 2 — Coding | done | implementation complete |", rendered)
        self.assertIn("| 4 — Validation | done | checks passed |", rendered)

    def test_pr_view_is_repository_explicit(self) -> None:
        with patch("_lib.github.json_command", return_value={}) as command:
            gh_pr_view("92", "acme/todoapp", 30)

        args = command.call_args.args[0]
        self.assertIn("-R", args)
        self.assertEqual(args[args.index("-R") + 1], "acme/todoapp")

    def test_plan_parses_tasks_gates_and_fenced_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tech-plan.md"
            path.write_text(TECH_PLAN, encoding="utf-8")
            plan = setup.parse_tech_plan(path)

        self.assertEqual(plan.title, "Task Priority Levels")
        self.assertEqual([task.task_id for task in plan.tasks], ["1", "2"])
        self.assertEqual([task.repo for task in plan.tasks], ["wsc-todoapp", "spa-todoapp"])
        self.assertEqual(plan.tasks[0].module, "api")
        self.assertEqual(plan.tasks[1].dependencies, ["1"])
        self.assertEqual(
            plan.tasks[0].exit_criteria,
            ["Update the model and API tests", "Add a migration test"],
        )
        self.assertEqual(len(plan.gates), 2)
        self.assertEqual(
            plan.gates[0].checks,
            [
                "- [ ] Run `python -m pytest tests/unit` → exits 0",
                "- [ ] Run `ruff check .` → exits 0",
                "- [ ] Confirm no regressions in the unit suite",
            ],
        )
        self.assertEqual(plan.execution_order[0].task_refs, ["1"])
        self.assertIn("### Task not-a-task", plan.tasks[0].markdown)

    def test_cross_repository_task_maps_to_each_repository(self) -> None:
        cross_repo_plan = TECH_PLAN.replace(
            "- **Repo**: spa-todoapp",
            "- **Repo**: `wsc-todoapp` and `spa-todoapp`",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tech-plan.md"
            path.write_text(cross_repo_plan, encoding="utf-8")
            plan = setup.parse_tech_plan(path)
            journal = setup.JournalData()
            contexts = setup.resolve_repositories(
                plan,
                Path(directory),
                journal,
                "local-only",
            )

        self.assertEqual(plan.tasks[1].repo, "wsc-todoapp, spa-todoapp")
        self.assertEqual(
            [context.target_repo for context in contexts],
            ["wsc-todoapp", "spa-todoapp"],
        )

    def test_backlog_plan_pending_item_is_not_a_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            plan_path = session / "tech-plan.md"
            backlog_path = session / "backlog-plan.yml"
            plan_path.write_text(TECH_PLAN, encoding="utf-8")
            backlog_path.write_text(BACKLOG_PLAN, encoding="utf-8")
            plan = setup.parse_tech_plan(plan_path)
            parent = setup.resolve_parent(plan, session, None)

        self.assertEqual(parent.status, "not-applicable")
        self.assertEqual(parent.unpublished_items, ["US-001"])
        self.assertEqual(parent.candidates, [])

    def test_approved_synced_backlog_item_resolves(self) -> None:
        approved = BACKLOG_PLAN.replace(
            "publish_decision: pending", "publish_decision: approved"
        ).replace(
            "issue_url: null", "issue_url: https://github.com/acme/tasks/issues/42"
        ).replace(
            "issue_number: null", "issue_number: 42"
        ).replace(
            "sync_status: not-published", "sync_status: synced"
        )
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            plan_path = session / "tech-plan.md"
            backlog_path = session / "backlog-plan.yml"
            plan_path.write_text(TECH_PLAN, encoding="utf-8")
            backlog_path.write_text(approved, encoding="utf-8")
            parent = setup.resolve_parent(setup.parse_tech_plan(plan_path), session, None)

        self.assertEqual(parent.status, "resolved")
        assert parent.candidate
        self.assertEqual(parent.candidate.backlog_id, "US-001")
        self.assertEqual(parent.candidate.repo, "acme/tasks")
        self.assertEqual(parent.candidate.issue_number, 42)

    def test_issue_body_contains_only_technical_gate_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tech-plan.md"
            path.write_text(TECH_PLAN, encoding="utf-8")
            plan = setup.parse_tech_plan(path)
        body = setup._issue_body([plan.tasks[0]], [plan.gates[0]])

        self.assertIn("## Definition of Done", body)
        self.assertIn("ruff check", body)
        self.assertNotIn("npm run dev", body)
        self.assertNotIn("user journey", body)
        self.assertNotIn("screenshot", body)

    def test_duplicate_task_ids_are_rejected(self) -> None:
        duplicate = TECH_PLAN.replace(
            "### Task 2: Render priority in the web client",
            "### Task 1: Render priority in the web client",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tech-plan.md"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaises(setup.SetupError):
                setup.parse_tech_plan(path)


if __name__ == "__main__":
    unittest.main()
