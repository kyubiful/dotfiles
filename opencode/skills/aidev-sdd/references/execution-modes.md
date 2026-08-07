# Execution Modes

SDD sessions run in one of two execution modes. The mode governs whether the orchestrator stops for user confirmation between phases or may chain phases unattended.

In `autopilot`, the orchestrator may chain unattended; in `interactive`, it stops after each phase and offers autopilot when entering the autopilot-recommended group.

## Allowed values

- `interactive` — default. The orchestrator stops after each phase for user confirmation. When the next non-skipped phase belongs to the autopilot-recommended group, the orchestrator loads `references/autopilot-offer-checkpoint.md` and offers to switch to `autopilot`.
- `autopilot` — unattended phase chaining is allowed. The orchestrator may use `accept-handoff --chain` to move directly into the next delegation when the next phase needs no user decision to start.

## How the mode is set

- At bootstrap, the session template defaults to `interactive`.
- If the user requests unattended execution when starting the session, run `sdd-state.py set-mode {session-dir} autopilot`.
- If the user accepts the autopilot offer at a checkpoint, run `sdd-state.py set-mode {session-dir} autopilot`.
- The mode survives session resumes and is reported by every `status`/`next`/`accept-handoff` output.

## Mode-aware stops

Even in `autopilot`, the orchestrator must stop and report (not self-accept) at these mandatory checkpoints:

- `references/autopilot-offer-checkpoint.md` — only in `interactive`; offer to switch to `autopilot` when entering the autopilot-recommended group.
- `references/pre-retro-acceptance-checkpoint.md` — before `retro`; the user must accept the implemented result.
- `references/post-retro-closure-checkpoint.md` — before `session-complete`; the user must accept the retro result and confirm closing the session.

## Mode-aware exceptions

- A `subagent-question-envelope` breaks the chain in both modes; resolve it through the delegated question protocol.
- A failed gate, recorded blocker, or semantic review demanding user judgment stops the chain in both modes.
- The bounded remediation loop runs unattended in both modes until convergence or budget exhaustion; see `references/remediation-loop.md`.
