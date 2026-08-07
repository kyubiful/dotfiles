# Autopilot Offer Checkpoint

In `interactive` execution mode, the orchestrator MUST offer to switch the session to `autopilot` when the next non-skipped phase belongs to the autopilot-recommended group. The phase groups and mode semantics are defined in `references/execution-modes.md`. This checkpoint does not add a phase, state field, or CLI command.

## Checkpoint position

Offer autopilot when the just-completed phase belongs to the user-interaction recommended group and the next non-skipped phase belongs to the autopilot-recommended group.

Typical trigger points:

| Track                                   | Completed phase that triggers the offer | Next phase (autopilot-recommended) |
| --------------------------------------- | --------------------------------------- | ---------------------------------- |
| `moderate`                              | `technical-plan`                        | `implementation`                   |
| `complex`                               | `technical-plan`                        | `implementation`                   |
| `exhaustive`                            | `technical-plan`                        | `test-design`                      |
| `smart` (with planning phases selected) | `technical-plan`                        | `test-design` or `implementation`  |
| `simple`                                | none                                    | —                                  |

Do not offer autopilot:

- When `execution_mode` is already `autopilot`.
- When an offer has already been made for the current transition (recorded in `decisions[]`).
- When the user has already accepted an earlier autopilot offer in the same session.
- When the user declined the offer at this transition point. Further offers after that decline add no value.
- When the next non-skipped phase is `session-complete`.

## User question

Use the host runtime's native question mechanism. Present the recommended option first.

```text
Hey!

I can continue the next phases in autopilot. Continuing in autopilot will:
- Make our session progress from phase to phase automatically.
- Unless I can't resolve a question for you, I will take recommended suggestions from specialists.
- I will stop before retro to let you review the implemented result.

Would you like to continue in autopilot?
```

Preferred bounded options:

- `Yes, continue in autopilot`
- `No, let's continue in interactive mode`

## State handling

Use only existing state CLI commands. Record every offer outcome in `decisions[]` with the exact prefix `Autopilot offer after {phase}:` so the orchestrator can detect duplicates on resume.

### If the user accepts

1. Run `sdd-state.py set-mode {session-dir} autopilot`.
2. Run `sdd-state.py decision-add {session-dir} --decision "Autopilot offer after {phase}: accepted — execution_mode changed to autopilot"`.
3. Continue the SDD flow; subsequent phases may use chained delegation (`accept-handoff --chain`) because the mode now allows unattended execution.

### If the user declines

1. Run `sdd-state.py decision-add {session-dir} --decision "Autopilot offer after {phase}: declined — continuing in interactive mode"`.
2. Continue the SDD flow in `interactive` mode; stop after each remaining phase for user confirmation.

## Interaction with existing rules

- A `subagent-question-envelope` still breaks the chain in `autopilot`; resolve it through the delegated question protocol.
- The pre-retro user acceptance checkpoint still stops `autopilot` before `retro`.
- The post-retro session closure checkpoint still stops `autopilot` before `session-complete`.
- The orchestrator must not self-accept or self-close on the user's behalf.
