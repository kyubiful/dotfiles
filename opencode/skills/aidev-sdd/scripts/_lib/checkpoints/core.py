"""Checkpoint hints framework: model, registry, context building, and emission.

A checkpoint is a mandatory orchestration decision point (for example: offering
autopilot, or getting the user's acceptance before `retro`) that today lives
only in prose the orchestrator has to remember. This package turns that prose
into a mechanical signal: after a command mutates or reports the session, the
applicable checkpoints are collected and appended to the command output as

    sdd-state: checkpoint-<name>: <imperative action>

This module owns the framework only. Each checkpoint is a pure detector that
inspects a read-only ``CheckpointContext`` and returns at most one
``Checkpoint``; the detector rules themselves live in ``rules.py`` and register
here at import time (wired by the package ``__init__``). Detectors never mutate
state and ``emit`` never changes a command's exit code: checkpoints are advisory
output layered on top of the command result."""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Optional

from .. import text, yamlscan

trim = yamlscan.trim_scalar


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Checkpoint:
    """A single advisory hint. ``name`` becomes the ``checkpoint-<name>`` label;
    ``action`` is the imperative reminder printed after it."""

    name: str
    action: str

    def render(self) -> str:
        return f"sdd-state: checkpoint-{self.name}: {self.action}"


@dataclass(frozen=True)
class CheckpointContext:
    """Read-only snapshot of the facts detectors reason over, built once per
    command from the post-command session state."""

    command: str
    directory: str
    session_status: str
    track: str
    execution_mode: str
    current_phase: str
    current_phase_status: str
    current_gate_status: str
    previous_phase: str
    next_phase: str
    mandatory_phases: tuple[str, ...]
    pending_delegation: bool
    decisions: tuple[str, ...]


Detector = Callable[[CheckpointContext], Optional[Checkpoint]]


@dataclass(frozen=True)
class _Registration:
    name: str
    commands: frozenset[str]
    detect: Detector


_REGISTRY: list[_Registration] = []


def register(name: str, commands: set[str]) -> Callable[[Detector], Detector]:
    """Register a detector under ``name``, evaluated only after ``commands``."""

    def decorate(detect: Detector) -> Detector:
        _REGISTRY.append(_Registration(name, frozenset(commands), detect))
        return detect

    return decorate


# ---------------------------------------------------------------------------
# context building
# ---------------------------------------------------------------------------

def _decision_texts(records: list[str]) -> tuple[str, ...]:
    rx = re.compile(r"^\s+decision:\s*(.*)$")
    out: list[str] = []
    for line in records:
        m = rx.match(line)
        if m:
            out.append(trim(m.group(1)))
    return tuple(out)


def _neighbours(mandatory: list[str], current: str) -> tuple[str, str]:
    """Return (previous_phase, next_phase) around ``current`` in the active
    mandatory sequence; empty strings at the ends."""
    if current not in mandatory:
        return "", ""
    idx = mandatory.index(current)
    prev = mandatory[idx - 1] if idx > 0 else ""
    nxt = mandatory[idx + 1] if idx + 1 < len(mandatory) else ""
    return prev, nxt


def build_context(command: str, directory: str, records: list[str]) -> CheckpointContext:
    current = trim(_head(records, r"current_phase:"))
    mandatory = list(yamlscan.session_mandatory_phases(records))
    prev, nxt = _neighbours(mandatory, current)
    return CheckpointContext(
        command=command,
        directory=directory.rstrip("/"),
        session_status=trim(_head(records, r"status:")),
        track=trim(_head(records, r"track:")),
        execution_mode=trim(_head(records, r"execution_mode:")) or "interactive",
        current_phase=current,
        current_phase_status=trim(yamlscan.nested_value("phases", current, "status", records)),
        current_gate_status=trim(yamlscan.nested_value("gates", current, "status", records)),
        previous_phase=prev,
        next_phase=nxt,
        mandatory_phases=tuple(mandatory),
        pending_delegation=yamlscan.pending_delegation_active(records),
        decisions=_decision_texts(records),
    )


def _head(records: list[str], prefix: str) -> str:
    rx = re.compile("^" + prefix)
    for line in records:
        if rx.match(line):
            return rx.sub("", line, count=1)
    return ""


# ---------------------------------------------------------------------------
# collection / emission
# ---------------------------------------------------------------------------

_trigger_cache: Optional[frozenset[str]] = None


def _trigger_commands() -> frozenset[str]:
    """Union of every registered detector's commands, cached on first use.

    Computed lazily so it reflects the full registry once the rules module has
    imported and registered its detectors."""
    global _trigger_cache
    if _trigger_cache is None:
        commands: set[str] = set()
        for reg in _REGISTRY:
            commands |= reg.commands
        _trigger_cache = frozenset(commands)
    return _trigger_cache


def collect(ctx: CheckpointContext) -> list[Checkpoint]:
    """Run every detector registered for ``ctx.command`` and return the hits, in
    registration order."""
    hits: list[Checkpoint] = []
    for reg in _REGISTRY:
        if ctx.command not in reg.commands:
            continue
        found = reg.detect(ctx)
        if found is not None:
            hits.append(found)
    return hits


def emit(command: str, argv_rest: list[str]) -> None:
    """Collect and print the checkpoints applicable after ``command``.

    Safe to call after any command: it short-circuits when no detector cares
    about the command, when the session directory / state file is missing, and
    swallows its own errors so a checkpoint bug can never change a command's
    result."""
    if command not in _trigger_commands():
        return
    if not argv_rest:
        return
    directory = argv_rest[0]
    state_file = os.path.join(directory.rstrip("/"), "sdd-state.yml")
    if not os.path.isfile(state_file):
        return
    try:
        records = text.read_lines(state_file)
        ctx = build_context(command, directory, records)
        for checkpoint in collect(ctx):
            print(checkpoint.render())
    except Exception as err:  # never let a hint break the command result
        print(f"sdd-state: checkpoint evaluation skipped: {err}", file=sys.stderr)