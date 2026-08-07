"""Track/phase ordering tables for the sdd lint/state CLIs."""
from __future__ import annotations

STANDARD_PHASES = [
    "bootstrap",
    "discovery",
    "functional-spec",
    "spec-validation",
    "technical-plan",
    "test-design",
    "implementation",
    "spec-verification",
    "retro",
]

# Execution-mode guidance groups. These are consumed by checkpoint detectors to
# identify boundaries where the orchestrator should pause for a user decision.
USER_INTERACTION_PHASES = [
    "bootstrap",
    "discovery",
    "functional-spec",
    "spec-validation",
    "technical-plan",
]

AUTOPILOT_PHASES = [
    "test-design",
    "implementation",
    "spec-verification",
    "retro",
]

_MANDATORY = {
    "simple": ["bootstrap", "implementation", "retro"],
    "moderate": ["bootstrap", "technical-plan", "implementation", "spec-verification", "retro"],
    "complex": [
        "bootstrap",
        "functional-spec",
        "spec-validation",
        "technical-plan",
        "implementation",
        "spec-verification",
        "retro",
    ],
    "exhaustive": list(STANDARD_PHASES),
}

_SKIPPED = {
    "simple": [
        "discovery",
        "functional-spec",
        "spec-validation",
        "technical-plan",
        "test-design",
        "spec-verification",
    ],
    "moderate": ["discovery", "functional-spec", "spec-validation", "test-design"],
    "complex": ["discovery", "test-design"],
    "exhaustive": [],
}

# The smart track has no fixed phase set. Its active set is chosen per session
# (persisted via the phases.<phase>.status: skipped markers) and resolved by the
# file-aware helpers in yamlscan. The core is always active; the rest are
# user-selected optional phases.
SMART_CORE = ["bootstrap", "implementation", "spec-verification", "retro"]
SMART_SELECTABLE = ["discovery", "functional-spec", "spec-validation", "technical-plan", "test-design"]

_ORDER = {name: i + 1 for i, name in enumerate(STANDARD_PHASES)}

_EXPECTED_ARTIFACTS = {
    "bootstrap": ["sdd-state.yml", "trace.md"],
    "discovery": ["research.md"],
    "functional-spec": ["plan.md", "backlog-plan.yml"],
    "spec-validation": [],
    "technical-plan": ["tech-plan.md"],
    "test-design": ["test-plan.md"],
    "implementation": ["code.md"],
    "spec-verification": ["verification.md"],
    "retro": ["retro.md"],
}


def track_mandatory_phases(track: str) -> list[str]:
    return list(_MANDATORY.get(track, []))


def track_skipped_phases(track: str) -> list[str]:
    return list(_SKIPPED.get(track, []))


def phase_order(phase: str) -> int:
    return _ORDER.get(phase, 999)


def expected_phase_artifacts(phase: str) -> list[str]:
    return list(_EXPECTED_ARTIFACTS.get(phase, []))


# Trace sections owned by each phase, used to prune the smart trace when the
# phase is not selected. 'Session' is intentionally excluded (core identity,
# always kept). Core phases (implementation, spec-verification) are never
# skipped in smart, so their sections are never pruned.
_TRACE_SECTIONS = {
    "functional-spec": ["Acceptance Criteria Trace"],
    "spec-validation": ["Input Contract Trace", "Backlog Trace"],
    "technical-plan": ["Technical Plan Trace"],
    "test-design": ["Test Design Trace"],
}


def phase_trace_sections(phase: str) -> list[str]:
    return list(_TRACE_SECTIONS.get(phase, []))
