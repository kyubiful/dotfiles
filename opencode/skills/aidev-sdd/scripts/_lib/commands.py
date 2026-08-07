"""sdd-state command implementations.

Each mutation command copies the state to a working file, edits it in place with
line-based transforms (never a full YAML reserialize), lints the result, and only
then replaces the real file."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import yaml

from . import checkpoints, handoff_tool, handoffs, linters, phases, state, text, trace, transaction, yamlscan
from .cli import LintFailure, ToolError
from .state import (
    StateEngine,
    fail,
    now_utc,
    read_records,
    replace_orchestration_subblock,
    sha256_of,
    state_file_of,
)

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "..", "assets")

trim = yamlscan.trim_scalar


USAGE = """Usage: sdd-state.py <command> [args]

Session lifecycle:
  init <sessions-root> <slug> --name <name>
      Create sessions/{YYYYMMDD}-{slug}/ with sdd-state.yml from the template
      (identity + real UTC timestamps). Fails on collision.
  set-track <session-dir> <simple|moderate|complex|exhaustive|smart> --rationale <text>
      [--phases <csv>] [--signals <csv>] [--skip-reason <text>] [--by <agent>]
      Set track + classification, mark skipped phases/gates with evidence,
      copy the matching trace template, set current_phase, complete bootstrap,
      and record the decision. One atomic operation. For smart, --phases carries
      the user-selected optional phases (the rest of the non-core phases are
      skipped).
  session-complete <session-dir>
      Set session status: complete (lint enforces all mandatory phases).
  set-mode <session-dir> <interactive|autopilot>
      Persist the session execution mode. interactive: stop after each phase
      for user confirmation; autopilot: unattended phase chaining is allowed.
      Missing field means interactive. Every transition guidance reports it.
  status <session-dir>
      Compact state summary (read-only; replaces reading the full YAML).
  metrics <session-dir>
      Session efficiency telemetry report (read-only).

Phase transitions (metrics are instrumented automatically):
  phase-start <session-dir> <phase>
      Mark phase in-progress; metrics: started_at now / specialist_invocations+1.
  question-round <session-dir> <phase>
      metrics: question_rounds+1 for the phase.
  gate <session-dir> <phase> <pass|conditional-pass|fail|paused> --evidence <text> [--evidence <text> ...]
      Set the gate status with evidence entries.
  phase-complete <session-dir> <phase>
      Mark phase complete with completed_at now; metrics: completed_at now.
  advance <session-dir>
      Move current_phase to the next non-skipped phase for the track.
  reroute <session-dir> <target-phase> --reason <text>
      Remediation loop: route a failed gate back to an earlier phase. Requires
      the current phase gate to be fail. Atomically: sets current_phase to the
      target, resets the target and every later re-run phase to pending
      (completed_at cleared, gates pending with evidence history preserved),
      appends a reroute evidence note on the target gate, and records the
      decision. Follow with phase-start + delegation. Never hand-edit this.
      Bounded loop: when the failed gate is spec-verification and the target is
      inside the technical-plan -> implementation window, one loop iteration is
      consumed; once orchestration.remediation_loop.iterations reaches
      max_iterations the reroute is refused (escalate to the user; --force only
      after an explicit decision to continue). Rerouting to an earlier scope
      phase (functional-spec) instead resets the loop. No-op on states without
      the block (older sessions opt in via loop-budget).
  loop-budget <session-dir> <max-iterations>
      Set the global bounded-remediation-loop budget
      (orchestration.remediation_loop.max_iterations). Creates the block on
      older states that lack it. Use to raise the budget after the user
      explicitly approves more iterations, or to tune the default (3).
  validate-handoff <session-dir> --file <manifest.yml>
      Validate a reference-based specialist handoff against staged candidate
      state and trace files. Read-only: never changes lifecycle files.
  accept-handoff <session-dir> --file <manifest.yml> --gate <pass|conditional-pass>
      [--evidence <text> ...] [--chain]
      Validate and accept a handoff as one logical transaction. Any failure
      leaves state and trace unchanged. --chain starts the next phase and is
      allowed only in autopilot mode.
  next <session-dir>
      Advisory routing: read the state and print the mechanically indicated
      next action (resume pending delegation / run gate-check / complete phase
      / advance / delegate current phase / session-complete). Read-only; user
      gates and semantic review remain the orchestrator's judgment.

Registries:
  artifact-add <session-dir> <phase> <path>          (idempotent)
  decision-add <session-dir> --decision <text> [--owner <agent>]
  spec-add <session-dir> <path> [--scope session|workspace] [--relation primary|dependency|reference]
  spec-repoint <session-dir> <old-path> <new-path>
      [--old-scope session|workspace] [--new-scope session|workspace]
      [--relation primary|dependency|reference]
  contract-map <session-dir> <contract-id> --spec <path>
      --scope <session|workspace> --ac <AC-N> [--ac <AC-N> ...]
      Add a late contract-to-AC mapping to Input Contract Trace without
      advancing or reopening a phase.

Delegation lifecycle:
   create-handoff <session-dir> --expect-phase <phase> --need <text>
       [--context <path> <note>] [--policy <key> <value>]
       Create the current specialist request. The request is portable and refers
       only to the active assistant's local resources.
   pause-handoff <session-dir> <phase> <agent> <delegation-id> <envelope-path> [--round <n>]
       Persist a specialist question envelope, block the phase, and pause its
       gate. The envelope remains immutable until resume-handoff succeeds.
   resume-handoff <session-dir> --expect-phase <phase>
       --answer <question-id> <selected|none> <answer> [--answer ...]
       Validate mapped answers, replace the request with a self-contained
       resume context, clear pending_delegation, reactivate the phase, and
       delete the consumed envelope as one transaction.
   retry-handoff <session-dir> --expect-phase <phase> --finding <text> [--finding <text> ...]
       Preserve the active self-contained request, replace its validation
       remediation context, and delete the stale phase manifest. The
       orchestrator continues the specialist using the printed pointer prompt.
   submit-handoff <session-dir> --expect-phase <phase> --status <ready|blocked>
       [phase-specific repeated flags]
       Materialize the specialist's minimal handoff manifest from the active
       phase profile. This command does not change lifecycle state.

Contracts:
  contract-add <session-dir> <file> --title <text> [--source <text>]
      [--summary <text>] [--media-type <type>] [--id <id>]
      Create contracts.yml lazily, compute sha256, register the entry, and
      list contracts.yml under the bootstrap phase artifacts.

Workspace preflight:
  preflight <session-dir> [--workspace <root>] [--validator <path>] [--allow-no-repos]
      Run the legacy-layout probe plus the deterministic workspace guidance
      validation and persist the result under orchestration.workspace_preflight
      atomically. The guidance validator is injected by the caller (--validator):
      any executable accepting --workspace <root> that prints one "PASS <repo>"
      or "FAIL <repo>" line per repository plus a final "... summary: ..." line
      (exit 0 all-pass, non-zero otherwise). aidev-explore ships the standard
      implementation; this script has no dependency on it. status=ready when
      every repository passes; status=blocked with per-repo reasons otherwise
      (also when repositories exist but no validator was provided). Delegate to
      AIDevInit only when blocked repositories need initialization, then re-run.

Validation composites:
  gate-check <session-dir> [--phase <phase>]
      Run the orchestrator validation contract for the phase (default:
      current_phase): the phase artifact lint plus every required cross check
      (session, contracts, coverage, trace-gate). One command, one verdict.
  layout-probe <session-dir>
      Deterministic legacy-layout probe: lists the sdd root and reports
      layout=clean or layout=legacy with the offending entries (exit 2 on
      legacy). Never reads file bodies.

