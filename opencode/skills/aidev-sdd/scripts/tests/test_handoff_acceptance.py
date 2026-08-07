from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _lib import commands, handoffs, linters, state, transaction, yamlscan  # noqa: E402
from _lib.cli import LintFailure, ToolError  # noqa: E402


class HandoffAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.sessions = self.workspace / ".aicontext" / "deliverables" / "sdd" / "sessions"
        self.sessions.mkdir(parents=True)
        self.session = self.sessions / f"{datetime.now().strftime('%Y%m%d')}-handoff-test"
        self._call(commands.cmd_init, [str(self.sessions), "handoff-test", "--name", "Handoff test"])
        self._call(
            commands.cmd_set_track,
            [str(self.session), "exhaustive", "--rationale", "exercise every delegated phase"],
        )
        self.assertTrue((self.session / "handoffs").is_dir())

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, function, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(args)

    def _write(self, relative, content):
        target = self.workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def _manifest(
        self,
        phase,
        artifacts,
        specs=None,
        status="ready",
        blocker_refs=None,
        **extra,
    ):
        path = self.session / "handoffs" / f"{phase}-handoff.yml"
        payload = {
            "schema_version": 1,
            "phase": phase,
            "status": status,
            "artifacts": artifacts,
        }
        if specs is not None:
            payload["specs"] = specs
        if blocker_refs is not None:
            payload["blocker_refs"] = blocker_refs
        payload.update(extra)
        path.write_text(yaml.safe_dump(payload, sort_keys=False))
        return path

    def _start(self, phase):
        self._call(commands.cmd_phase_start, [str(self.session), phase])

    def _accept(self, manifest, gate="pass"):
        self._call(
            commands.cmd_accept_handoff,
            [str(self.session), "--file", str(manifest), "--gate", gate],
        )

    def _advance_orchestrator_phase(self, phase):
        self._call(commands.cmd_gate_check, [str(self.session), "--phase", phase])
        self._call(commands.cmd_gate, [str(self.session), phase, "pass", "--evidence", "validated"])
        self._call(commands.cmd_phase_complete, [str(self.session), phase])
        self._call(commands.cmd_advance, [str(self.session)])

    def test_exhaustive_track_accepts_every_delegated_phase(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example

## Problem Context
Example context.

## Research Conclusions
Proceed.

## Sources
Internal source.

## Source Confirmation Log
Confirmed.
""",
        )
        self._accept(
            self._manifest(
                "discovery",
                {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
            )
        )

        self._start("functional-spec")
        self._write(self.session.relative_to(self.workspace) / "plan.md", "# Plan: Example\n")
        self._write(
            self.session.relative_to(self.workspace) / "specs/example/example/spec.md",
            _spec("Session specification"),
        )
        self._write(
            self.session.relative_to(self.workspace) / "backlog-plan.yml",
            _backlog(self.session.name),
        )
        self._accept(
            self._manifest(
                "functional-spec",
                {
                    "plan": {"kind": "plan", "scope": "session", "path": "plan.md"},
                    "backlog": {
                        "kind": "backlog",
                        "scope": "session",
                        "path": "backlog-plan.yml",
                    },
                    "primary-spec": {
                        "kind": "spec",
                        "scope": "session",
                        "path": "specs/example/example/spec.md",
                    },
                },
                specs=[{"artifact": "primary-spec", "relation": "primary"}],
            )
        )

        self._advance_orchestrator_phase("spec-validation")

        self._start("technical-plan")
        self._write(
            self.session.relative_to(self.workspace) / "tech-plan.md",
            _tech_plan(),
        )
        self._accept(
            self._manifest(
                "technical-plan",
                {
                    "technical-plan": {
                        "kind": "technical-plan",
                        "scope": "session",
                        "path": "tech-plan.md",
                    }
                },
            )
        )

        self._start("test-design")
        self._write(
            self.session.relative_to(self.workspace) / "test-plan.md",
            _test_plan(),
        )
        self._accept(
            self._manifest(
                "test-design",
                {
                    "test-plan": {
                        "kind": "test-plan",
                        "scope": "session",
                        "path": "test-plan.md",
                    }
                },
            )
        )

        self._start("implementation")
        self._write(self.session.relative_to(self.workspace) / "code.md", _code_journal())
        self._accept(
            self._manifest(
                "implementation",
                {
                    "code": {
                        "kind": "code-journal",
                        "scope": "session",
                        "path": "code.md",
                    }
                },
            )
        )

        self._start("spec-verification")
        self._write(
            self.session.relative_to(self.workspace) / "verification.md",
            _verification(),
        )
        eng = state.StateEngine()
        eng.begin(str(self.session))
        eng.set_nested_scalar("orchestration", "remediation_loop", "iterations", "2")
        eng.set_nested_scalar(
            "orchestration", "remediation_loop", "last_target", "implementation"
        )
        eng.commit()
        self._accept(
            self._manifest(
                "spec-verification",
                {
                    "verification": {
                        "kind": "verification",
                        "scope": "session",
                        "path": "verification.md",
                    }
                },
            )
        )
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual(
            "0",
            yamlscan.trim_scalar(
                yamlscan.nested_value(
                    "orchestration", "remediation_loop", "iterations", records
                )
            ),
        )

        self._start("retro")
        self._write(self.session.relative_to(self.workspace) / "retro.md", _retro())
        canonical = ".aicontext/deliverables/sdd/specs/example/example/spec.md"
        self._write(canonical, _spec("Canonical specification"))
        deleted = ".aicontext/deliverables/sdd/specs/example/obsolete/spec.md"
        deleted_package = ".aicontext/deliverables/sdd/specs/example/obsolete"
        self._write(deleted, _spec("Obsolete specification"))
        self._write(
            ".aicontext/deliverables/sdd/specs/example/obsolete/changes/changes.json",
            '{"schema_version": 2, "changes": []}\n',
        )
        self._call(
            commands.cmd_spec_add,
            [str(self.session), deleted, "--scope", "workspace", "--relation", "reference"],
        )
        shutil.rmtree(self.workspace / deleted_package)
        retro_manifest = self._manifest(
                "retro",
                {
                    "retro": {"kind": "retro", "scope": "session", "path": "retro.md"},
                    "canonical-spec": {"kind": "spec", "scope": "workspace", "path": canonical},
                },
                specs=[
                    {
                        "artifact": "canonical-spec",
                        "relation": "primary",
                        "replaces": {
                            "scope": "session",
                            "path": "specs/example/example/spec.md",
                        },
                    }
                ],
                spec_deletions=[
                    {
                        "registered": {"scope": "workspace", "path": deleted},
                        "package": deleted_package,
                    }
                ],
            )
        self._accept(retro_manifest)
        accepted_state = (self.session / "sdd-state.yml").read_bytes()
        accepted_trace = (self.session / "trace.md").read_bytes()
        with self.assertRaises(ToolError):
            self._accept(retro_manifest)
        self.assertEqual(accepted_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(accepted_trace, (self.session / "trace.md").read_bytes())

        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual("retro", _top(records, "current_phase"))
        self.assertEqual("complete", yamlscan.trim_scalar(yamlscan.nested_value("phases", "retro", "status", records)))
        specs = yamlscan.parse_state_specs(records)
        self.assertEqual([(f'"{canonical}"', "workspace", "primary")], specs)
        self.assertFalse((self.workspace / deleted_package).exists())
        linters.lint_session_state(str(self.session / "sdd-state.yml"))
        linters.lint_trace_gate(str(self.session / "trace.md"), "retro")

    def test_failed_acceptance_leaves_state_and_trace_unchanged(self):
        self._start("discovery")
        research = self._write(
            self.session.relative_to(self.workspace) / "research.md",
            "# Research: Invalid\n",
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
        )
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()
        with self.assertRaises(ToolError):
            self._accept(manifest)
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())
        self.assertTrue(research.exists())

    def test_failed_validation_can_retry_and_accept_a_corrected_handoff(self):
        self._start("discovery")
        self._call(
            commands.cmd_create_handoff,
            [
                str(self.session),
                "--expect-phase",
                "discovery",
                "--need",
                "Research the approved scope.",
            ],
        )
        request = self.session / "handoffs" / "requests" / "discovery.md"
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            "# Research: Invalid\n",
        )
        self._call(
            commands.cmd_submit_handoff,
            [str(self.session), "--expect-phase", "discovery", "--status", "ready"],
        )
        manifest = self.session / "handoffs" / "discovery-handoff.yml"
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()
        before_request = request.read_bytes()

        with self.assertRaises(ToolError):
            self._call(commands.cmd_validate_handoff, [str(self.session), "--file", str(manifest)])

        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())
        self.assertEqual(before_request, request.read_bytes())
        self.assertTrue(manifest.exists())

        self._call(
            commands.cmd_retry_handoff,
            [
                str(self.session),
                "--expect-phase",
                "discovery",
                "--finding",
                "Research artifact failed deterministic validation.",
            ],
        )

        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())
        self.assertEqual("in-progress", yamlscan.nested_value("phases", "discovery", "status", records))
        self.assertEqual("pending", yamlscan.nested_value("gates", "discovery", "status", records))
        self.assertIn("Research the approved scope.", request.read_text())
        self.assertIn("Research artifact failed deterministic validation.", request.read_text())
        self.assertFalse(manifest.exists())

        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Corrected

## Problem Context
Corrected context.

## Research Conclusions
Proceed.

## Sources
Internal source.

## Source Confirmation Log
Confirmed.
    """,
        )
        self._call(
            commands.cmd_submit_handoff,
            [str(self.session), "--expect-phase", "discovery", "--status", "ready"],
        )
        self._call(commands.cmd_validate_handoff, [str(self.session), "--file", str(manifest)])
        self._accept(manifest)

        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual("functional-spec", _top(records, "current_phase"))
        self.assertEqual("complete", yamlscan.nested_value("phases", "discovery", "status", records))

    def test_manifest_path_cannot_escape_session_handoffs(self):
        self._start("discovery")
        research = self._write(
            self.session.relative_to(self.workspace) / "research.md",
            "# Research: Invalid\n",
        )
        outside = self.workspace / "handoff.yml"
        outside.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "phase": "discovery",
                    "status": "ready",
                    "artifacts": {
                        "research": {
                            "kind": "research",
                            "scope": "session",
                            "path": research.name,
                        }
                    },
                }
            )
        )
        with self.assertRaises(ToolError):
            self._call(commands.cmd_validate_handoff, [str(self.session), "--file", str(outside)])

    def test_nested_session_artifact_path_is_accepted(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "outputs" / "research.md",
            """# Research: Nested
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        manifest = self._manifest(
            "discovery",
            {
                "research": {
                    "kind": "research",
                    "scope": "session",
                    "path": "outputs/research.md",
                }
            },
        )
        self._accept(manifest)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertTrue(
            yamlscan.phase_artifact_value("discovery", "research.md", records).endswith(
                "outputs/research.md"
            )
        )

    def test_manifest_artifact_path_is_yaml_quoted_in_state(self):
        self._start("discovery")
        artifact_path = "foo: bar/research.md"
        self._write(
            self.session.relative_to(self.workspace) / artifact_path,
            """# Research: Quoted path
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        self._accept(
            self._manifest(
                "discovery",
                {
                    "research": {
                        "kind": "research",
                        "scope": "session",
                        "path": artifact_path,
                    }
                },
            )
        )
        parsed = yaml.safe_load((self.session / "sdd-state.yml").read_text())
        artifacts = parsed["phases"]["discovery"]["artifacts"]
        self.assertEqual([artifact_path], artifacts)
        self.assertTrue(all(isinstance(item, str) for item in artifacts))

    def test_handoff_requires_started_phase(self):
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Not started
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
        )
        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_validate_handoff,
                [str(self.session), "--file", str(manifest)],
            )

    def test_blocked_manifest_is_valid_but_not_accepted(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Blocked

## Problem Context
BLOCK-1 prevents completion.

## Research Conclusions
Blocked.

## Sources
Internal.

## Source Confirmation Log
Confirmed.
""",
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
            status="blocked",
            blocker_refs=[{"artifact": "research", "id": "BLOCK-1"}],
        )
        self._call(commands.cmd_validate_handoff, [str(self.session), "--file", str(manifest)])
        with self.assertRaises(ToolError):
            self._accept(manifest)

    def test_chain_requires_autopilot(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
        )
        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_accept_handoff,
                [str(self.session), "--file", str(manifest), "--gate", "pass", "--chain"],
            )

    def test_multi_file_commit_rolls_back_when_second_replace_fails(self):
        candidate = transaction.create_candidate_session(str(self.session))
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()
        Path(candidate, "sdd-state.yml").write_text("candidate-state\n")
        Path(candidate, "trace.md").write_text("candidate-trace\n")
        original_replace = os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated replacement failure")
            return original_replace(source, target)

        with mock.patch.object(transaction.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                transaction.commit_candidate(str(self.session), candidate)
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())

    def test_multi_file_commit_rolls_back_on_keyboard_interrupt(self):
        candidate = transaction.create_candidate_session(str(self.session))
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()
        Path(candidate, "sdd-state.yml").write_text("candidate-state\n")
        Path(candidate, "trace.md").write_text("candidate-trace\n")
        original_replace = os.replace

        def interrupt_trace(source, target):
            if target == str(self.session / "trace.md"):
                raise KeyboardInterrupt()
            return original_replace(source, target)

        with mock.patch.object(transaction.os, "replace", side_effect=interrupt_trace):
            with self.assertRaises(KeyboardInterrupt):
                transaction.commit_candidate(str(self.session), candidate)
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())

    def test_acceptance_requires_pending_delegation_to_be_resumed(self):
        self._call(
            commands.cmd_preflight,
            [
                str(self.session),
                "--workspace",
                str(self.workspace),
                "--allow-no-repos",
            ],
        )
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        envelope_relative = (
            self.session.relative_to(self.workspace)
            / "delegations"
            / "research-questions.md"
        )
        envelope = self._write(
            envelope_relative,
            _question_envelope("research-question", "AIDevResearcher"),
        )
        self._call(
            commands.cmd_pause_handoff,
            [
                str(self.session),
                "discovery",
                "AIDevResearcher",
                "research-question",
                str(envelope),
            ],
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
        )
        with self.assertRaises(ToolError):
            self._accept(manifest)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertTrue(yamlscan.pending_delegation_active(records))
        self.assertTrue(envelope.exists())

    def test_pending_delegation_rejects_stale_manifest_without_resume_request(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        manifest = self._manifest(
            "discovery",
            {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
        )
        envelope = self._write(
            self.session.relative_to(self.workspace) / "delegations" / "stale-questions.md",
            _question_envelope("stale", "AIDevResearcher"),
        )
        self._call(
            commands.cmd_pause_handoff,
            [str(self.session), "discovery", "AIDevResearcher", "stale", str(envelope)],
        )
        with self.assertRaises(ToolError):
            self._accept(manifest)
        self.assertTrue(envelope.exists())
        self.assertTrue(yamlscan.pending_delegation_active(
            state.read_records(str(self.session / "sdd-state.yml"))
        ))

    def test_spec_add_supports_workspace_scope_idempotently(self):
        canonical = ".aicontext/deliverables/sdd/specs/example/example/spec.md"
        self._write(canonical, _spec("Canonical specification"))
        args = [
            str(self.session),
            canonical,
            "--scope",
            "workspace",
            "--relation",
            "reference",
        ]
        self._call(commands.cmd_spec_add, args)
        self._call(commands.cmd_spec_add, args)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual(
            [(f'"{canonical}"', "workspace", "reference")],
            yamlscan.parse_state_specs(records),
        )

    def test_functional_handoff_removes_prior_spec_reference(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        self._accept(
            self._manifest(
                "discovery",
                {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
            )
        )
        self._start("functional-spec")
        removed = "specs/example/removed/spec.md"
        retained = "specs/example/example/spec.md"
        self._write(self.session.relative_to(self.workspace) / "plan.md", "# Plan: Example\n")
        self._write(self.session.relative_to(self.workspace) / removed, _spec("Removed specification"))
        self._write(self.session.relative_to(self.workspace) / retained, _spec("Retained specification"))
        self._write(
            self.session.relative_to(self.workspace) / "backlog-plan.yml",
            _backlog(self.session.name),
        )
        first_manifest = self._manifest(
            "functional-spec",
            {
                "plan": {"kind": "plan", "scope": "session", "path": "plan.md"},
                "backlog": {
                    "kind": "backlog",
                    "scope": "session",
                    "path": "backlog-plan.yml",
                },
                "primary-spec": {
                    "kind": "spec",
                    "scope": "session",
                    "path": retained,
                },
                "removed-spec": {
                    "kind": "spec",
                    "scope": "session",
                    "path": removed,
                },
            },
            specs=[
                {"artifact": "primary-spec", "relation": "primary"},
                {"artifact": "removed-spec", "relation": "primary"},
            ],
        )
        self._accept(first_manifest)
        self._call(
            commands.cmd_gate,
            [str(self.session), "spec-validation", "fail", "--evidence", "revise specs"],
        )
        self._call(
            commands.cmd_reroute,
            [str(self.session), "functional-spec", "--reason", "drop removed spec"],
        )
        self._start("functional-spec")
        removed_file = self.session / removed
        removed_file.unlink()
        removed_file.parent.rmdir()

        manifest = self._manifest(
            "functional-spec",
            {
                "plan": {"kind": "plan", "scope": "session", "path": "plan.md"},
                "backlog": {
                    "kind": "backlog",
                    "scope": "session",
                    "path": "backlog-plan.yml",
                },
                "primary-spec": {
                    "kind": "specpecs=[{"artifact": "primary-spec", "relation": "primary"}],
        )
        payload = yaml.safe_load(manifest.read_text())
        payload["spec_removals"] = [{"scope": "session", "path": removed}]
        manifest.write_text(yaml.safe_dump(payload, sort_keys=False))
        self._accept(manifest)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual(
            [(f'"{retained}"', "session", "primary")],
            yamlscan.parse_state_specs(records),
        )
        self.assertFalse(
            yamlscan.phase_artifact_value("functional-spec", removed, records)
        )
        self.assertFalse(any(removed in line for line in records))

    def test_functional_handoff_derives_input_contract_trace(self):
        contract = self._write("input-contract.txt", "Binding behavior\n")
        self._call(
            commands.cmd_contract_add,
            [
                str(self.session),
                str(contract),
                "--id",
                "CON-1",
                "--title",
                "Input contract",
            ],
        )
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        self._accept(
            self._manifest(
                "discovery",
                {"research": {"kind": "research", "scope": "session", "path": "research.md"}},
            )
        )
        self._start("functional-spec")
        spec_path = "specs/example/example/spec.md"
        self._write(self.session.relative_to(self.workspace) / "plan.md", "# Plan: Example\n")
        self._write(
            self.session.relative_to(self.workspace) / spec_path,
            _spec("Contract-backed specification"),
        )
        self._write(
            self.session.relative_to(self.workspace) / "backlog-plan.yml",
            _backlog(self.session.name),
        )
        manifest = self._manifest(
                "functional-spec",
                {
                    "plan": {"kind": "plan", "scope": "session", "path": "plan.md"},
                    "backlog": {
                        "kind": "backlog",
                        "scope": "session",
                        "path": "backlog-plan.yml",
                    },
                    "primary-spec": {
                        "kind": "spec",
                        "scope": "session",
                        "path": spec_path,
                    },
                },
                specs=[{"artifact": "primary-spec", "relation": "primary"}],
                contract_mappings=[
                    {"contract": "CON-1", "spec": "primary-spec", "acs": ["AC-1"]}
                ],
            )
        self._accept(manifest)
        self.assertNotIn("[Contract:", (self.session / spec_path).read_text())
        trace_content = (self.session / "trace.md").read_text()
        self.assertIn(
            "| CON-1 | contracts/input-contract.txt | AC-1 | "
            "Mapped in specs/example/example/spec.md. |",
            trace_content,
        )
        self._call(
            commands.cmd_gate_check,
            [str(self.session), "--phase", "spec-validation"],
        )
        late_contract = self._write("late-contract.txt", "Late binding behavior\n")
        self._call(
            commands.cmd_contract_add,
            [
                str(self.session),
                str(late_contract),
                "--id",
                "CON-2",
                "--title",
                "Late contract",
            ],
        )
        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_gate_check,
                [str(self.session), "--phase", "spec-validation"],
            )
        self._call(
            commands.cmd_contract_map,
            [
                str(self.session),
                "CON-2",
                "--spec",
                spec_path,
                "--scope",
                "session",
                "--ac",
                "AC-1",
            ],
        )
        first_trace = (self.session / "trace.md").read_text().replace(
            "| CON-2 | contracts/late-contract.txt | AC-1 | "
            "Mapped in specs/example/example/spec.md. |",
            "| CON-2 | contracts/late-contract.txt | AC-1 | "
            "Mapped in specs/example/example/spec.md.; EVID-LATE-1 |",
        )
        (self.session / "trace.md").write_text(first_trace)
        self._call(
            commands.cmd_contract_map,
            [
                str(self.session),
                "CON-2",
                "--spec",
                spec_path,
                "--scope",
                "session",
                "--ac",
                "AC-1",
            ],
        )
        self._call(
            commands.cmd_gate_check,
            [str(self.session), "--phase", "spec-validation"],
        )
        trace_content = (self.session / "trace.md").read_text()
        self.assertIn(
            "| CON-2 | contracts/late-contract.txt | AC-1 | "
            "Mapped in specs/example/example/spec.md.; EVID-LATE-1 |",
            trace_content,
        )

    def test_retro_can_delete_last_canonical_spec(self):
        canonical = ".aicontext/deliverables/sdd/specs/example/obsolete/spec.md"
        package = ".aicontext/deliverables/sdd/specs/example/obsolete"
        self._write(canonical, _spec("Obsolete specification"))
        self._call(
            commands.cmd_spec_add,
            [str(self.session), canonical, "--scope", "workspace"],
        )
        required_artifacts = {
            "discovery": ("research.md",),
            "functional-spec": ("plan.md", "backlog-plan.yml"),
            "technical-plan": ("tech-plan.md",),
            "test-design": ("test-plan.md",),
            "implementation": ("code.md",),
            "spec-verification": ("verification.md",),
        }
        for artifact_names in required_artifacts.values():
            for artifact_name in artifact_names:
                self._write(
                    self.session.relative_to(self.workspace) / artifact_name,
                    "fixture\n",
                )
        eng = state.StateEngine()
        eng.begin(str(self.session))
        for phase in yamlscan.session_mandatory_phases(eng.records):
            if phase == "retro":
                eng.set_nested_scalar("phases", phase, "status", "in-progress")
                eng.set_nested_scalar("gates", phase, "status", "pending")
            else:
                eng.set_nested_scalar("phases", phase, "status", "complete")
                eng.set_nested_scalar("phases", phase, "completed_at", '"2026-07-23T10:00:00Z"')
                eng.set_nested_scalar("gates", phase, "status", "pass")
                if not yamlscan.gate_has_evidence(phase, eng.records):
                    eng.append_nested_list_item(
                        "gates", phase, "evidence", '"validated"'
                    )
                for artifact_name in required_artifacts.get(phase, ()):
                    if not eng.nested_list_contains(
                        "phases", phase, "artifacts", artifact_name
                    ):
                        eng.append_nested_list_item(
                            "phases",
                            phase,
                            "artifacts",
                            state.yaml_scalar(artifact_name),
                        )
        eng.set_top_scalar("current_phase", "retro")
        eng.commit()
        self._write(self.session.relative_to(self.workspace) / "retro.md", _retro())
        shutil.rmtree(self.workspace / package)
        manifest = self._manifest(
            "retro",
            {"retro": {"kind": "retro", "scope": "session", "path": "retro.md"}},
            spec_deletions=[
                {
                    "registered": {"scope": "workspace", "path": canonical},
                    "package": package,
                }
            ],
        )
        self._accept(manifest)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual([], yamlscan.parse_state_specs(records))
        self.assertTrue(any(line == "specs: []" for line in records))
        self.assertTrue(
            any(
                "Canonical spec deleted: workspace:" + package in line
                for line in records
            )
        )
        trace_content = (self.session / "trace.md").read_text()
        self.assertNotIn(canonical, trace_content)
        self.assertIn("| N/A | N/A | N/A | No active specs remain. |", trace_content)
        linters.lint_session_state(str(self.session / "sdd-state.yml"))
        linters.lint_coverage(str(self.session))
        self._call(commands.cmd_session_complete, [str(self.session)])
        self.assertEqual(
            "complete",
            _top(state.read_records(str(self.session / "sdd-state.yml")), "status"),
        )

    def test_complete_code_journal_requires_evidence_row(self):
        journal = self._write(
            self.session.relative_to(self.workspace) / "code.md",
            _code_journal().replace(
                "| EVID-CODE-1 | T1 | AC-1 | example | task test | pass |\n",
                "",
            ),
        )
        with self.assertRaises(LintFailure):
            linters.lint_code(str(journal))

    def test_test_plan_rejects_coverage_without_matrix_row(self):
        plan = self._write(
            self.session.relative_to(self.workspace) / "test-plan.md",
            _test_plan().replace(
                "| AC-1 | Observable behavior | TEST-1 | Integration | Medium |",
                "| AC-1 | Observable behavior | TEST-1 | Integration | Medium |\n"
                "| AC-2 | Another behavior | TEST-2 | Integration | Medium |",
            ),
        )
        with self.assertRaises(LintFailure):
            linters.lint_test_plan(str(plan))

    def test_test_plan_requires_execution_evidence_row(self):
        plan = self._write(
            self.session.relative_to(self.workspace) / "test-plan.md",
            _test_plan().replace(
                "| EVID-TEST-1 | TEST-1 | task test | Passing output |\n",
                "",
            ),
        )
        with self.assertRaises(LintFailure):
            linters.lint_test_plan(str(plan))

    def test_coverage_ignores_stale_artifact_for_reset_phase(self):
        spec_path = "specs/example/example/spec.md"
        self._write(
            self.session.relative_to(self.workspace) / spec_path,
            _spec("Current specification"),
        )
        self._call(commands.cmd_spec_add, [str(self.session), spec_path])
        self._write(
            self.session.relative_to(self.workspace) / "test-plan.md",
            "stale downstream artifact without current AC coverage\n",
        )
        self._call(
            commands.cmd_artifact_add,
            [str(self.session), "test-design", "test-plan.md"],
        )
        linters.lint_coverage(str(self.session))

    def test_pause_handoff_rejects_wrong_phase_agent(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        envelope = self._write(
            self.session.relative_to(self.workspace) / "delegations" / "wrong-questions.md",
            _question_envelope("wrong-question", "AIDevPlanner"),
        )
        before = (self.session / "sdd-state.yml").read_bytes()
        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_pause_handoff,
                [str(self.session), "discovery", "AIDevPlanner", "wrong-question", str(envelope)],
            )
        self.assertEqual(before, (self.session / "sdd-state.yml").read_bytes())

    def test_acceptance_rejects_symlinked_delegations_directory(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
""",
        )
        external = self.workspace / "outside-delegations"
        external.mkdir()
        (self.session / "delegations").symlink_to(external, target_is_directory=True)
        envelope = external / "questions.md"
        envelope.write_text(
            _question_envelope("research-question", "AIDevResearcher")
        )
        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_pause_handoff,
                [
                    str(self.session),
                    "discovery",
                    "AIDevResearcher",
                    "research-question",
                    str(envelope),
                ],
            )
        self.assertTrue(envelope.exists())

    def test_session_scope_rejects_reserved_workspace_prefix(self):
        with self.assertRaises(ValueError):
            state.resolve_scoped_path(
                str(self.session), "session", "workspace:outputs/research.md"
            )

    def test_workspace_scope_allows_symlinked_sdd_root_only(self):
        external = Path(self.tmp.name) / "external-sdd"
        external.mkdir()
        link_workspace = Path(self.tmp.name) / "linked-workspace"
        (link_workspace / ".aicontext").mkdir(parents=True)
        (link_workspace / ".aicontext" / "deliverables").symlink_to(external)
        sessions = external / "sdd" / "sessions"
        sessions.mkdir(parents=True)
        physical_session = sessions / "20260723-linked"
        physical_session.mkdir()
        (physical_session / "sdd-state.yml").write_text("current_phase: retro\n")
        session = (
            link_workspace
            / ".aicontext"
            / "deliverables"
            / "sdd"
            / "sessions"
            / "20260723-linked"
        )
        target = external / "sdd" / "specs" / "example" / "linked" / "spec.md"
        target.parent.mkdir(parents=True)
        target.write_text(_spec("Linked specification"))
        declared = ".aicontext/deliverables/sdd/specs/example/linked/spec.md"
        self.assertEqual(
            str(target.resolve()),
            state.resolve_scoped_path(str(session), "workspace", declared),
        )
        outside = Path(self.tmp.name) / "outside-spec.md"
        outside.write_text(_spec("Outside"))
        nested_link = external / "sdd" / "specs" / "escape"
        nested_link.symlink_to(outside.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            state.resolve_scoped_path(
                str(session),
                "workspace",
                ".aicontext/deliverables/sdd/specs/escape/outside-spec.md",
            )


def _top(records, key):
    for line in records:
        if line.startswith(f"{key}:"):
            return yamlscan.trim_scalar(line.split(":", 1)[1])
    return ""


def _spec(title):
    return f"""---
schema_version: 1
---

# {title}

## Purpose
Observable behavior.

## Scope
Example scope.

## Out Of Scope
Unrelated behavior.

## Acceptance Criteria
- AC-1: Given a valid request, when it is handled, then the result is visible.

## Edge Cases
None identified.

## Error Scenarios
Invalid requests are rejected.

## Risks And Assumptions
The environment is available.
"""


def _question_envelope(delegation_id, agent):
    return f"""# Subagent Question Envelope
- **Schema:** `1.0`
- **Delegation:** `{delegation_id}`
- **Agent:** `{agent}`
- **Topic:** `scope`
- **Phase:** `discovery`
- **Status:** `needs_user_input`
- **Gate:** `paused`

## Checkpoint
- **Current step:** selection
- **Last completed:** context read
- **Resume from:** continue
- **Primary artifact:** research.md
- **Supporting artifacts:** none
- **Progress:** context captured

## Questions
### `choice`
- **Reason:** `approval_required`
- **Question:** Continue?
- **Context:** Decision-ready context.
- **Blocks:** discovery
- **Options:**
  - `yes` — Continue; impact: proceed; recommended: yes
- **Freeform:** yes
- **Default:** none

## Resume Contract
- **Read first:** research.md
- **Apply:** answer
- **Completed:** context
- **Pending:** research
- **Preserved decisions:** scope
- **Invalidate if:** scope changes
"""


def _backlog(session):
    return f"""schema_version: 2
session: {session}
source: .aicontext/deliverables/sdd/sessions/{session}
backlog_items:
  - id: US-001
    type: user-story
    title: Example
    source_spec: specs/example/example/spec.md
    change_kind: new
    publish_decision: declined
    github:
      issue_url: null
      issue_number: null
      sync_status: not-published
"""


def _tech_plan():
    return """# Tech Plan: Example

## Adviser Guidance
Guidance.

## Codebase Grounding
Grounding.

## Design Decisions
Decision.

## Implementation Plan

### Task 1: Implement example
- **What**: Implement the behavior.
- **Repo**: repos/example

## Verification Gates

### Gate: example
- Run tests.

## AC Coverage
| AC | Tasks | Gates |
|----|-------|-------|
| AC-1 | Task 1 | Gate: example |
"""


def _test_plan():
    return """# SDD Test Plan

## Test Strategy
Use an integration test.

## Acceptance Criteria Coverage
| AC ID | Acceptance Criterion | Covering Tests | Planned Test Levels | Risk |
|---|---|---|---|---|
| AC-1 | Observable behavior | TEST-1 | Integration | Medium |

## Test Matrix
| Test ID | Linked ACs | Level | Scenario | Preconditions | Expected Result | Automation Target |
|---|---|---|---|---|---|---|
| TEST-1 | AC-1 | Integration | Run behavior | Ready | Visible result | Automated |

## Execution Evidence Plan
| Evidence ID | Linked Tests | Command / Tool | Expected Output |
|---|---|---|---|
| EVID-TEST-1 | TEST-1 | task test | Passing output |
"""


def _code_journal():
    return """# Implementation Journal — handoff-test
> Tech plan: `tech-plan.md`
> Started: 2026-07-22
> Status: complete

## Repositories
| Repo | GitHub Repo | Branch | Issue | PR | Status |
|---|---|---|---|---|---|
| example | n/a | feature/example | n/a | n/a | local-only |

## Task Progress
| # | Task | Repo | Status | Phase |
|---|---|---|---|---|
| T1 | Implement example | example | done | 1 |

## Implementation Evidence
| Evidence ID | Task IDs | Linked ACs | Repo | Files / Commands | Result |
|---|---|---|---|---|---|
| EVID-CODE-1 | T1 | AC-1 | example | task test | pass |

## Key Decisions
| Decision | Repo | Rationale | Alternatives |
|---|---|---|---|
| Use existing pattern | example | Consistent | none |

## Phase Status
| Phase | Status | Notes |
|---|---|---|
| 1 — Delivery Setup | done | Local branch. |
| 2 — Coding | done | Implemented. |
| 3 — PaaS Config | done | No changes required. |
| 4 — Validation | done | Tests pass. |
| 5 — Commit | done | Local-only delivery. |
"""


def _verification():
    return """# SDD Verification

## Verification Summary
The criterion passes.

## Acceptance Criteria Verification
| AC ID | Acceptance Criterion | Evidence Reviewed | Status | Notes |
|---|---|---|---|---|
| AC-1 | Observable behavior | EVID-CODE-1 | pass | Verified. |

## Evidence Reviewed
| Evidence ID | Type | Source | Result | Linked Tests | Linked ACs |
|---|---|---|---|---|---|
| EVID-CODE-1 | implementation | code.md | pass | TEST-1 | AC-1 |

## Gate Decision
| Field | Value |
|---|---|
| Gate | spec-verification |
| Decision | pass |

## Review
### Contract Review
Reviewed.
### Findings
| Finding ID | Severity | Status | Linked ACs | Location | Description | Required Action |
|---|---|---|---|---|---|---|
| REVIEW-0 | none | closed | AC-1 | N/A | No findings. | None. |
### Combined Gate Decision
| Field | Value |
|---|---|
| Combined decision | pass |
"""


def _retro():
    return """# SDD Retro

## Outcome Summary
The behavior was delivered.

## Observations
No additional observations.

## Compounding Ledger
Canonical specification created.

## Spec Consolidation
Canonical spec exists.

## Closure Decision
Complete.
"""


if __name__ == "__main__":
    unittest.main()
