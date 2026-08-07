#!/usr/bin/env python3
"""Focused standard-library tests for lifecycle journal checkpoints."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _lib.errors import SetupError
from _lib.journal import apply_journal_checkpoint, load_journal


JOURNAL = """# Implementation Journal — topic

> Tech plan: `tech-plan.md`
> Delivery mode: local-only
> Started: 2026-07-27
> Status: in-progress

## Task Progress

| # | Task | Repo | Status | Phase | Notes |
|---|------|------|--------|-------|-------|
| T1 | Add model | service | pending | 1 | n/a |
| T2 | Add endpoint | service | pending | 1 | n/a |

## Implementation Evidence

| Evidence ID | Task IDs | Linked ACs | Repo | Files / Commands | Result |
|-------------|----------|------------|------|------------------|--------|

## Key Decisions

| Decision | Repo | Rationale | Alternatives |
|----------|------|-----------|-------------|

## Continuation Iterations

| Iteration | Requested Change | Strategy | Evidence Baseline | Phase Dispositions | Validation Scope | Escalation / Blocker |
|-----------|------------------|----------|-------------------|--------------------|------------------|----------------------|

## CI Handoffs

| Exec Phase | Repo | Action | PR Comment | Artifact | Status |
|------------|------|--------|------------|----------|--------|

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1 — Delivery Setup | done | setup verified |
| 2 — Coding | in-progress | implementation started |
| 3 — PaaS Config | pending | waiting for coding |
| 4 — Validation | pending | waiting for implementation |
| 5 — Commit | pending | waiting for validation |
"""


class JournalCheckpointTests(unittest.TestCase):
    def _journal_path(self, directory: str) -> Path:
        path = Path(directory) / "code.md"
        path.write_text(JOURNAL, encoding="utf-8")
        return path

    def test_checkpoint_updates_tasks_phase_and_overall_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._journal_path(directory)

            updated = apply_journal_checkpoint(
                path,
                {
                    "task_updates": [
                        {"task_id": "T1", "status": "done", "notes": "model complete"},
                        {"task_id": "T2", "status": "done", "notes": "endpoint complete"},
                    ],
                    "phase_update": {
                        "phase": "2 — Coding",
                        "status": "done",
                        "notes": "all implementation tasks recorded",
                    },
                    "overall_status": "complete",
                },
            )

            self.assertEqual(updated.task_rows["T1"]["status"], "done")
            self.assertEqual(updated.task_rows["T2"]["notes"], "endpoint complete")
            self.assertEqual(updated.phase_rows["2 — Coding"]["status"], "done")
            self.assertEqual(updated.overall_status, "complete")
            self.assertEqual(load_journal(path).task_rows["T1"]["status"], "done")

    def test_done_coding_phase_rejects_pending_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._journal_path(directory)

            with self.assertRaisesRegex(SetupError, "Task Progress remains open: T2"):
                apply_journal_checkpoint(
                    path,
                    {
                        "task_updates": [
                            {"task_id": "T1", "status": "done", "notes": "model complete"}
                        ],
                        "phase_update": {
                            "phase": "2 — Coding",
                            "status": "done",
                            "notes": "attempted completion",
                        },
                    },
                )

            self.assertEqual(load_journal(path).task_rows["T1"]["status"], "pending")

    def test_follow_up_disposition_requires_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._journal_path(directory)

            with self.assertRaisesRegex(SetupError, "requires notes for status deferred"):
                apply_journal_checkpoint(
                    path,
                    {
                        "task_updates": [{"task_id": "T1", "status": "deferred"}],
                        "phase_update": {
                            "phase": "2 — Coding",
                            "status": "in-progress",
                            "notes": "scope adjusted",
                        },
                    },
                )

    def test_done_commit_phase_requires_overall_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._journal_path(directory)

            with self.assertRaisesRegex(SetupError, "requires an overall status"):
                apply_journal_checkpoint(
                    path,
                    {
                        "task_updates": [
                            {"task_id": "T1", "status": "done", "notes": "model complete"},
                            {"task_id": "T2", "status": "done", "notes": "endpoint complete"},
                        ],
                        "phase_update": {
                            "phase": "5 — Commit",
                            "status": "done",
                            "notes": "commits created",
                        },
                    },
                )


if __name__ == "__main__":
    unittest.main()
