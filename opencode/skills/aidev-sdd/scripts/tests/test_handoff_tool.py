from __future__ import annotations

import contextlib
import io
import shlex
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _lib import commands, state, yamlscan  # noqa: E402
from _lib.cli import ToolError  # noqa: E402


class HandoffToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.sessions = self.workspace / ".aicontext" / "deliverables" / "sdd" / "sessions"
        self.sessions.mkdir(parents=True)
        self.session = self.sessions / f"{datetime.now().strftime('%Y%m%d')}-tool-test"
        self._call(
            commands.cmd_init,
            [str(self.sessions), "tool-test", "--name", "Handoff tool test"],
        )
        self._call(
            commands.cmd_set_track,
            [str(self.session), "exhaustive", "--rationale", "exercise handoff tool"],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, function, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(args)

    def _capture(self, function, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            function(args)
        return stdout.getvalue()

    def _capture_main(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            exit_code = commands.main(args)
        return exit_code, stdout.getvalue()

    def _start(self, phase):
        engine = state.StateEngine()
        engine.begin(str(self.session))
        engine.set_top_scalar("current_phase", phase)
        engine.commit()
        self._call(commands.cmd_phase_start, [str(self.session), phase])

    def _write(self, relative, content):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def _create(self, phase="discovery"):
        return self._capture(
            commands.cmd_create_handoff,
            [
                str(self.session),
                "--expect-phase",
                phase,
                "--need",
                "Research the approved scope.",
                "--context",
                ".aicontext/deliverables/sdd/sessions/example/research.md",
                "binding input",
            ],
        )

    def _pause(self, envelope, delegation="research.scope"):
        return self._capture(
            commands.cmd_pause_handoff,
            [
                str(self.session),
                "discovery",
                "AIDevResearcher",
                delegation,
                str(envelope),
            ],
        )

    def _resume(self, question_id="source-choice", answer="Use Source A"):
        return self._capture(
            commands.cmd_resume_handoff,
            [
                str(self.session),
                "--expect-phase",
                "discovery",
                "--answer",
                question_id,
                "source-a",
                answer,
            ],
        )

    def _retry(self, phase="discovery", *findings):
        args = [str(self.session), "--expect-phase", phase]
        for finding in findings:
            args.extend(["--finding", finding])
        return self._capture(commands.cmd_retry_handoff, args)

    def _submit(self, phase="discovery", *flags):
        return self._capture(
            commands.cmd_submit_handoff,
            [
                str(self.session),
                "--expect-phase",
                phase,
                "--status",
                "ready",
                *flags,
            ],
        )

    def test_create_handoff_uses_active_assistant_paths_and_portable_request(self):
        self._start("discovery")
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()

        output = self._create()

        request = self.session / "handoffs" / "requests" / "discovery.md"
        content = request.read_text()
        self.assertIn("AIDevResearcher", content)
        self.assertIn("Research the approved scope.", content)
        self.assertIn("submit-handoff", content)
        self.assertIn("<agent-dir>/skills/aidev-sdd", content)
        self.assertNotIn(".aicontext/packages", content)
        self.assertNotIn(str(self.workspace), content)
        self.assertNotIn("<!-- SDD_", content)
        self.assertEqual(
            "Read and execute the complete delegation at "
            f".aicontext/deliverables/sdd/sessions/{self.session.name}/handoffs/requests/discovery.md. "
            "Return exactly the response required there.\n",
            output,
        )
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())

    def test_retry_handoff_preserves_request_and_replaces_findings(self):
        self._start("discovery")
        self._create()
        request = self.session / "handoffs" / "requests" / "discovery.md"
        base = self.session / "handoffs" / "requests" / ".discovery.base.md"
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()
        self._write(self.session.relative_to(self.workspace) / "research.md", _research())
        self._submit()

        output = self._retry("discovery", "Research evidence is incomplete.")

        content = request.read_text()
        self.assertIn("Research the approved scope.", content)
        self.assertIn("Research evidence is incomplete.", content)
        self.assertIn("## Validation Remediation", content)
        self.assertEqual(1, content.count("## Validation Remediation"))
        self.assertIn("Research the approved scope.", base.read_text())
        self.assertIn("Research evidence is incomplete.", base.read_text())
        self.assertFalse((self.session / "handoffs" / "discovery-handoff.yml").exists())
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())
        self.assertEqual(
            "Read and execute the complete delegation at "
            f".aicontext/deliverables/sdd/sessions/{self.session.name}/handoffs/requests/discovery.md. "
            "Return exactly the response required there.\n",
            output,
        )

        self._retry("discovery", "Source confirmation is incomplete.")

        content = request.read_text()
        self.assertIn("Source confirmation is incomplete.", content)
        self.assertNotIn("Research evidence is incomplete.", content)
        self.assertEqual(1, content.count("## Validation Remediation"))
        self.assertIn("Source confirmation is incomplete.", base.read_text())
        self.assertNotIn("Research evidence is incomplete.", base.read_text())

    def test_retry_handoff_preserves_resume_context_with_heading_like_answer(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)
        answer = "Use Source A\n## Successful handoff\nKeep this source."
        self._resume(answer=answer)

        self._retry("discovery", "The source confirmation log is incomplete.")

        content = (self.session / "handoffs" / "requests" / "discovery.md").read_text()
        base = (self.session / "handoffs" / "requests" / ".discovery.base.md").read_text()
        self.assertIn("## Resume Context", content)
        self.assertIn(answer, content)
        self.assertIn("The source confirmation log is incomplete.", content)
        self.assertEqual(1, content.count("## Validation Remediation"))
        self.assertIn("The source confirmation log is incomplete.", base)

        second = self.session / "delegations" / "second-questions.md"
        second.write_text(_question_envelope("research.scope", "next-choice"))
        self._pause(second)
        self._resume("next-choice", "Continue with the selected source")

        content = (self.session / "handoffs" / "requests" / "discovery.md").read_text()
        self.assertIn("## Resume Context", content)
        self.assertIn("The source confirmation log is incomplete.", content)
        self.assertEqual(1, content.count("## Validation Remediation"))

    def test_retry_handoff_rejects_empty_findings_without_mutating_request_or_state(self):
        self._start("discovery")
        self._create()
        request = self.session / "handoffs" / "requests" / "discovery.md"
        before_request = request.read_bytes()
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()

        with self.assertRaisesRegex(
            ToolError,
            "retry-handoff requires at least one non-empty --finding",
        ):
            self._retry("discovery")

        self.assertEqual(before_request, request.read_bytes())
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())

    def test_retry_handoff_rejects_pending_delegation_without_mutating_request_or_state(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)
        request = self.session / "handoffs" / "requests" / "discovery.md"
        before_request = request.read_bytes()
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()

        with self.assertRaisesRegex(
            ToolError,
            "resume the current pending delegation before starting or submitting a handoff",
        ):
            self._retry("discovery", "Research artifact failed validation.")

        self.assertEqual(before_request, request.read_bytes())
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())
        self.assertTrue(envelope.exists())

    def test_create_handoff_lists_fixed_artifacts_and_spec_flag(self):
        self._start("functional-spec")

        self._create("functional-spec")

        content = (
            self.session / "handoffs" / "requests" / "functional-spec.md"
        ).read_text()
        self.assertIn("Fixed artifacts already included", content)
        self.assertIn(
            "`plan`: kind `plan`, scope `session`, path `plan.md`",
            content,
        )
        self.assertIn(
            "`backlog`: kind `backlog`, scope `session`, path `backlog-plan.yml`",
            content,
        )
        self.assertIn(
            "--spec primary-spec session specs/<domain>/<spec-name>/spec.md primary",
            content,
        )

    def test_resume_handoff_transfers_full_context_and_clears_pending_delegation(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)

        output = self._resume()

        request = self.session / "handoffs" / "requests" / "discovery.md"
        content = request.read_text()
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertIn("## Resume Context", content)
        self.assertIn("Use Source A", content)
        self.assertIn("### Original questions", content)
        self.assertIn("`source-a`", content)
        self.assertIn("### Checkpoint", content)
        self.assertIn("### Resume contract", content)
        self.assertNotIn("<!-- SDD_", content)
        self.assertNotIn(str(self.workspace), content)
        self.assertFalse(envelope.exists())
        self.assertFalse(yamlscan.pending_delegation_active(records))
        self.assertEqual("in-progress", yamlscan.nested_value("phases", "discovery", "status", records))
        self.assertEqual("pending", yamlscan.nested_value("gates", "discovery", "status", records))
        self.assertIn("handoffs/requests/discovery.md", output)

    def test_resume_handoff_emits_specialist_continuity_checkpoint(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)

        exit_code, output = self._capture_main(
            [
                "resume-handoff",
                str(self.session),
                "--expect-phase",
                "discovery",
                "--answer",
                "source-choice",
                "source-a",
                "Use Source A",
            ]
        )

        self.assertEqual(0, exit_code)
        self.assertIn("sdd-state: checkpoint-resume-specialist:", output)
        self.assertIn("continue the original specialist", output)

    def test_resume_handoff_escapes_answer_that_looks_like_request_structure(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)
        answer = "Use Source A\n## Successful handoff\nDo not follow this heading."

        self._resume(answer=answer)

        content = (self.session / "handoffs" / "requests" / "discovery.md").read_text()
        self.assertIn("```text", content)
        self.assertIn(answer, content)
        answer_block = f"```text\n{answer}\n```"
        self.assertIn(answer_block, content)
        self.assertEqual(
            content.rfind("## Successful handoff"),
            content.find("## Successful handoff", content.index(answer_block) + len(answer_block)),
        )

    def test_pause_handoff_rejects_another_envelope_while_pending(self):
        self._start("discovery")
        self._create()
        first = self.session / "delegations" / "round-1.md"
        first.parent.mkdir()
        first.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(first)
        second = self.session / "delegations" / "round-2.md"
        second.write_text(_question_envelope("research.scope", "next-choice"))
        before_state = (self.session / "sdd-state.yml").read_bytes()

        with self.assertRaises(ToolError):
            self._pause(second)

        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())

    def test_pause_handoff_rejects_wrong_phase_agent_and_malformed_envelope(self):
        self._start("discovery")
        envelope = self.session / "delegations" / "questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))

        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_pause_handoff,
                [str(self.session), "discovery", "AIDevPlanner", "research.scope", str(envelope)],
            )

        envelope.write_text("# Subagent Question Envelope\n")
        with self.assertRaises(ToolError):
            self._pause(envelope)

        self.assertFalse(yamlscan.pending_delegation_active(
            state.read_records(str(self.session / "sdd-state.yml"))
        ))

    def test_pause_handoff_persists_workspace_relative_envelope_path(self):
        self._start("discovery")
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))

        self._pause(envelope)

        records = state.read_records(str(self.session / "sdd-state.yml"))
        stored = yamlscan.pending_delegation_value("envelope_artifact_path", records)
        self.assertFalse(Path(stored).is_absolute())
        self.assertEqual(
            f".aicontext/deliverables/sdd/sessions/{self.session.name}/delegations/research-questions.md",
            stored,
        )

    def test_invalid_resume_leaves_request_state_and_envelope_unchanged(self):
        self._start("discovery")
        self._create()
        envelope = self.session / "delegations" / "research-questions.md"
        envelope.parent.mkdir()
        envelope.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(envelope)
        request = self.session / "handoffs" / "requests" / "discovery.md"
        before_request = request.read_bytes()
        before_state = (self.session / "sdd-state.yml").read_bytes()

        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_resume_handoff,
                [str(self.session), "--expect-phase", "discovery"],
            )

        self.assertEqual(before_request, request.read_bytes())
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertTrue(envelope.exists())

    def test_pause_handoff_rejects_envelope_outside_session_delegations(self):
        self._start("discovery")
        outside = self.workspace / "outside-questions.md"
        outside.write_text(_question_envelope("research.scope", "source-choice"))

        with self.assertRaises(ToolError):
            self._call(
                commands.cmd_pause_handoff,
                [
                    str(self.session),
                    "discovery",
                    "AIDevResearcher",
                    "research.scope",
                    str(outside),
                ],
            )

        self.assertFalse(yamlscan.pending_delegation_active(
            state.read_records(str(self.session / "sdd-state.yml"))
        ))

    def test_second_question_round_can_pause_after_a_resolved_round(self):
        self._start("discovery")
        self._create()
        first = self.session / "delegations" / "round-1.md"
        first.parent.mkdir()
        first.write_text(_question_envelope("research.scope", "source-choice"))
        self._pause(first)
        self._resume()

        second = self.session / "delegations" / "round-2.md"
        second.write_text(_question_envelope("research.scope", "next-choice"))
        self._pause(second)
        records = state.read_records(str(self.session / "sdd-state.yml"))
        self.assertEqual("2", yamlscan.pending_delegation_value("round", records))

        self._resume("next-choice", "Continue second round")
        self.assertFalse(second.exists())
        self.assertFalse(yamlscan.pending_delegation_active(
            state.read_records(str(self.session / "sdd-state.yml"))
        ))

    def test_generated_submit_command_runs_against_the_unified_cli_contract(self):
        self._start("discovery")
        self._create()
        self._write(self.session.relative_to(self.workspace) / "research.md", _research())
        request = (self.session / "handoffs" / "requests" / "discovery.md").read_text()
        command = next(
            line
            for line in request.splitlines()
            if "submit-handoff" in line
        )

        self.assertEqual(
            "python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py "
            f"submit-handoff .aicontext/deliverables/sdd/sessions/{self.session.name} "
            "--expect-phase discovery --status ready",
            command,
        )
        self._submit()
        self.assertTrue((self.session / "handoffs" / "discovery-handoff.yml").exists())

    def test_submit_handoff_writes_profile_manifest_without_mutating_state(self):
        self._start("discovery")
        self._write(
            self.session.relative_to(self.workspace) / "research.md",
            _research(),
        )
        before_state = (self.session / "sdd-state.yml").read_bytes()
        before_trace = (self.session / "trace.md").read_bytes()

        output = self._submit()

        manifest = self.session / "handoffs" / "discovery-handoff.yml"
        payload = yaml.safe_load(manifest.read_text())
        self.assertEqual(
            {"kind": "research", "scope": "session", "path": "research.md"},
            payload["artifacts"]["research"],
        )
        self.assertEqual(
            f"My handoff is in: .aicontext/deliverables/sdd/sessions/{self.session.name}/handoffs/discovery-handoff.yml\n",
            output,
        )
        self.assertEqual(before_state, (self.session / "sdd-state.yml").read_bytes())
        self.assertEqual(before_trace, (self.session / "trace.md").read_bytes())

    def test_submit_handoff_supports_functional_spec_dynamic_flags(self):
        self._start("functional-spec")
        self._write(self.session.relative_to(self.workspace) / "plan.md", "# Plan: Example\n")
        self._write(self.session.relative_to(self.workspace) / "backlog-plan.yml", _backlog(self.session.name))
        self._write(self.session.relative_to(self.workspace) / "specs/orders/refund/spec.md", _spec("Refund"))
        contract = self._write("contract.txt", "binding\n")
        self._call(
            commands.cmd_contract_add,
            [str(self.session), str(contract), "--id", "CON-1", "--title", "Contract"],
        )

        self._submit(
            "functional-spec",
            "--spec", "primary-spec", "session", "specs/orders/refund/spec.md", "primary",
            "--contract-map", "CON-1", "primary-spec", "AC-1",
        )

        payload = yaml.safe_load((self.session / "handoffs" / "functional-spec-handoff.yml").read_text())
        self.assertEqual("plan.md", payload["artifacts"]["plan"]["path"])
        self.assertEqual(["AC-1"], payload["contract_mappings"][0]["acs"])

    def test_functional_spec_request_supports_blocked_handoff_with_primary_spec(self):
        self._start("functional-spec")
        self._create("functional-spec")
        self._write(
            self.session.relative_to(self.workspace) / "plan.md",
            "# Plan: Example\n\nfinal-expanded-plan-approval\n",
        )
        self._write(
            self.session.relative_to(self.workspace) / "backlog-plan.yml",
            _backlog(self.session.name),
        )
        self._write(
            self.session.relative_to(self.workspace) / "specs/orders/refund/spec.md",
            _spec("Refund"),
        )
        request = (self.session / "handoffs" / "requests" / "functional-spec.md").read_text()
        command = request[request.index("python3 "):request.index("\n```", request.index("python3 "))]
        submit_args = shlex.split(
            command.replace("<domain>", "orders").replace("<spec-name>", "refund")
        )
        submit_args = submit_args[submit_args.index("submit-handoff") + 1:]
        submit_args[0] = str(self.session)
        submit_args[submit_args.index("ready")] = "blocked"
        submit_args.extend(["--blocker", "plan", "final-expanded-plan-approval"])

        self._call(commands.cmd_submit_handoff, submit_args)

        payload = yaml.safe_load((self.session / "handoffs" / "functional-spec-handoff.yml").read_text())
        self.assertEqual("blocked", payload["status"])
        self.assertEqual(
            [{"artifact": "primary-spec", "relation": "primary"}],
            payload["specs"],
        )
        self.assertEqual(
            [{"artifact": "plan", "id": "final-expanded-plan-approval"}],
            payload["blocker_refs"],
        )

    def test_submit_handoff_rejects_duplicate_fixed_artifact_path(self):
        self._start("functional-spec")
        self._write(self.session.relative_to(self.workspace) / "plan.md", "# Plan: Example\n")
        self._write(
            self.session.relative_to(self.workspace) / "backlog-plan.yml",
            _backlog(self.session.name),
        )
        self._write(
            self.session.relative_to(self.workspace) / "specs/orders/refund/spec.md",
            _spec("Refund"),
        )
        primary_spec = (
            "--spec", "primary-spec", "session", "specs/orders/refund/spec.md", "primary",
        )

        with self.assertRaisesRegex(
            ToolError,
            "--artifact must not redeclare fixed artifact: plan",
        ):
            self._submit(
                "functional-spec",
                "--artifact", "plan", "plan", "session", "plan.md",
                *primary_spec,
            )

        with self.assertRaisesRegex(
            ValueError,
            "artifacts backlog and backlog-plan reference the same file",
        ):
            self._submit(
                "functional-spec",
                "--artifact", "backlog-plan", "backlog", "session", "backlog-plan.yml",
                *primary_spec,
            )

        self.assertFalse(
            (self.session / "handoffs" / "functional-spec-handoff.yml").exists()
        )

    def test_acceptance_removes_request_only_after_success(self):
        self._start("discovery")
        self._create()
        request = self.session / "handoffs" / "requests" / "discovery.md"
        self._write(self.session.relative_to(self.workspace) / "research.md", "# Research: Invalid\n")
        self._submit()
        manifest = self.session / "handoffs" / "discovery-handoff.yml"

        with self.assertRaises(ToolError):
            self._call(commands.cmd_accept_handoff, [str(self.session), "--file", str(manifest), "--gate", "pass"])
        self.assertTrue(request.exists())

        (self.session / "research.md").write_text(_research())
        self._call(commands.cmd_accept_handoff, [str(self.session), "--file", str(manifest), "--gate", "pass"])
        self.assertFalse(request.exists())
        self.assertFalse((self.session / "handoffs" / "requests" / ".discovery.base.md").exists())


