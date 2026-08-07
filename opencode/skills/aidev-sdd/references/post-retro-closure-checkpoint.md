# Post-retro Session Closure Checkpoint

The `retro` gate must not be accepted and the session must not be marked complete until the user confirms whether the retro result is acceptable and whether to finish the SDD session.

This gives the user one final chance to review the closure/compounding result without adding a phase, state field, CLI command, or special transition rule.

## Checkpoint Position

- After `AIDevRetro` returns its handoff and `retro.md` plus any retro side effects are available.
- Before accepting/completing `retro` and before running `session-complete`.

## User Question

Use the host runtime's native question mechanism. Ask a closure-oriented question. The question must include the retro outcome as context, so the user is confirming an evidenced closure result:

```text
Retro completed. Compounded knowledge: <summary>. Spec consolidation: <summary>. Follow-ups: <count/status>.
The implementation has been delivered. Is the retro result OK, and do you want to finish the SDD session?

Choose "Yes, finish SDD session" to close, or type what you want changed in the retro.
```

Preferred bounded options:

- `Yes, finish SDD session` — recommended when retro produced no unresolved blockers.

Allow the runtime's freeform/custom answer and treat any typed answer as a request for retro changes; the typed text is the requested retro change detail. Do not ask the user to choose internal transition commands.

## State Handling

- If the user accepts: record the closure acceptance with `decision-add`, then accept the `retro` handoff normally and run `session-complete`.
- If the user requests retro changes: keep `retro` open. Do not use `reroute`.
- If the user requests new product scope or implementation changes after retro: do not expand the current session. Record the scope boundary decision and suggest starting a new SDD session for that work.
- In `autopilot`, stop and report at this checkpoint. The orchestrator must not self-accept or self-close on the user's behalf.
