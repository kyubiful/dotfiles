#!/usr/bin/env python3
"""Validate the deterministic structure of SDD session artifacts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import linters
from _lib.cli import LintFailure

USAGE = """Usage: sdd-lint.py <mode> <path> [current-phase]

Modes operating on a single file:
  session      sdd-state.yml (for a session directory)
  spec-package specs/{domain}/{spec-name}/spec.md
  backlog      backlog-plan.yml
  trace        trace.md
  trace-gate   trace.md with no unresolved placeholders due by the current phase
               (optional 3rd arg: current phase; omitted = strict whole-file gate)
  research     research.md
  tech-plan    tech-plan.md
  code         code.md
  test-plan    test-plan.md
  verification verification.md
  retro        retro.md
  changes      changes.json
  contracts    contracts.yml
  metrics      sdd-state.yml (report session efficiency telemetry; read-only)

Modes operating on a session directory:
  coverage     cross-artifact AC coverage check

Validates the deterministic structure of SDD session artifacts.
"""

VALID_MODES = {
    "session", "spec-package", "backlog", "trace", "trace-gate", "research",
    "tech-plan", "code", "test-plan", "verification", "retro", "changes",
    "contracts", "metrics", "coverage",
}


def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        sys.stderr.write(USAGE)
        return 2

    mode = argv[0]
    target = argv[1]
    phase = argv[2] if len(argv) == 3 else ""

    if mode not in VALID_MODES:
        sys.stderr.write(USAGE)
        return 2

    try:
        linters.run_mode(mode, target, phase)
    except LintFailure as err:
        if err.message is not None:
            print(f"sdd-lint: {err.message}", file=sys.stderr)
        return err.code

    print(f"sdd-lint: {mode} OK: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