All mutating commands refresh session.updated_at, then validate the result
with the deterministic session lint BEFORE committing the change. A failing
lint rolls the mutation back (use --force to commit anyway with a warning)."""


def usage() -> str:
    return USAGE


def _head(prefix: str, file: str) -> str:
    return trim(text.head1_sub(prefix, file))


def execution_mode_of(file: str) -> str:
    mode = _head(r"execution_mode:[[:space:]]*", file)
    return mode or "interactive"


def _require_value(name: str) -> None:
    pass


# ---------------------------------------------------------------------------
# init / set-track
# ---------------------------------------------------------------------------

def cmd_init(args: list[str]) -> None:
    if not args:
        fail("usage: init <sessions-root> <slug> --name <name>")
    root = args[0]
    if len(args) < 2:
        fail("missing slug")
    slug = args[1]
    rest = args[2:]
    name = ""
    i = 0
    while i < len(rest):
        if rest[i] == "--name":
            name = rest[i + 1]
            i += 2
        else:
            fail(f"unknown init option: {rest[i]}")
    if not name:
        fail("init requires --name")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        fail(f"slug must be kebab-case: {slug}")

    from datetime import datetime

    date_ymd = datetime.now().strftime("%Y%m%d")
    session_id = f"{date_ymd}-{slug}"
    directory = os.path.join(root.rstrip("/"), session_id)
    if os.path.exists(directory):
        fail(f"session already exists: {directory} (choose another slug)")
    template = os.path.join(ASSETS_DIR, "sdd-state-template.yml")
    if not os.path.isfile(template):
        fail(f"state template not found at {ASSETS_DIR}")

    os.makedirs(os.path.join(directory, "handoffs"), exist_ok=True)
    ts = now_utc()
    with open(template) as handle:
        content = handle.read()
    content = content.replace('id: "YYYYMMDD-{slug}"', f'id: "{session_id}"')
    content = content.replace(
        'name: "Descriptive session name"', f"name: {state.yaml_scalar(name)}"
    )
    content = content.replace('date: "YYYYMMDD"', f'date: "{date_ymd}"')
    content = content.replace("<AIDEV_NOW_UTC>", ts)
    state_path = os.path.join(directory, "sdd-state.yml")
    with open(state_path, "w") as handle:
        handle.write(content)

    ok, out = state.capture_lint(linters.lint_session_state, state_path)
    if not ok:
        print(f"sdd-state: warning: freshly initialized state failed lint: {out}", file=sys.stderr)

    print(f"sdd-state: init OK: {directory}")
    print(f'sdd-state: next: set-track {directory} <simple|moderate|complex|exhaustive|smart> --rationale "..."')


def _apply_track_classification(records, by, ts, rationale, signals):
    out = []
    in_tc = False
    for line in records:
        if re.match(r"^track_classification:", line):
            in_tc = True
            out.append(line)
            continue
        if in_tc and re.match(r"^\S", line):
            in_tc = False
        if in_tc and re.match(r"^  decided_by:", line):
            out.append(f"  decided_by: {state.yaml_scalar(by)}")
            continue
        if in_tc and re.match(r"^  decided_at:", line):
            out.append(f'  decided_at: "{ts}"')
            continue
        if in_tc and re.match(r"^  rationale:", line):
            out.append(f"  rationale: {state.yaml_scalar(rationale)}")
            continue
        if in_tc and re.match(r"^  signals:", line):
            if signals == "":
                out.append("  signals: []")
            else:
                out.append("  signals:")
                for part in signals.split(","):
                    out.append(f"    - {state.yaml_scalar(part.strip())}")
            continue
        out.append(line)
    return out


def _delete_md_section(path: str, section: str) -> None:
    """Delete a '## <section>' block (header through the line before the next
    '## ') from a markdown file, in place."""
    with open(path) as handle:
        lines = handle.read().split("\n")
    out = []
    skip = False
    target = "## " + section
    for line in lines:
        if line.rstrip() == target:
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if skip:
            continue
        out.append(line)
    with open(path, "w") as handle:
        handle.write("\n".join(out))


def _smart_trace_prune(path: str, skipped_phases: list[str]) -> None:
    """Prune the exhaustive trace to a smart selection: set Track to smart,
    resolve the Source spec placeholder when functional-spec is not selected,
    and delete the sections owned by every skipped phase."""
    with open(path) as handle:
        body = handle.read()
    body = re.sub(r"(?m)^\| Track \|.*\|$", "| Track | smart |", body)
    if "functional-spec" in skipped_phases:
        body = re.sub(
            r"(?m)^\| Source spec \|.*\|$",
            "| Source spec | n/a (functional-spec not selected) |",
            body,
        )
    with open(path, "w") as handle:
        handle.write(body)
    for phase in skipped_phases:
        for section in phases.phase_trace_sections(phase):
            _delete_md_section(path, section)


def cmd_set_track(args: list[str]) -> None:
    if not args:
        fail("usage: set-track <session-dir> <track> --rationale <text>")
    directory = args[0]
    if len(args) < 2:
        fail("missing track")
    track = args[1]
    rest = args[2:]
    rationale = signals = skip_reason = phases_csv = ""
    by = "AIDevOrchestrator"
    force = False
    i = 0
    while i < len(rest):
        opt = rest[i]
        if opt == "--rationale":
            rationale = rest[i + 1]; i += 2
        elif opt == "--signals":
            signals = rest[i + 1]; i += 2
        elif opt == "--skip-reason":
            skip_reason = rest[i + 1]; i += 2
        elif opt == "--by":
            by = rest[i + 1]; i += 2
        elif opt == "--phases":
            phases_csv = rest[i + 1]; i += 2
        elif opt == "--force":
            force = True; i += 1
        else:
            fail(f"unknown set-track option: {opt}")
    if track not in ("simple", "moderate", "complex", "exhaustive", "smart"):
        fail(f"invalid track: {track} (allowed: simple | moderate | complex | exhaustive | smart)")
    if not rationale:
        fail("set-track requires --rationale")
    if not skip_reason:
        skip_reason = rationale

    # Resolve which phases this track skips. Static tracks use their fixed list;
    # the smart track builds it from the user-selected optional phases (--phases),
    # keeping the immutable core (bootstrap, implementation, spec-verification,
    # retro) always active.
    if track == "smart":
        selected = []
        for raw in phases_csv.split(","):
            name = raw.strip()
            if not name:
                continue
            if name not in phases.SMART_SELECTABLE:
                fail(
                    f"smart --phases: '{name}' is not selectable "
                    f"(choose from: {' '.join(phases.SMART_SELECTABLE)})"
                )
            selected.append(name)
        if "spec-validation" in selected and "functional-spec" not in selected:
            fail("smart --phases: spec-validation requires functional-spec")
        if "test-design" in selected and "functional-spec" not in selected:
            fail("smart --phases: test-design requires functional-spec")
        skipped_phases = [p for p in phases.SMART_SELECTABLE if p not in selected]
    else:
        skipped_phases = phases.track_skipped_phases(track)

    eng = StateEngine(force)
    eng.begin(directory)
    ts = now_utc()

    eng.set_top_scalar("track", track)
    eng.records = _apply_track_classification(eng.records, by, ts, rationale, signals)

    for phase in skipped_phases:
        eng.set_nested_scalar("phases", phase, "status", "skipped")
        eng.set_nested_scalar("gates", phase, "status", "skipped")
        eng.append_nested_list_item(
            "gates", phase, "evidence", state.yaml_scalar(f"skipped: track={track}; {skip_reason}")
        )

    eng.set_nested_scalar("phases", "bootstrap", "status", "complete")
    eng.set_nested_scalar("phases", "bootstrap", "completed_at", f'"{ts}"')
    eng.set_nested_scalar("gates", "bootstrap", "status", "pass")
    eng.append_nested_list_item("gates", "bootstrap", "evidence", f'"session initialized; track={track} classified"')
    if not eng.nested_list_contains("phases", "bootstrap", "artifacts", "sdd-state.yml"):
        eng.append_nested_list_item("phases", "bootstrap", "artifacts", "sdd-state.yml")
    if not eng.nested_list_contains("phases", "bootstrap", "artifacts", "trace.md"):
        eng.append_nested_list_item("phases", "bootstrap", "artifacts", "trace.md")

    first_active = ""
    for phase in phases.STANDARD_PHASES:
        if phase == "bootstrap":
            continue
        if phase in skipped_phases:
            continue
        first_active = phase
        break
    if not first_active:
        fail(f"track {track} has no active phase after bootstrap")
    eng.set_top_scalar("current_phase", first_active)

    records, found = state.insert_after(
        eng.records,
        r"^decisions:",
        [
            f'  - date: "{ts}"',
            f"    decision: {state.yaml_scalar(f'Track classified as {track}. {rationale}')}",
            f"    owner: {state.yaml_scalar(by)}",
        ],
    )
    if not found:
        fail("decisions block not found")
    eng.records = records

    trace_asset = "trace-template-exhaustive.md"
    if track == "complex":
        trace_asset = "trace-template-complex.md"
    elif track == "moderate":
        trace_asset = "trace-template-moderate.md"
    elif track == "simple":
        trace_asset = "trace-template-simple.md"
    trace_src = os.path.join(ASSETS_DIR, trace_asset)
    if not os.path.isfile(trace_src):
        fail(f"trace template not found: {trace_asset}")
    import shutil

    trace_dest = os.path.join(directory.rstrip("/"), "trace.md")
    shutil.copy(trace_src, trace_dest)
    if track == "smart":
        _smart_trace_prune(trace_dest, skipped_phases)

    eng.commit()
    print(f"sdd-state: set-track OK: track={track} current_phase={first_active} trace={trace_asset}")


# ---------------------------------------------------------------------------
# status / metrics / next
# ---------------------------------------------------------------------------

def _workspace_preflight_status(lines: list[str]) -> str:
    in_o = False
    for i, line in enumerate(lines):
        if re.match(r"^orchestration:", line):
            in_o = True
            continue
        if in_o and re.match(r"^\S", line):
            in_o = False
        if in_o and re.match(r"^  workspace_preflight:", line):
            value = re.sub(r"^  workspace_preflight:\s*", "", line)
            if value != "":
                return value
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if re.match(r"^    status:", nxt):
                    return re.sub(r"^    status:\s*", "", nxt)
                if not re.match(r"^    ", nxt):
                    break
                j += 1
            return "block"
    return ""


def cmd_status(args: list[str]) -> None:
    if not args:
        fail("usage: status <session-dir>")
    file = state_file_of(args[0])
    lines = text.read_lines(file)

    sid = _head(r"[[:space:]]+id:[[:space:]]*", file)
    track = _head(r"track:[[:space:]]*", file)
    sstatus = _head(r"status:[[:space:]]*", file)
    current = _head(r"current_phase:[[:space:]]*", file)
    exec_mode = execution_mode_of(file)

    pending = "none"
    if yamlscan.pending_delegation_active(lines):
        agent = yamlscan.pending_delegation_value("agent", lines)
        pending = agent or "set"

    preflight = _workspace_preflight_status(lines)

    print(f"session={sid} status={sstatus} track={track} current_phase={current} execution_mode={exec_mode}")
    print(f"pending_delegation={pending} workspace_preflight={preflight or 'null'}")

    if not yamlscan.pending_delegation_active(lines):
        delegation_dir = os.path.join(args[0], "delegations")
        if os.path.isdir(delegation_dir):
            envelopes = sorted(
                name
                for name in os.listdir(delegation_dir)
                if name.endswith(("-questions.md", "-questions.yml", "-question-envelope.yml"))
            )
            if envelopes:
                print(
                    "unregistered_question_envelopes="
                    + ",".join(os.path.join("delegations", name) for name in envelopes)
                )

    phases_line = ""
    gates_line = ""
    for p in phases.STANDARD_PHASES:
        ps = trim(yamlscan.nested_value("phases", p, "status", lines))
        gs = trim(yamlscan.nested_value("gates", p, "status", lines))
        phases_line += f"{p}={ps} "
        gates_line += f"{p}={gs} "
    print(f"phases: {phases_line}")
    print(f"gates: {gates_line}")

    specs_count = 0
    s = False
    for line in lines:
        if re.match(r"^specs:", line):
            s = True
            continue
        if s and re.match(r"^\S", line):
            s = False
        if s and re.match(r"^\s*-\s+path:", line):
            specs_count += 1
    print(f"specs={specs_count}")

    if text.grep_q(r"^  remediation_loop:", file):
        rl_max = trim(yamlscan.nested_value("orchestration", "remediation_loop", "max_iterations", lines))
        rl_iters = trim(yamlscan.nested_value("orchestration", "remediation_loop", "iterations", lines))
        print(f"remediation_loop={rl_iters or '0'}/{rl_max or '0'}")


def cmd_metrics(args: list[str]) -> None:
    if not args:
        fail("usage: metrics <session-dir>")
    linters.report_metrics(state_file_of(args[0]))


# ---------------------------------------------------------------------------
# phase / gate lifecycle
# ---------------------------------------------------------------------------

def cmd_phase_start(args: list[str]) -> None:
    if not args:
        fail("usage: phase-start <session-dir> <phase>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    force = len(args) > 2 and args[2] == "--force"
    state.require_phase_name(phase)
    if phase in handoffs.DELEGATED_PHASES:
        os.makedirs(os.path.join(directory, "handoffs"), exist_ok=True)
    eng = StateEngine(force)
    eng.begin(directory)
    current = trim(yamlscan.nested_value("phases", phase, "status", eng.records))
    if current == "skipped":
        eng.discard()
        fail(f"phase {phase} is skipped for this track")
    if current in ("pending", "blocked"):
        eng.set_nested_scalar("phases", phase, "status", "in-progress")
    eng.metrics_touch(phase, "start")
    eng.commit()
    print(f"sdd-state: phase-start OK: {phase} (metrics instrumented)")


def cmd_question_round(args: list[str]) -> None:
    if not args:
        fail("usage: question-round <session-dir> <phase>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    state.require_phase_name(phase)
    eng = StateEngine()
    eng.begin(directory)
    eng.metrics_touch(phase, "round")
    eng.commit()
    print(f"sdd-state: question-round OK: {phase}")


def cmd_gate(args: list[str]) -> None:
    if not args:
        fail("usage: gate <session-dir> <phase> <status> --evidence <text>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    if len(args) < 3:
        fail("missing gate status")
    gstatus = args[2]
    rest = args[3:]
    state.require_phase_name(phase)
    if gstatus not in ("pass", "conditional-pass", "fail", "paused"):
        fail(f"invalid gate status: {gstatus}")
    evidence = []
    force = False
    i = 0
    while i < len(rest):
        if rest[i] == "--evidence":
            evidence.append(rest[i + 1]); i += 2
        elif rest[i] == "--force":
            force = True; i += 1
        else:
            fail(f"unknown gate option: {rest[i]}")
    if not evidence:
        fail("gate requires at least one --evidence")

    eng = StateEngine(force)
    eng.begin(directory)
    eng.set_nested_scalar("gates", phase, "status", gstatus)
    for e in evidence:
        eng.append_nested_list_item("gates", phase, "evidence", state.yaml_scalar(e))
    if (
        phase == "spec-verification"
        and gstatus in ("pass", "conditional-pass")
        and any(re.match(r"^  remediation_loop:", line) for line in eng.records)
    ):
        eng.set_nested_scalar("orchestration", "remediation_loop", "iterations", "0")
        eng.set_nested_scalar("orchestration", "remediation_loop", "last_target", "null")
    eng.commit()
    print(f"sdd-state: gate OK: {phase}={gstatus} ({len(evidence)} evidence)")


def cmd_phase_complete(args: list[str]) -> None:
    if not args:
        fail("usage: phase-complete <session-dir> <phase>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    force = len(args) > 2 and args[2] == "--force"
    state.require_phase_name(phase)
    eng = StateEngine(force)
    eng.begin(directory)
    eng.set_nested_scalar("phases", phase, "status", "complete")
    eng.set_nested_scalar("phases", phase, "completed_at", f'"{now_utc()}"')
    eng.metrics_touch(phase, "complete")
    eng.commit()
    print(f"sdd-state: phase-complete OK: {phase}")


def cmd_advance(args: list[str]) -> None:
    if not args:
        fail("usage: advance <session-dir>")
    directory = args[0]
    eng = StateEngine()
    eng.begin(directory)
    track = _records_head(eng.records, r"^track:\s*")
    current = _records_head(eng.records, r"^current_phase:\s*")
    nxt = ""
    seen = False
    for p in yamlscan.session_mandatory_phases(eng.records):
        if seen:
            nxt = p
            break
        if p == current:
            seen = True
    if not seen:
        eng.discard()
        fail(f"current_phase {current} is not in track {track} mandatory phases")
    if not nxt:
        eng.discard()
        fail(f"no phase after {current} for track {track} — use session-complete")
    eng.set_top_scalar("current_phase", nxt)
    eng.commit()
    print(f"sdd-state: advance OK: {current} -> {nxt}")


def _records_head(records: list[str], pattern: str) -> str:
    rx = re.compile(pattern)
    for line in records:
        if rx.match(line):
            return trim(rx.sub("", line, count=1))
    return ""


def cmd_reroute(args: list[str]) -> None:
    if not args:
        fail("usage: reroute <session-dir> <target-phase> --reason <text>")
    directory = args[0]
    if len(args) < 2:
        fail("missing target phase")
    target = args[1]
    rest = args[2:]
    reason = ""
    force = False
    i = 0
    while i < len(rest):
        if rest[i] == "--reason":
            reason = rest[i + 1]; i += 2
        elif rest[i] == "--force":
            force = True; i += 1
        else:
            fail(f"unknown reroute option: {rest[i]}")
    state.require_phase_name(target)
    if target == "bootstrap":
        fail("cannot reroute to bootstrap")
    if not reason:
        fail("reroute requires --reason")

    eng = StateEngine(force)
    eng.begin(directory)
    track = _records_head(eng.records, r"^track:\s*")
    current = _records_head(eng.records, r"^current_phase:\s*")
    current_gate = trim(yamlscan.nested_value("gates", current, "status", eng.records))

    if _pending_delegation_present(eng.records):
        eng.discard()
        fail("reroute blocked: resolve the pending delegation first")
    if current_gate != "fail" and not force:
        eng.discard()
        fail(
            f"reroute requires the current phase gate to be fail (gates.{current}={current_gate}) "
            "— record the failure with gate first, or pass --force"
        )

    if current == "spec-verification" and any(re.match(r"^  remediation_loop:", line) for line in eng.records):
        if target in ("technical-plan", "test-design", "implementation"):
            rl_max = trim(yamlscan.nested_value("orchestration", "remediation_loop", "max_iterations", eng.records))
            rl_iters = trim(yamlscan.nested_value("orchestration", "remediation_loop", "iterations", eng.records))
            rl_max_n = int(rl_max) if re.match(r"^[0-9]+$", rl_max) else 0
            rl_iters_n = int(rl_iters) if re.match(r"^[0-9]+$", rl_iters) else 0
            if rl_iters_n >= rl_max_n:
                if not force:
                    eng.discard()
                    fail(
                        f"remediation loop budget exhausted ({rl_iters_n}/{rl_max_n}) — do not auto-retry; "
                        "escalate to the user (accepted-risk / deferred / manual fix / raise the budget with "
                        "loop-budget), then pass --force only after an explicit decision to continue"
                    )
                rl_max_n = rl_iters_n + 1
                eng.set_nested_scalar("orchestration", "remediation_loop", "max_iterations", str(rl_max_n))
            rl_iters_n += 1
            eng.set_nested_scalar("orchestration", "remediation_loop", "iterations", str(rl_iters_n))
            eng.set_nested_scalar("orchestration", "remediation_loop", "last_target", target)
        else:
            eng.set_nested_scalar("orchestration", "remediation_loop", "iterations", "0")
            eng.set_nested_scalar("orchestration", "remediation_loop", "last_target", "null")

    mandatory = yamlscan.session_mandatory_phases(eng.records)
    ti = ci = -1
    for i, p in enumerate(mandatory):
        if p == target:
            ti = i
        if p == current:
            ci = i
    if ti < 0:
        eng.discard()
        fail(f"target phase {target} is not mandatory for track {track}")
    if ci < 0:
        eng.discard()
        fail(f"current_phase {current} is not in track {track} mandatory phases")
    if not ti < ci:
        eng.discard()
        fail(f"reroute target must precede the current phase ({target} does not precede {current})")

    for i, p in enumerate(mandatory):
        if ti <= i <= ci:
            eng.set_nested_scalar("phases", p, "status", "pending")
            eng.set_nested_scalar("phases", p, "completed_at", "null")
            eng.set_nested_scalar("gates", p, "status", "pending")
    eng.append_nested_list_item(
        "gates", target, "evidence", state.yaml_scalar(f"rerouted: from {current}; {reason}")
    )
    eng.set_top_scalar("current_phase", target)

    ts = now_utc()
    records, found = state.insert_after(
        eng.records,
        r"^decisions:",
        [
            f'  - date: "{ts}"',
            f"    decision: {state.yaml_scalar(f'Rerouted {current} -> {target} for remediation. {reason}')}",
            f"    owner: {state.yaml_scalar('AIDevOrchestrator')}",
        ],
    )
    if not found:
        eng.discard()
        fail("decisions block not found")
    eng.records = records

    eng.commit()
    print(f"sdd-state: reroute OK: {current} -> {target} (phases reset to pending through {current})")
    print_next_action(state_file_of(directory), directory)


def _pending_delegation_present(records: list[str]) -> bool:
    # A pending delegation is active only when orchestration.pending_delegation
    # is a non-null block carrying an agent. Scope the check to that sub-block so
    # sibling orchestration metadata (e.g. workspace_preflight.agent) is ignored.
    return bool(trim(yamlscan.nested_value("orchestration", "pending_delegation", "agent", records)))


def _ensure_remediation_loop_block(eng: StateEngine) -> None:
    if any(re.match(r"^  remediation_loop:", line) for line in eng.records):
        return
    anchor = r"^metrics:" if any(re.match(r"^metrics:", line) for line in eng.records) else r"^decisions:"
    if not any(re.match(anchor, line) for line in eng.records):
        fail("no metrics/decisions anchor found — cannot insert remediation_loop")
    eng.records = state._insert_before(
        eng.records,
        anchor,
        [
            "  remediation_loop:",
            "    max_iterations: 3",
            "    iterations: 0",
            "    last_target: null",
        ],
    )


def cmd_loop_budget(args: list[str]) -> None:
    if not args:
        fail("usage: loop-budget <session-dir> <max-iterations>")
    directory = args[0]
    if len(args) < 2:
        fail("missing max-iterations")
    maxval = args[1]
    force = len(args) > 2 and args[2] == "--force"
    if not re.match(r"^[0-9]+$", maxval):
        fail(f"loop-budget max-iterations must be a non-negative integer: {maxval}")
    eng = StateEngine(force)
    eng.begin(directory)
    _ensure_remediation_loop_block(eng)
    eng.set_nested_scalar("orchestration", "remediation_loop", "max_iterations", maxval)
    eng.commit()
    print(f"sdd-state: loop-budget OK: max_iterations={maxval}")


# ---------------------------------------------------------------------------
# registration commands
# ---------------------------------------------------------------------------

def cmd_artifact_add(args: list[str]) -> None:
    if not args:
        fail("usage: artifact-add <session-dir> <phase> <path>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    if len(args) < 3:
        fail("missing artifact path")
    path = args[2]
    state.require_phase_name(phase)
    if path.startswith("/") or ".." in path:
        fail(f"artifact path must be session-relative without '..': {path}")
    eng = StateEngine()
    eng.begin(directory)
    if eng.nested_list_contains("phases", phase, "artifacts", path):
        eng.discard()
        print(f"sdd-state: artifact-add OK (already registered): {phase} -> {path}")
        return
    eng.append_nested_list_item(
        "phases", phase, "artifacts", state.yaml_scalar(path)
    )
    eng.commit()
    print(f"sdd-state: artifact-add OK: {phase} -> {path}")


def cmd_decision_add(args: list[str]) -> None:
    if not args:
        fail("usage: decision-add <session-dir> --decision <text>")
    directory = args[0]
    rest = args[1:]
    decision = ""
    owner = "AIDevOrchestrator"
    force = False
    i = 0
    while i < len(rest):
        if rest[i] == "--decision":
            decision = rest[i + 1]; i += 2
        elif rest[i] == "--owner":
            owner = rest[i + 1]; i += 2
        elif rest[i] == "--force":
            force = True; i += 1
        else:
            fail(f"unknown decision-add option: {rest[i]}")
    if not decision:
        fail("decision-add requires --decision")
    eng = StateEngine(force)
    eng.begin(directory)
    ts = now_utc()
    records, found = state.insert_after(
        eng.records,
        r"^decisions:",
        [
            f'  - date: "{ts}"',
            f"    decision: {state.yaml_scalar(decision)}",
            f"    owner: {state.yaml_scalar(owner)}",
        ],
    )
    if not found:
        eng.discard()
        fail("decisions block not found")
    eng.records = records
    eng.commit()
    print("sdd-state: decision-add OK")


def cmd_spec_add(args: list[str]) -> None:
    if not args:
        fail("usage: spec-add <session-dir> <path>")
    directory = args[0]
    if len(args) < 2:
        fail("missing spec path")
    path = args[1]
    rest = args[2:]
    scope = "session"
    relation = "primary"
    force = False
    i = 0
    while i < len(rest):
        if rest[i] == "--scope":
            if i + 1 >= len(rest):
                fail("--scope requires a value")
            scope = rest[i + 1]; i += 2
        elif rest[i] == "--relation":
            if i + 1 >= len(rest):
                fail("--relation requires a value")
            relation = rest[i + 1]; i += 2
        elif rest[i] == "--force":
            force = True; i += 1
        else:
            fail(f"unknown spec-add option: {rest[i]}")
    if scope not in ("session", "workspace"):
        fail(f"invalid scope: {scope}")
    if relation not in ("primary", "dependency", "reference"):
        fail(f"invalid relation: {relation}")
    try:
        state.resolve_scoped_path(directory, scope, path)
    except ValueError as err:
        fail(str(err))
    eng = StateEngine(force)
    eng.begin(directory)
    existing_relation = next(
        (
            trim(current_relation)
            for current_path, current_scope, current_relation in yamlscan.parse_state_specs(
                eng.records
            )
            if trim(current_path) == path
            and (trim(current_scope) or "session") == scope
        ),
        None,
    )
    if existing_relation is not None:
        eng.discard()
        if existing_relation != relation:
            fail(
                f"spec already registered with relation {existing_relation}: {scope}:{path}"
            )
        print(f"sdd-state: spec-add OK (already registered): {scope}:{path} ({relation})")
        return
    records, found = _insert_specs_entry(eng.records, path, relation, scope)
    if not found:
        eng.discard()
        fail("specs block not found")
    eng.records = records
    eng.commit()
    print(f"sdd-state: spec-add OK: {scope}:{path} ({relation})")


def _insert_specs_entry(records, path, relation, scope="session"):
    out = []
    done = False
    for line in records:
        if not done and re.match(r"^specs:", line):
            if re.search(r"\[\]\s*$", line):
                out.append("specs:")
            else:
                out.append(line)
            out.append(f'  - path: "{path}"')
            out.append(f"    scope: {scope}")
            out.append(f"    relation: {relation}")
            done = True
            continue
        out.append(line)
    return out, done


def cmd_spec_repoint(args: list[str]) -> None:
    if not args:
        fail("usage: spec-repoint <session-dir> <old-path> <new-path>")
    directory = args[0]
    if len(args) < 2:
        fail("missing old path")
    old = args[1]
    if len(args) < 3:
        fail("missing new path")
    new = args[2]
    old_scope = "session"
    new_scope = ""
    relation = ""
    rest = args[3:]
    i = 0
    while i < len(rest):
        if rest[i] == "--old-scope":
            if i + 1 >= len(rest):
                fail("--old-scope requires a value")
            old_scope = rest[i + 1]; i += 2
        elif rest[i] == "--new-scope":
            if i + 1 >= len(rest):
                fail("--new-scope requires a value")
            new_scope = rest[i + 1]; i += 2
        elif rest[i] == "--relation":
            if i + 1 >= len(rest):
                fail("--relation requires a value")
            relation = rest[i + 1]; i += 2
        else:
            fail(f"unknown spec-repoint option: {rest[i]}")
    new_scope = new_scope or old_scope
    if old_scope not in ("session", "workspace"):
        fail(f"invalid old scope: {old_scope}")
    if new_scope not in ("session", "workspace"):
        fail(f"invalid new scope: {new_scope}")
    if relation and relation not in ("primary", "dependency", "reference"):
        fail(f"invalid relation: {relation}")
    try:
        state.resolve_scoped_path(directory, old_scope, old)
        state.resolve_scoped_path(directory, new_scope, new)
    except ValueError as err:
        fail(str(err))
    eng = StateEngine()
    eng.begin(directory)
    eng.records = _replace_spec_entry(
        eng.records, old_scope, old, new_scope, new, relation
    )
    eng.commit()
    print(
        f"sdd-state: spec-repoint OK: {old_scope}:{old} -> {new_scope}:{new}"
    )


def cmd_pause_handoff(args: list[str]) -> None:
    if not args:
        fail("usage: pause-handoff <session-dir> <phase> <agent> <delegation-id> <envelope-path>")
    directory = args[0]
    if len(args) < 2:
        fail("missing phase")
    phase = args[1]
    if len(args) < 3:
        fail("missing agent")
    agent = args[2]
    if len(args) < 4:
        fail("missing delegation id")
    delegation_id = args[3]
    if len(args) < 5:
        fail("missing envelope path")
    envelope = args[4]
    rest = args[5:]
    round_val = ""
    force = False
    i = 0
    while i < len(rest):
        if rest[i] == "--round":
            round_val = rest[i + 1]; i += 2
        elif rest[i] == "--force":
            force = True; i += 1
        else:
            fail(f"unknown pause-handoff option: {rest[i]}")
    state.require_phase_name(phase)
    if phase not in handoffs.DELEGATED_PHASES:
        fail(f"pause-handoff phase is not delegated: {phase}")
    try:
        expected_agent = handoffs.expected_agent(phase)
    except ValueError as err:
        fail(str(err))
    if agent != expected_agent:
        fail(f"pause-handoff agent must be {expected_agent} for {phase}")

    workspace = state.workspace_root_of_session(directory)
    if os.path.isabs(envelope):
        envelope_path = os.path.abspath(envelope)
    elif envelope.startswith(".aicontext/"):
        envelope_path = os.path.abspath(os.path.join(workspace, envelope))
    else:
        envelope_path = os.path.abspath(os.path.join(directory, envelope))
    session_path = os.path.abspath(directory)
    delegation_path = os.path.realpath(os.path.join(directory, "delegations"))
    resolved_envelope = os.path.realpath(envelope_path)
    try:
        lexical_session_contained = os.path.commonpath((session_path, envelope_path)) == session_path
        delegation_contained = os.path.commonpath((os.path.realpath(directory), delegation_path)) == os.path.realpath(directory)
        envelope_contained = os.path.commonpath((delegation_path, resolved_envelope)) == delegation_path
    except ValueError:
        lexical_session_contained = delegation_contained = envelope_contained = False
    if (
        not lexical_session_contained
        or not delegation_contained
        or not envelope_contained
        or not os.path.isfile(resolved_envelope)
    ):
        fail("handoff envelope must be an existing file inside session delegations/")
    envelope = handoff_tool._workspace_relative(directory, envelope_path)

    eng = StateEngine(force)
    eng.begin(directory)
    current = _records_head(eng.records, r"^current_phase:\s*")
    if current != phase:
        eng.discard()
        fail(f"pending_delegation.phase must equal current_phase ({current})")
    phase_status = trim(yamlscan.nested_value("phases", phase, "status", eng.records))
    gate_status = trim(yamlscan.nested_value("gates", phase, "status", eng.records))
    if phase_status != "in-progress" or gate_status != "pending":
        eng.discard()
        fail(
            f"pause-handoff requires {phase} phase=in-progress and gate=pending "
            f"(got phase={phase_status or 'unset'}, gate={gate_status or 'unset'})"
        )
    if yamlscan.pending_delegation_active(eng.records):
        eng.discard()
        fail("resume the current pending delegation before registering another question envelope")
    try:
        handoff_tool.validate_question_envelope(
            resolved_envelope,
            expected_agent,
            phase,
            delegation_id,
        )
    except ToolError:
        eng.discard()
        raise
    if not round_val:
        prior_rounds = [
            int(match.group(1))
            for line in eng.records
            if (
                match := re.search(
                    rf"pending delegation {re.escape(delegation_id)} \(round ([0-9]+)\)",
                    line,
                )
            )
        ]
        round_val = str(max(prior_rounds, default=0) + 1)

    eng.records = replace_orchestration_subblock(
        eng.records,
        r"^  pending_delegation:",
        [
            "  pending_delegation:",
            f"    round: {round_val}",
            f'    delegation_id: "{delegation_id}"',
            f"    agent: {agent}",
            f"    phase: {phase}",
            f"    envelope_artifact_path: {envelope}",
        ],
    )
    eng.set_nested_scalar("phases", phase, "status", "blocked")
    eng.set_nested_scalar("gates", phase, "status", "paused")
    eng.append_nested_list_item("gates", phase, "evidence", f'"paused: pending delegation {delegation_id} (round {round_val})"')
    eng.metrics_touch(phase, "round")
    eng.commit()
    print(f"sdd-state: pause-handoff OK: {phase} blocked on {agent} (round {round_val})")


def _reactivate_pending_delegation(engine: StateEngine, phase: str) -> None:
    engine.records = replace_orchestration_subblock(
        engine.records,
        r"^  pending_delegation:",
        ["  pending_delegation: null"],
    )
    engine.set_nested_scalar("phases", phase, "status", "in-progress")
    engine.set_nested_scalar("gates", phase, "status", "pending")


def _parse_handoff_request_options(args: list[str], action: str):
    if not args:
        fail(f"usage: {action} <session-dir> --expect-phase <phase>")
    directory = args[0]
    phase = need = ""
    contexts: list[list[str]] = []
    policies: list[list[str]] = []
    rest = args[1:]
    index = 0
    while index < len(rest):
        option = rest[index]
        if option == "--expect-phase" and index + 1 < len(rest):
            phase = rest[index + 1]; index += 2
        elif option == "--need" and index + 1 < len(rest):
            need = rest[index + 1]; index += 2
        elif option == "--context" and index + 2 < len(rest):
            contexts.append([rest[index + 1], rest[index + 2]]); index += 3
        elif option == "--policy" and index + 2 < len(rest):
            policies.append([rest[index + 1], rest[index + 2]]); index += 3
        else:
            fail(f"unknown or incomplete {action} option: {option}")
    if not phase:
        fail(f"{action} requires --expect-phase")
    return directory, phase, need, contexts, policies


def cmd_create_handoff(args: list[str]) -> None:
    directory, phase, need, contexts, policies = _parse_handoff_request_options(
        args, "create-handoff"
    )
    request = handoff_tool.create_request(directory, phase, need, contexts, policies)
    print(
        f"Read and execute the complete delegation at {request}. "
        "Return exactly the response required there."
    )


def cmd_resume_handoff(args: list[str]) -> None:
    if not args:
        fail("usage: resume-handoff <session-dir> --expect-phase <phase> --answer <id> <selected|none> <answer>")
    directory = args[0]
    phase = ""
    answers: list[list[str]] = []
    rest = args[1:]
    index = 0
    while index < len(rest):
        option = rest[index]
        if option == "--expect-phase" and index + 1 < len(rest):
            phase = rest[index + 1]; index += 2
        elif option == "--answer" and index + 3 < len(rest):
            answers.append([rest[index + 1], rest[index + 2], rest[index + 3]]); index += 4
        else:
            fail(f"unknown or incomplete resume-handoff option: {option}")
    if not phase:
        fail("resume-handoff requires --expect-phase")

    request_path, content, envelope = handoff_tool.build_resumed_request(
        directory, phase, answers
    )
    staged_request = handoff_tool.stage_request(request_path, content)
    stale_manifest = os.path.join(directory, "handoffs", f"{phase}-handoff.yml")
    candidate = transaction.create_candidate_session(directory)
    try:
        engine = StateEngine()
        engine.begin(candidate)
        _reactivate_pending_delegation(engine, phase)
        engine.commit()
        transaction.commit_candidate(
            directory,
            candidate,
            delete_paths=tuple(path for path in (envelope, stale_manifest) if os.path.isfile(path)),
            write_paths=((request_path, staged_request),),
        )
        staged_request = ""
    finally:
        shutil.rmtree(candidate, ignore_errors=True)
        if staged_request and os.path.exists(staged_request):
            os.remove(staged_request)
    request = handoff_tool._workspace_relative(directory, request_path)
    print(
        f"Read and execute the complete delegation at {request}. "
        "Return exactly the response required there."
    )


def cmd_retry_handoff(args: list[str]) -> None:
    if not args:
        fail("usage: retry-handoff <session-dir> --expect-phase <phase> --finding <text> [--finding <text> ...]")
    directory = args[0]
    phase = ""
    findings: list[str] = []
    rest = args[1:]
    index = 0
    while index < len(rest):
        option = rest[index]
        if option == "--expect-phase" and index + 1 < len(rest):
            phase = rest[index + 1]; index += 2
        elif option == "--finding" and index + 1 < len(rest):
            findings.append(rest[index + 1]); index += 2
        else:
            fail(f"unknown or incomplete retry-handoff option: {option}")
    if not phase:
        fail("retry-handoff requires --expect-phase")

    request_path, request_content, base_path, base_content = handoff_tool.build_retry_request(
        directory, phase, findings
    )
    staged_request = staged_base = ""
    candidate = ""
    try:
        staged_request = handoff_tool.stage_request(request_path, request_content)
        staged_base = handoff_tool.stage_request(base_path, base_content)
        stale_manifest = os.path.join(directory, "handoffs", f"{phase}-handoff.yml")
        candidate = transaction.create_candidate_session(directory)
        transaction.commit_candidate(
            directory,
            candidate,
            delete_paths=(stale_manifest,) if os.path.isfile(stale_manifest) else (),
            write_paths=((request_path, staged_request), (base_path, staged_base)),
        )
        staged_request = staged_base = ""
    finally:
        if candidate:
            shutil.rmtree(candidate, ignore_errors=True)
        if staged_request and os.path.exists(staged_request):
            os.remove(staged_request)
        if staged_base and os.path.exists(staged_base):
            os.remove(staged_base)
    request = handoff_tool._workspace_relative(directory, request_path)
    print(
        f"Read and execute the complete delegation at {request}. "
        "Return exactly the response required there."
    )


def cmd_submit_handoff(args: list[str]) -> None:
    if not args:
        fail("usage: submit-handoff <session-dir> --expect-phase <phase> --status <ready|blocked>")
    directory = args[0]
    values = {
        "session": directory,
        "expect_phase": "",
        "status": "",
        "artifact": [],
        "spec": [],
        "replace_spec": [],
        "contract_map": [],
        "remove_spec": [],
        "delete_spec": [],
        "blocker": [],
    }
    arities = {
        "--expect-phase": ("expect_phase", 1),
        "--status": ("status", 1),
        "--artifact": ("artifact", 4),
        "--spec": ("spec", 4),
        "--replace-spec": ("replace_spec", 3),
        "--contract-map": ("contract_map", 3),
        "--remove-spec": ("remove_spec", 2),
        "--delete-spec": ("delete_spec", 3),
        "--blocker": ("blocker", 2),
    }
    rest = args[1:]
    index = 0
    while index < len(rest):
        option = rest[index]
        if option not in arities:
            fail(f"unknown submit-handoff option: {option}")
        key, arity = arities[option]
        if index + arity >= len(rest):
            fail(f"{option} requires {arity} value(s)")
        raw = rest[index + 1:index + arity + 1]
        if isinstance(values[key], list):
            values[key].append(raw)
        else:
            values[key] = raw[0]
        index += arity + 1
    if not values["expect_phase"]:
        fail("submit-handoff requires --expect-phase")
    if values["status"] not in ("ready", "blocked"):
        fail("submit-handoff requires --status ready|blocked")

    class SubmitArgs:
        pass

    submitted = SubmitArgs()
    for key, value in values.items():
        setattr(submitted, key, value)
    manifest = handoff_tool.submit_manifest(submitted)
    print(f"My handoff is in: {manifest}")


def cmd_contract_add(args: list[str]) -> None:
    if not args:
        fail("usage: contract-add <session-dir> <file> --title <text>")
    directory = args[0]
    if len(args) < 2:
        fail("missing contract file path")
    file_path = args[1]
    rest = args[2:]
    title = summary = media_type = cid = ""
    source_desc = "user-provided"
    force = False
    i = 0
    while i < len(rest):
        opt = rest[i]
        if opt == "--title":
            title = rest[i + 1]; i += 2
        elif opt == "--source":
            source_desc = rest[i + 1]; i += 2
        elif opt == "--summary":
            summary = rest[i + 1]; i += 2
        elif opt == "--media-type":
            media_type = rest[i + 1]; i += 2
        elif opt == "--id":
            cid = rest[i + 1]; i += 2
        elif opt == "--force":
            force = True; i += 1
        else:
            fail(f"unknown contract-add option: {opt}")
    if not title:
        fail("contract-add requires --title")

    sdir = directory.rstrip("/")
    contracts_file = os.path.join(sdir, "contracts.yml")
    state_file_of(directory)

    base = os.path.basename(file_path)
    prefix = sdir + "/contracts/"
    if file_path.startswith(prefix):
        rel = "contracts/" + file_path[len(prefix):]
    else:
        if not os.path.isfile(file_path):
            fail(f"contract file not found: {file_path}")
        os.makedirs(os.path.join(sdir, "contracts"), exist_ok=True)
        import shutil

        shutil.copy(file_path, os.path.join(sdir, "contracts", base))
        rel = "contracts/" + base
    if not os.path.isfile(os.path.join(sdir, rel)):
        fail(f"contract file not found: {sdir}/{rel}")
    sha = sha256_of(os.path.join(sdir, rel))
    ts = now_utc()
    if not cid:
        slug = re.sub(r"[^a-zA-Z0-9]", "-", base).lower()
        slug = re.sub(r"-+", "-", slug)
        slug = re.sub(r"^-|-$", "", slug)
        cid = "CON-" + slug
    if not media_type:
        ext = base.rsplit(".", 1)[-1] if "." in base else ""
        lower = base.lower()
        if lower.endswith((".png", ".jpg", ".jpeg", ".gif")):
            media_type = f"image/{ext}"
        elif lower.endswith(".pdf"):
            media_type = "application/pdf"
        elif lower.endswith((".yaml", ".yml")):
            media_type = "application/yaml"
        elif lower.endswith(".json"):
            media_type = "application/json"
        elif lower.endswith(".md"):
            media_type = "text/markdown"
        else:
            media_type = "application/octet-stream"

    if not os.path.isfile(contracts_file):
        template = os.path.join(ASSETS_DIR, "contracts-template.yml")
        if not os.path.isfile(template):
            fail("contracts template not found")
        import shutil

        shutil.copy(template, contracts_file)

    manifest = read_records(contracts_file)
    if any(re.match(r"^  - id: " + re.escape(cid) + r"$", line) for line in manifest):
        fail(f"contract id already exists: {cid}")
    entry = [
        f"  - id: {cid}",
        f'    title: "{title}"',
        f"    path: {rel}",
        f"    media_type: {media_type}",
        f"    sha256: {sha}",
        f'    source: "{source_desc}"',
        f'    captured_at: "{ts}"',
        "    links: []",
        f'    summary: "{summary}"',
        "    metadata: {}",
    ]
    out = []
    done = False
    for line in manifest:
        if not done and re.match(r"^contracts:", line):
            if re.search(r"\[\]\s*$", line):
                out.append("contracts:")
            else:
                out.append(line)
            out.extend(entry)
            done = True
            continue
        out.append(line)
    if not done:
        fail("contracts: block not found in manifest")
    state.write_records(contracts_file, out)

    eng = StateEngine(force)
    eng.begin(directory)
    if not eng.nested_list_contains("phases", "bootstrap", "artifacts", "contracts.yml"):
        eng.append_nested_list_item("phases", "bootstrap", "artifacts", "contracts.yml")
    eng.commit()

    print(f"sdd-state: contract-add OK: {cid} ({rel}, sha256={sha[:12]}...)")


# ---------------------------------------------------------------------------
# validation commands
# ---------------------------------------------------------------------------

def _layout_probe(directory: str) -> tuple[int, list[str]]:
    state_file_of(directory)
    sdd_root = os.path.abspath(os.path.join(directory.rstrip("/"), "..", ".."))
    names = os.listdir(sdd_root)
    visible = sorted(n for n in names if not n.startswith("."))
    hidden = sorted(n for n in names if n.startswith(".") and len(n) > 1 and n[1] != ".")
    signals = []
    for name in visible + hidden:
        if name in ("specs", "sessions"):
            continue
        signals.append(name)
    if not signals:
        return 0, [f"sdd-state: layout-probe OK: layout=clean root={sdd_root}"]
    return 2, [
        f"sdd-state: layout-probe LEGACY: layout=legacy root={sdd_root} signals={','.join(signals)}",
        "sdd-state: next: dispatch the migration subagent per "
        "<agent-dir>/skills/aidev-sdd/references/sdd-layout-migration.md",
    ]


def cmd_layout_probe(args: list[str]) -> None:
    if not args:
        fail("usage: layout-probe <session-dir>")
    rc, out = _layout_probe(args[0])
    for line in out:
        print(line)
    if rc != 0:
        raise ToolError(None, rc)


def cmd_preflight(args: list[str]) -> None:
    if not args:
        fail("usage: preflight <session-dir> [--workspace <root>] [--validator <path>] [--allow-no-repos]")
    directory = args[0]
    rest = args[1:]
    workspace = os.getcwd()
    allow_no_repos = False
    validator = ""
    force = False
    i = 0
    while i < len(rest):
        opt = rest[i]
        if opt == "--workspace":
            if i + 1 >= len(rest):
                fail("--workspace requires a value")
            workspace = rest[i + 1]; i += 2
        elif opt == "--validator":
            if i + 1 >= len(rest):
                fail("--validator requires a value")
            validator = rest[i + 1]; i += 2
        elif opt == "--allow-no-repos":
            allow_no_repos = True; i += 1
        elif opt == "--force":
            force = True; i += 1
        else:
            fail(f"unknown preflight option: {opt}")
    if not os.path.isdir(workspace):
        fail(f"workspace root not found: {workspace}")
    workspace = os.path.abspath(workspace)
    if validator and not os.path.isfile(validator):
        fail(f"guidance validator not found: {validator}")

    pf_status = "ready"
    summary = ""
    validator_rc = 0
    checked: list[str] = []
    passed_repos: list[str] = []
    blocked_entries: list[str] = []

    probe_rc, probe_out = _layout_probe(directory)
    if probe_rc == 2:
        probe_signals = probe_out[0]
        probe_signals = probe_signals.split("signals=", 1)[-1]
        pf_status = "blocked"
        summary = f"legacy sdd layout detected ({probe_signals}); run the layout migration before preflight"
    elif not _has_repos(workspace):
        if allow_no_repos:
            pf_status = "ready"
            summary = "no repositories under repos/; allowed by --allow-no-repos"
        else:
            pf_status = "blocked"
            summary = f"no repositories found under {workspace}/repos"
    elif not validator:
        pf_status = "blocked"
        summary = (
            "repositories exist but no guidance validator was provided; pass --validator <path> "
            "(aidev-explore ships the standard one)"
        )
    else:
        proc = subprocess.run(
            [validator, "--workspace", workspace],
            capture_output=True, text=True,
        )
        validator_rc = proc.returncode
        validator_output = proc.stdout + proc.stderr

        current_fail = ""
        fail_sections = ""

        def flush_fail():
            nonlocal current_fail, fail_sections
            if current_fail:
                reason = fail_sections
                if reason.startswith(", "):
                    reason = reason[2:]
                blocked_entries.append(f"{current_fail}|guidance validation failed: {reason}")
                current_fail = ""
                fail_sections = ""

        for line in validator_output.split("\n"):
            if line.startswith("PASS "):
                flush_fail()
                repo = line[len("PASS "):]
                checked.append(repo)
                passed_repos.append(repo)
            elif line.startswith("FAIL "):
                flush_fail()
                repo = line[len("FAIL "):]
                checked.append(repo)
                current_fail = repo
            elif line.startswith(" "):
                if current_fail and re.match(r"^ [A-Z][A-Za-z0-9._-]*$", line):
                    fail_sections += ", " + line[1:]
            elif "summary:" in line:
                flush_fail()
                summary = line.split("summary: ", 1)[-1]
        flush_fail()
        if blocked_entries or validator_rc != 0:
            pf_status = "blocked"
            if not summary:
                summary = f"validator exited with code {validator_rc}"
        if not summary:
            summary = f"total={len(checked)} passed={len(passed_repos)} failed=0"

    block = ["  workspace_preflight:", f"    status: {pf_status}", "    agent: sdd-state-cli",
             f'    completed_at: "{now_utc()}"', f'    workspace_root: "{workspace}"']
    if not checked:
        block.append("    repos_checked: []")
        block.append("    already_initialized_repos: []")
    else:
        block.append("    repos_checked:")
        for r in checked:
            block.append(f"      - {r}")
        if not passed_repos:
            block.append("    already_initialized_repos: []")
        else:
            block.append("    already_initialized_repos:")
            for r in passed_repos:
                block.append(f"      - {r}")
    block.append("    newly_initialized_repos: []")
    if not blocked_entries:
        block.append("    blocked_repos: []")
    else:
        block.append("    blocked_repos:")
        for entry in blocked_entries:
            repo, _, reason = entry.partition("|")
            block.append(f"      - repo: {repo}")
            block.append(f'        reason: "{reason}"')
    block.append(f'    validation_summary: "{summary}"')

    eng = StateEngine(force)
    eng.begin(directory)
    eng.records = replace_orchestration_subblock(eng.records, r"^  workspace_preflight:", block)
    eng.commit()

    if pf_status == "ready":
        print(f"sdd-state: preflight OK: ready ({summary})")
    else:
        print(f"sdd-state: preflight BLOCKED: {summary}")
        for entry in blocked_entries:
            repo, _, reason = entry.partition("|")
            print(f"sdd-state:   blocked: {repo} — {reason}")
        if summary.startswith("legacy sdd layout"):
            print(
                "sdd-state: next: dispatch the migration subagent per "
                "<agent-dir>/skills/aidev-sdd/references/sdd-layout-migration.md, then re-run preflight"
            )
        else:
            print("sdd-state: next: delegate AIDevInit with the blocked repositories, then re-run preflight")
        raise ToolError(None, 1)


def _has_repos(workspace: str) -> bool:
    repos = os.path.join(workspace, "repos")
    if not os.path.isdir(repos):
        return False
    return any(os.path.isdir(os.path.join(repos, e)) for e in os.listdir(repos))


def cmd_gate_check(args: list[str]) -> None:
    if not args:
        fail("usage: gate-check <session-dir> [--phase <phase>]")
    directory = args[0]
    rest = args[1:]
    phase = ""
    i = 0
    while i < len(rest):
        if rest[i] == "--phase":
            phase = rest[i + 1]; i += 2
        else:
            fail(f"unknown gate-check option: {rest[i]}")
    file = state_file_of(directory)
    sdir = directory.rstrip("/")
    records = text.read_lines(file)
    if not phase:
        phase = _head(r"current_phase:[[:space:]]*", file)
    state.require_phase_name(phase)

    rc = [0]

    def run_gate_check(label, func, *fargs):
        ok, out = state.capture_lint(func, *fargs)
        if ok:
            print(f"sdd-state: gate-check PASS: {label}")
        else:
            err = out
            if err.startswith("sdd-lint: "):
                err = err[len("sdd-lint: "):]
            firstline = err.split("\n", 1)[0]
            print(f"sdd-state: gate-check FAIL: {label} — {firstline}")
            rc[0] = 1

    def artifact_path(owner_phase, basename, label, required=True):
        stored = yamlscan.phase_artifact_value(owner_phase, basename, records)
        if not stored and os.path.isfile(os.path.join(sdir, basename)):
            stored = basename
        if not stored:
            if required:
                print(f"sdd-state: gate-check FAIL: {label} — artifact not registered: {basename}")
                rc[0] = 1
            return ""
        try:
            resolved = state.resolve_state_artifact(sdir, stored)
        except ValueError as err:
            print(f"sdd-state: gate-check FAIL: {label} — {err}")
            rc[0] = 1
            return ""
        if not os.path.isfile(resolved):
            print(f"sdd-state: gate-check FAIL: {label} — artifact not found: {stored}")
            rc[0] = 1
            return ""
        return resolved

    print(f"sdd-state: gate-check for phase={phase}")

    run_gate_check("session", linters.lint_session_state, file)

    if phase == "discovery":
        artifact = artifact_path("discovery", "research.md", "research artifact")
        if artifact:
            run_gate_check("research", linters.lint_research, artifact)
    elif phase in ("functional-spec", "spec-validation"):
        had_spec = False
        for spec_path, spec_scope, _relation in yamlscan.parse_state_specs(records):
            spec_path = trim(spec_path)
            spec_scope = trim(spec_scope) or "session"
            if not spec_path:
                continue
            had_spec = True
            try:
                resolved_spec = state.resolve_scoped_path(sdir, spec_scope, spec_path)
            except ValueError as err:
                print(f"sdd-state: gate-check FAIL: spec-package {spec_path} — {err}")
                rc[0] = 1
                continue
            if os.path.isfile(resolved_spec):
                run_gate_check(
                    f"spec-package {spec_scope}:{spec_path}",
                    linters.lint_spec_package,
                    resolved_spec,
                )
            else:
                print(
                    f"sdd-state: gate-check FAIL: spec-package {spec_scope}:{spec_path} "
                    f"— artifact not found"
                )
                rc[0] = 1
        if not had_spec:
            print("sdd-state: gate-check FAIL: spec-package — no approved specs listed in sdd-state.yml")
            rc[0] = 1
        backlog = artifact_path(
            "functional-spec", "backlog-plan.yml", "backlog artifact", required=False
        )
        if backlog:
            run_gate_check("backlog", linters.lint_backlog, backlog)
        if phase == "spec-validation":
            trace_file = artifact_path("bootstrap", "trace.md", "trace-gate")
            if trace_file:
                run_gate_check("trace-gate", linters.lint_trace_gate, trace_file, phase)
            run_gate_check("coverage", linters.lint_coverage, sdir + "/")
        else:
            trace_file = artifact_path("bootstrap", "trace.md", "trace-gate", required=False)
            if trace_file:
                run_gate_check("trace-gate", linters.lint_trace_gate, trace_file, phase)
    elif phase == "technical-plan":
        artifact = artifact_path("technical-plan", "tech-plan.md", "tech-plan artifact")
        if artifact:
            run_gate_check("tech-plan", linters.lint_tech_plan, artifact)
        run_gate_check("coverage", linters.lint_coverage, sdir + "/")
    elif phase == "test-design":
        artifact = artifact_path("test-design", "test-plan.md", "test-plan artifact")
        if artifact:
            run_gate_check("test-plan", linters.lint_test_plan, artifact)
        run_gate_check("coverage", linters.lint_coverage, sdir + "/")
        trace_file = artifact_path("bootstrap", "trace.md", "trace-gate", required=False)
        if trace_file:
            run_gate_check("trace-gate", linters.lint_trace_gate, trace_file, phase)
    elif phase == "implementation":
        artifact = artifact_path("implementation", "code.md", "code journal")
        if artifact:
            run_gate_check("code", linters.lint_code, artifact)
        run_gate_check("coverage", linters.lint_coverage, sdir + "/")
        trace_file = artifact_path("bootstrap", "trace.md", "trace-gate", required=False)
        if trace_file:
            run_gate_check("trace-gate", linters.lint_trace_gate, trace_file, phase)
    elif phase == "spec-verification":
        artifact = artifact_path(
            "spec-verification", "verification.md", "verification artifact"
        )
        if artifact:
            run_gate_check("verification", linters.lint_verification, artifact)
        run_gate_check("coverage", linters.lint_coverage, sdir + "/")
        trace_file = artifact_path("bootstrap", "trace.md", "trace-gate")
        if trace_file:
            run_gate_check("trace-gate", linters.lint_trace_gate, trace_file, phase)
    elif phase == "retro":
        artifact = artifact_path("retro", "retro.md", "retro artifact")
        if artifact:
            run_gate_check("retro", linters.lint_retro, artifact)
    elif phase == "bootstrap":
        trace_file = artifact_path("bootstrap", "trace.md", "trace", required=False)
        if trace_file:
            run_gate_check("trace", linters.lint_trace, trace_file)
        contracts = artifact_path(
            "bootstrap", "contracts.yml", "contracts artifact", required=False
        )
        if contracts:
            run_gate_check("contracts", linters.lint_contracts, contracts)

    if phases.phase_order(phase) >= phases.phase_order("functional-spec"):
        contracts = artifact_path(
            "bootstrap", "contracts.yml", "contracts artifact", required=False
        )
        if contracts:
            run_gate_check("contracts", linters.lint_contracts, contracts)
            trace_file = artifact_path("bootstrap", "trace.md", "contract trace")
            if trace_file:
                run_gate_check(
                    "contract-trace",
                    linters.lint_contract_trace,
                    contracts,
                    trace_file,
                )

    if rc[0] == 0:
        print(f"sdd-state: gate-check OK: phase={phase} — all checks passed")
    else:
        print(f"sdd-state: gate-check FAILED: phase={phase} — fix the findings above before advancing")
        raise ToolError(None, 1)


# ---------------------------------------------------------------------------
# routing / handoff
# ---------------------------------------------------------------------------

def print_next_action(file: str, directory: str) -> None:
    sdir = directory.rstrip("/")
    lines = text.read_lines(file)
    sstatus = _head(r"status:[[:space:]]*", file)
    track = _head(r"track:[[:space:]]*", file)
    current = _head(r"current_phase:[[:space:]]*", file)
    gate_status = trim(yamlscan.nested_value("gates", current, "status", lines))
    exec_mode = execution_mode_of(file)

    print(
        f"sdd-state: where: session={sstatus or 'unknown'} track={track or 'unknown'} "
        f"current_phase={current or 'unknown'} gate={gate_status or 'unknown'} execution_mode={exec_mode}"
    )

    if sstatus == "complete":
        print("sdd-state: next: session is complete — nothing to do")
        return

    pending_agent = yamlscan.pending_delegation_value("agent", lines)
    pending_phase = yamlscan.pending_delegation_value("phase", lines)
    if pending_agent:
        print(
            f"sdd-state: next: resolve the pending delegation — ask the user the envelope questions, "
            f"then resume {trim(pending_agent)} for {trim(pending_phase)} according to the delegated question protocol "
            "with resume-handoff before re-entering the specialist"
        )
        return

    phase_status = trim(yamlscan.nested_value("phases", current, "status", lines))

    if gate_status in ("pass", "conditional-pass"):
        if phase_status != "complete":
            print(f"sdd-state: next: gate already {gate_status} — run phase-complete {current}, then advance")
        else:
            last_mandatory = ""
            for p in yamlscan.session_mandatory_phases(lines):
                last_mandatory = p
            if current == last_mandatory:
                print("sdd-state: next: last mandatory phase is complete — run session-complete")
            elif exec_mode == "autopilot":
                print(
                    "sdd-state: next: phase complete — run advance, then phase-start + delegate the next "
                    "phase (autopilot: chain unattended)"
                )
            else:
                print(
                    "sdd-state: next: phase complete — run advance, report to the user, and confirm before "
                    "delegating the next phase (interactive: no unattended chaining)"
                )
    elif gate_status == "pending":
        if phase_status == "in-progress":
            print(
                f"sdd-state: next: phase {current} is in progress — collect the specialist handoff, "
                "run gate-check, then accept-handoff"
            )
        else:
            print(f"sdd-state: next: delegate phase {current} to its owner (phase-start first)")
    elif gate_status == "paused":
        print("sdd-state: next: gate is paused — resolve the pending delegation before anything else")
    elif gate_status == "fail":
        if current == "spec-verification" and text.grep_q(r"^  remediation_loop:", file):
            rl_max = trim(yamlscan.nested_value("orchestration", "remediation_loop", "max_iterations", lines))
            rl_iters = trim(yamlscan.nested_value("orchestration", "remediation_loop", "iterations", lines))
            rl_max_n = int(rl_max) if re.match(r"^[0-9]+$", rl_max) else 0
            rl_iters_n = int(rl_iters) if re.match(r"^[0-9]+$", rl_iters) else 0
            if rl_iters_n >= rl_max_n:
                if exec_mode == "autopilot":
                    print(
                        f"sdd-state: next: spec-verification failed and the remediation loop budget is "
                        f"exhausted ({rl_iters_n}/{rl_max_n}) — stop the loop, record a blocker, and report to "
                        "the user; autopilot must not fabricate an accepted-risk. Options: accepted-risk / "
                        f"deferred / manual fix / raise the budget with loop-budget {sdir} <n>"
                    )
                else:
                    print(
                        f"sdd-state: next: spec-verification failed and the remediation loop budget is "
                        f"exhausted ({rl_iters_n}/{rl_max_n}) — stop and ask the user through the native "
                        "mechanism. Options: accepted-risk / deferred / manual fix / raise the budget with "
                        f"loop-budget {sdir} <n>"
                    )
            else:
                print(
                    f"sdd-state: next: spec-verification failed — remediation loop iteration "
                    f"{rl_iters_n + 1}/{rl_max_n}: classify the root cause, run reroute {sdir} "
                    '<implementation|technical-plan> --reason "..." and re-delegate passing only the failing '
                    "ACs/findings. Runs unattended within budget in both modes"
                )
        else:
            print(
                f"sdd-state: next: gate failed — run reroute {sdir} <target-phase> --reason \"...\" to route "
                "remediation to the owning phase, then phase-start + re-delegate"
            )
    else:
        print(
            f"sdd-state: next: inspect the session — gate status {gate_status or 'unset'} for {current} "
            "is not mechanically routable"
        )


def cmd_next(args: list[str]) -> None:
    if not args:
        fail("usage: next <session-dir>")
    directory = args[0]
    file = state_file_of(directory)
    print_next_action(file, directory)


def _parse_handoff_options(args: list[str], accepting: bool):
    action = "accept-handoff" if accepting else "validate-handoff"
    if not args:
        fail(f"usage: {action} <session-dir> --file <manifest.yml>")
    directory = args[0]
    manifest = gstatus = ""
    evidence: list[str] = []
    chain = False
    rest = args[1:]
    i = 0
    while i < len(rest):
        option = rest[i]
        if option == "--file":
            if i + 1 >= len(rest):
                fail("--file requires a value")
            manifest = rest[i + 1]; i += 2
        elif accepting and option == "--gate":
            if i + 1 >= len(rest):
                fail("--gate requires a value")
            gstatus = rest[i + 1]; i += 2
        elif accepting and option == "--evidence":
            if i + 1 >= len(rest):
                fail("--evidence requires a value")
            evidence.append(rest[i + 1]); i += 2
        elif accepting and option == "--chain":
            chain = True; i += 1
        else:
            fail(f"unknown {action} option: {option}")
    if not manifest:
        fail(f"{action} requires --file <manifest.yml>")
    if not os.path.isabs(manifest):
        manifest = os.path.join(state.workspace_root_of_session(directory), manifest)
    if accepting:
        if gstatus not in ("pass", "conditional-pass"):
            fail("accept-handoff requires --gate pass|conditional-pass")
        if not evidence:
            evidence = [f"accepted handoff manifest: {os.path.basename(manifest)}"]
    return directory, manifest, gstatus, evidence, chain


def _spec_entry_exists(records, scope, path):
    return any(
        trim(current_path) == path and (trim(current_scope) or "session") == scope
        for current_path, current_scope, _relation in yamlscan.parse_state_specs(records)
    )


def _replace_spec_entry(records, old_scope, old_path, new_scope, new_path, relation):
    parsed = [
        (trim(path), trim(scope) or "session", trim(current_relation))
        for path, scope, current_relation in yamlscan.parse_state_specs(records)
    ]
    match_count = sum(
        path == old_path and scope == old_scope for path, scope, _relation in parsed
    )
    if match_count == 0:
        fail(f"spec replacement target not found: {old_scope}:{old_path}")
    if match_count > 1:
        fail(f"spec replacement target is duplicated: {old_scope}:{old_path}")
    if (old_scope, old_path) != (new_scope, new_path) and any(
        path == new_path and scope == new_scope for path, scope, _relation in parsed
    ):
        fail(f"spec replacement target already exists: {new_scope}:{new_path}")

    for start, end, path, scope, current_relation in _spec_entry_ranges(records):
        if path != old_path or scope != old_scope:
            continue
        replacement = _rewrite_spec_entry(
            records[start:end],
            new_scope,
            new_path,
            relation or current_relation,
        )
        return records[:start] + replacement + records[end:]
    fail(f"spec replacement target not found: {old_scope}:{old_path}")


def _remove_spec_entry(records, scope, path):
    parsed = [
        (trim(item_path), trim(item_scope) or "session", trim(relation))
        for item_path, item_scope, relation in yamlscan.parse_state_specs(records)
    ]
    match_count = sum(
        item_path == path and item_scope == scope
        for item_path, item_scope, _relation in parsed
    )
    if match_count == 0:
        fail(f"spec removal target not found: {scope}:{path}")
    if match_count > 1:
        fail(f"spec removal target is duplicated: {scope}:{path}")
    for start, end, item_path, item_scope, _relation in _spec_entry_ranges(records):
        if item_path == path and item_scope == scope:
            updated = records[:start] + records[end:]
            if not yamlscan.parse_state_specs(updated):
                updated = [
                    "specs: []" if line.startswith("specs:") else line
                    for line in updated
                ]
            return updated
    fail(f"spec removal target not found: {scope}:{path}")


def _spec_entry_ranges(records):
    start = next((i for i, line in enumerate(records) if line.startswith("specs:")), -1)
    if start < 0:
        fail("specs block not found")
    block_end = next(
        (i for i in range(start + 1, len(records)) if re.match(r"^\S", records[i])),
        len(records),
    )
    starts = [
        index
        for index in range(start + 1, block_end)
        if re.match(r"^  -(?:\s|$)", records[index])
    ]
    ranges = []
    for index, item_start in enumerate(starts):
        item_end = starts[index + 1] if index + 1 < len(starts) else block_end
        parsed = yamlscan.parse_state_specs(["specs:", *records[item_start:item_end]])
        if not parsed:
            continue
        path, scope, relation = parsed[0]
        ranges.append(
            (
                item_start,
                item_end,
                trim(path),
                trim(scope) or "session",
                trim(relation),
            )
        )
    return ranges


def _rewrite_spec_entry(lines, scope, path, relation):
    has_scope = any(re.match(r"^(?:  - |    )scope:", line) for line in lines)
    has_relation = any(re.match(r"^(?:  - |    )relation:", line) for line in lines)
    found_path = False
    out = []
    for line in lines:
        list_item = line.startswith("  - ")
        prefix = "  - " if list_item else "    "
        if re.match(r"^(?:  - |    )path:", line):
            out.append(f"{prefix}path: {state.yaml_scalar(path)}")
            found_path = True
            if not has_scope:
                out.append(f"    scope: {scope}")
                if not has_relation:
                    out.append(f"    relation: {relation}")
            continue
        if re.match(r"^(?:  - |    )scope:", line):
            out.append(f"{prefix}scope: {scope}")
            if not has_relation:
                out.append(f"    relation: {relation}")
            continue
        if re.match(r"^(?:  - |    )relation:", line):
            out.append(f"{prefix}relation: {relation}")
            continue
        out.append(line)
    if not found_path:
        fail("spec entry is missing path")
    return out


def _next_mandatory(records, phase):
    mandatory = yamlscan.session_mandatory_phases(records)
    if phase not in mandatory:
        fail(f"current_phase {phase} is not mandatory for the active track")
    index = mandatory.index(phase)
    return mandatory[index + 1] if index + 1 < len(mandatory) else ""


def _artifact_lint(artifact: trace.ArtifactRef) -> None:
    lint = {
        "research": linters.lint_research,
        "backlog": linters.lint_backlog,
        "spec": linters.lint_spec_package,
        "technical-plan": linters.lint_tech_plan,
        "test-plan": linters.lint_test_plan,
        "code-journal": linters.lint_code,
        "verification": linters.lint_verification,
        "retro": linters.lint_retro,
        "changes-registry": linters.lint_changes,
    }.get(artifact.kind)
    if lint is None:
        return
    ok, output = state.capture_lint(lint, artifact.resolved)
    if not ok:
        fail(
            f"handoff artifact {artifact.name} failed {artifact.kind} validation: "
            f"{output.splitlines()[0] if output else 'unknown lint failure'}"
        )


def _validate_handoff_lifecycle(records: list[str], phase: str) -> None:
    phase_status = trim(yamlscan.nested_value("phases", phase, "status", records))
    gate_status = trim(yamlscan.nested_value("gates", phase, "status", records))
    if yamlscan.pending_delegation_active(records):
        if phase_status != "blocked" or gate_status != "paused":
            fail(
                f"pending delegation for {phase} requires phase=blocked and gate=paused"
            )
        return
    if phase_status != "in-progress" or gate_status != "pending":
        fail(
            f"handoff requires {phase} phase=in-progress and gate=pending "
            f"(got phase={phase_status or 'unset'}, gate={gate_status or 'unset'})"
        )


def _prepare_handoff_candidate(directory, manifest_path):
    try:
        manifest = handoffs.load_manifest(directory, manifest_path)
    except ValueError as err:
        fail(str(err))
    if manifest.status != "ready":
        blockers = ", ".join(
            f"{artifact}:{blocker}" for artifact, blocker in manifest.blocker_refs
        )
        fail(f"cannot accept blocked handoff ({blockers})")
    for artifact in manifest.artifacts.values():
        _artifact_lint(artifact)

    candidate = transaction.create_candidate_session(directory)
    try:
        eng = StateEngine()
        eng.begin(candidate)
        phase = _records_head(eng.records, r"^current_phase:\s*")
        _validate_handoff_lifecycle(eng.records, phase)
        if yamlscan.pending_delegation_active(eng.records):
            pending_phase = trim(yamlscan.pending_delegation_value("phase", eng.records))
            pending_agent = trim(yamlscan.pending_delegation_value("agent", eng.records))
            expected_agent = handoffs.expected_agent(phase)
            if pending_phase != phase:
                fail(f"pending delegation belongs to {pending_phase}, not {phase}")
            if pending_agent != expected_agent:
                fail(
                    f"pending delegation belongs to {pending_agent}, expected {expected_agent}"
                )
            fail("pending delegation must be resumed before submitting a handoff")

        for artifact in manifest.artifacts.values():
            stored = state.encode_artifact_path(artifact.scope, artifact.path)
            if not eng.nested_list_contains("phases", phase, "artifacts", stored):
                eng.append_nested_list_item(
                    "phases", phase, "artifacts", state.yaml_scalar(stored)
                )

        for removal in manifest.spec_removals:
            eng.records = _remove_spec_entry(
                eng.records, removal.scope, removal.path
            )
            eng.remove_nested_list_item(
                "phases",
                "functional-spec",
                "artifacts",
                state.encode_artifact_path(removal.scope, removal.path),
            )

        for deletion in manifest.spec_deletions:
            eng.records = _remove_spec_entry(
                eng.records,
                deletion.registered_scope,
                deletion.registered_path,
            )
            stored = state.encode_artifact_path(
                deletion.registered_scope,
                deletion.registered_path,
            )
            for owner_phase in phases.STANDARD_PHASES:
                eng.remove_nested_list_item(
                    "phases",
                    owner_phase,
                    "artifacts",
                    stored,
                )
            decision_records, found = state.insert_after(
                eng.records,
                r"^decisions:",
                [
                    f'  - date: "{now_utc()}"',
                    "    decision: "
                    + state.yaml_scalar(
                        "Canonical spec deleted: "
                        f"workspace:{deletion.package_path}"
                    ),
                    f"    owner: {state.yaml_scalar('AIDevRetro')}",
                ],
            )
            if not found:
                fail("decisions block not found")
            eng.records = decision_records

        for spec in manifest.specs:
            artifact = manifest.artifacts[spec.artifact]
            if spec.replaces_path:
                eng.records = _replace_spec_entry(
                    eng.records,
                    spec.replaces_scope,
                    spec.replaces_path,
                    artifact.scope,
                    artifact.path,
                    spec.relation,
                )
            elif not _spec_entry_exists(eng.records, artifact.scope, artifact.path):
                eng.records, found = _insert_specs_entry(
                    eng.records, artifact.path, spec.relation, artifact.scope
                )
                if not found:
                    fail("specs block not found")
            else:
                current_relation = next(
                    trim(relation)
                    for path, scope, relation in yamlscan.parse_state_specs(eng.records)
                    if trim(path) == artifact.path
                    and (trim(scope) or "session") == artifact.scope
                )
                if current_relation != spec.relation:
                    eng.records = _replace_spec_entry(
                        eng.records,
                        artifact.scope,
                        artifact.path,
                        artifact.scope,
                        artifact.path,
                        spec.relation,
                    )
        eng.commit()

        next_phase = _next_mandatory(eng.records, phase)
        try:
            trace.render_trace(
                os.path.join(candidate, "trace.md"),
                candidate,
                phase,
                manifest.artifacts,
                eng.records,
                next_phase or phase,
                manifest.contract_mappings,
            )
        except (AttributeError, OSError, TypeError, ValueError, yaml.YAMLError) as err:
            fail(f"could not derive trace from handoff artifacts: {err}")
        cmd_gate_check([candidate, "--phase", phase])
        return candidate, phase, next_phase
    except BaseException:
        shutil.rmtree(candidate, ignore_errors=True)
        raise


def cmd_validate_handoff(args: list[str]) -> str:
    directory, manifest, _gate, _evidence, _chain = _parse_handoff_options(args, False)
    try:
        parsed = handoffs.load_manifest(directory, manifest)
    except ValueError as err:
        fail(str(err))
    _validate_handoff_lifecycle(text.read_lines(state_file_of(directory)), parsed.phase)
    if parsed.status == "blocked":
        print(
            f"sdd-state: validate-handoff OK: phase={parsed.phase} status=blocked "
            f"manifest={manifest}"
        )
        return "blocked"
    candidate, phase, _next = _prepare_handoff_candidate(directory, manifest)
    shutil.rmtree(candidate, ignore_errors=True)
    print(f"sdd-state: validate-handoff OK: phase={phase} manifest={manifest}")
    return "ready"


def cmd_contract_map(args: list[str]) -> None:
    if not args:
        fail(
            "usage: contract-map <session-dir> <contract-id> --spec <path> "
            "--scope <session|workspace> --ac <AC-N> [--ac <AC-N> ...]"
        )
    directory = args[0]
    if len(args) < 2:
        fail("missing contract id")
    contract_id = args[1]
    spec_path = scope = ""
    acs: list[str] = []
    rest = args[2:]
    i = 0
    while i < len(rest):
        if rest[i] == "--spec":
            if i + 1 >= len(rest):
                fail("--spec requires a value")
            spec_path = rest[i + 1]; i += 2
        elif rest[i] == "--scope":
            if i + 1 >= len(rest):
                fail("--scope requires a value")
            scope = rest[i + 1]; i += 2
        elif rest[i] == "--ac":
            if i + 1 >= len(rest):
                fail("--ac requires a value")
            acs.append(rest[i + 1]); i += 2
        else:
            fail(f"unknown contract-map option: {rest[i]}")
    if not spec_path:
        fail("contract-map requires --spec")
    if scope not in ("session", "workspace"):
        fail("contract-map requires --scope session|workspace")
    if not acs:
        fail("contract-map requires at least one --ac")
    if len(acs) != len(set(acs)) or any(
        not re.fullmatch(r"AC-[0-9]+", ac) for ac in acs
    ):
        fail("contract-map --ac values must be unique AC-N IDs")

    records = text.read_lines(state_file_of(directory))
    current_phase = _records_head(records, r"^current_phase:\s*")
    if current_phase not in ("spec-validation", "technical-plan", "test-design"):
        fail(
            "contract-map is only for late mappings during spec-validation, "
            "technical-plan, or test-design"
        )
    if not _spec_entry_exists(records, scope, spec_path):
        fail(f"spec is not registered in session state: {scope}:{spec_path}")
    try:
        resolved_spec = state.resolve_scoped_path(directory, scope, spec_path)
    except ValueError as err:
        fail(str(err))
    if not os.path.isfile(resolved_spec):
        fail(f"spec path not found: {scope}:{spec_path}")
    available_acs = {
        ac
        for line in text.read_lines(resolved_spec)
        for ac in re.findall(r"AC-[0-9]+", line)
    }
    missing = sorted(set(acs) - available_acs)
    if missing:
        fail("contract-map ACs not found in spec: " + ", ".join(missing))

    contracts_path = os.path.join(directory, "contracts.yml")
    if not os.path.isfile(contracts_path):
        fail("contracts.yml not found")
    known_contracts = {
        trim(item_id)
        for item_id, _path, _sha256 in yamlscan.parse_contract_entries(
            text.read_lines(contracts_path)
        )
        if trim(item_id)
    }
    if contract_id not in known_contracts:
        fail(f"contract id not found in contracts.yml: {contract_id}")

    candidate = transaction.create_candidate_session(directory)
    try:
        eng = StateEngine()
        eng.begin(candidate)
        eng.commit()
        source = spec_path if scope == "session" else f"workspace:{spec_path}"
        trace.upsert_contract_mapping(
            os.path.join(candidate, "trace.md"),
            os.path.join(candidate, "contracts.yml"),
            contract_id,
            source,
            tuple(acs),
        )
        ok, output = state.capture_lint(
            linters.lint_trace,
            os.path.join(candidate, "trace.md"),
        )
        if not ok:
            fail(output or "contract-map produced an invalid trace")
        transaction.commit_candidate(directory, candidate)
    finally:
        shutil.rmtree(candidate, ignore_errors=True)
    print(
        f"sdd-state: contract-map OK: {contract_id} -> {scope}:{spec_path} "
        f"({', '.join(acs)})"
    )


def cmd_accept_handoff(args: list[str]) -> None:
    directory, manifest, gstatus, evidence, chain = _parse_handoff_options(args, True)

    if chain and execution_mode_of(state_file_of(directory)) != "autopilot":
        fail("accept-handoff --chain requires execution_mode=autopilot")
    candidate, phase, next_phase = _prepare_handoff_candidate(directory, manifest)
    try:
        eng = StateEngine()
        eng.begin(candidate)
        eng.set_nested_scalar("gates", phase, "status", gstatus)
        for item in evidence:
            eng.append_nested_list_item(
                "gates", phase, "evidence", state.yaml_scalar(item)
            )
        if (
            phase == "spec-verification"
            and any(re.match(r"^  remediation_loop:", line) for line in eng.records)
        ):
            eng.set_nested_scalar("orchestration", "remediation_loop", "iterations", "0")
            eng.set_nested_scalar("orchestration", "remediation_loop", "last_target", "null")
        eng.set_nested_scalar("phases", phase, "status", "complete")
        eng.set_nested_scalar("phases", phase, "completed_at", f'"{now_utc()}"')
        eng.metrics_touch(phase, "complete")
        if next_phase:
            eng.set_top_scalar("current_phase", next_phase)
            if chain:
                eng.set_nested_scalar("phases", next_phase, "status", "in-progress")
                eng.metrics_touch(next_phase, "start")
        eng.commit()
        cmd_gate_check([candidate, "--phase", phase])
        try:
            request_cleanup = handoffs.request_cleanup_paths(directory, phase)
        except ValueError as err:
            fail(str(err))
        transaction.commit_candidate(directory, candidate, delete_paths=request_cleanup)
    finally:
        shutil.rmtree(candidate, ignore_errors=True)

    handoffs.prune_requests_dir(directory)
    suffix = " and next phase started" if chain and next_phase else ""
    print(f"sdd-state: accept-handoff OK: {phase} accepted{suffix}")
    print_next_action(state_file_of(directory), directory)


def cmd_session_complete(args: list[str]) -> None:
    if not args:
        fail("usage: session-complete <session-dir>")
    directory = args[0]
    force = len(args) > 1 and args[1] == "--force"
    eng = StateEngine(force)
    eng.begin(directory)
    eng.set_top_scalar("status", "complete")
    eng.commit()
    print("sdd-state: session-complete OK")


def cmd_set_mode(args: list[str]) -> None:
    if not args:
        fail("usage: set-mode <session-dir> <interactive|autopilot>")
    directory = args[0]
    if len(args) < 2:
        fail("missing mode")
    mode = args[1]
    force = len(args) > 2 and args[2] == "--force"
    if mode not in ("interactive", "autopilot"):
        fail(f"invalid execution mode: {mode} (allowed: interactive | autopilot)")
    eng = StateEngine(force)
    eng.begin(directory)
    if any(re.match(r"^execution_mode:", line) for line in eng.records):
        eng.set_top_scalar("execution_mode", mode)
    else:
        if not any(re.match(r"^current_phase:", line) for line in eng.records):
            eng.discard()
            fail("current_phase not found — cannot insert execution_mode")
        eng.records = state._insert_before(eng.records, r"^current_phase:", [f"execution_mode: {mode}"])
    eng.commit()
    print(f"sdd-state: set-mode OK: execution_mode={mode}")


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

_DISPATCH = {
    "init": cmd_init,
    "set-track": cmd_set_track,
    "status": cmd_status,
    "phase-start": cmd_phase_start,
    "question-round": cmd_question_round,
    "gate": cmd_gate,
    "phase-complete": cmd_phase_complete,
    "advance": cmd_advance,
    "reroute": cmd_reroute,
    "loop-budget": cmd_loop_budget,
    "create-handoff": cmd_create_handoff,
    "pause-handoff": cmd_pause_handoff,
    "resume-handoff": cmd_resume_handoff,
    "retry-handoff": cmd_retry_handoff,
    "submit-handoff": cmd_submit_handoff,
    "validate-handoff": cmd_validate_handoff,
    "accept-handoff": cmd_accept_handoff,
    "next": cmd_next,
    "artifact-add": cmd_artifact_add,
    "decision-add": cmd_decision_add,
    "spec-add": cmd_spec_add,
    "spec-repoint": cmd_spec_repoint,
    "contract-map": cmd_contract_map,
    "contract-add": cmd_contract_add,
    "preflight": cmd_preflight,
    "gate-check": cmd_gate_check,
    "layout-probe": cmd_layout_probe,
    "session-complete": cmd_session_complete,
    "set-mode": cmd_set_mode,
    "metrics": cmd_metrics,
}


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print(usage(), file=sys.stderr)
        return 2
    command = argv[0]
    rest = argv[1:]
    if command in ("help", "--help", "-h"):
        print(usage())
        return 0
    handler = _DISPATCH.get(command)
    if handler is None:
        print(usage(), file=sys.stderr)
        return 2
    try:
        handler(rest)
        checkpoints.emit(command, rest)
    except LintFailure as err:
        if err.message is not None:
            print(f"sdd-state: {err.message}", file=sys.stderr)
        return err.code
    except ToolError as err:
        if err.message is not None:
            print(f"sdd-state: {err.message}", file=sys.stderr)
        return err.code
    return 0