def _research():
    return """# Research: Example
## Problem Context
Context.
## Research Conclusions
Proceed.
## Sources
Internal.
## Source Confirmation Log
Confirmed.
"""


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


def _backlog(session):
    return f"""schema_version: 2
session: {session}
source: .aicontext/deliverables/sdd/sessions/{session}
backlog_items:
  - id: US-001
    type: user-story
    title: Example
    source_spec: specs/orders/refund/spec.md
    change_kind: new
    publish_decision: declined
    github:
      issue_url: null
      issue_number: null
      sync_status: not-published
"""


def _question_envelope(delegation_id, question_id):
    return f"""# Subagent Question Envelope

- **Schema:** `1.0`
- **Delegation:** `{delegation_id}`
- **Agent:** `AIDevResearcher`
- **Topic:** `scope`
- **Phase:** `discovery`
- **Status:** `needs_user_input`
- **Gate:** `paused`

## Checkpoint

- **Current step:** source selection
- **Last completed:** context read
- **Resume from:** run research
- **Primary artifact:** research.md
- **Supporting artifacts:** none
- **Progress:** context captured

## Questions

### `{question_id}`

- **Reason:** `approval_required`
- **Question:** Which source?
- **Context:** Source A is recommended.
- **Blocks:** discovery
- **Options:**
  - `source-a` — Source A; impact: proceed; recommended: yes
- **Freeform:** yes
- **Default:** none

## Resume Contract

- **Read first:** research.md
- **Apply:** selected source
- **Completed:** context
- **Pending:** research
- **Preserved decisions:** scope
- **Invalidate if:** scope changes
"""


if __name__ == "__main__":
    unittest.main()
