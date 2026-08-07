# Pre-retro User Acceptance Checkpoint

Before `retro` starts, the user must confirm whether the implemented result is acceptable. This keeps `retro` as closure/compounding only, and keeps refinement inside the active session while the requested change is still within the approved session scope.

This checkpoint does not add a phase, state field, CLI command, or special transition rule.

## Checkpoint Position

- `simple`: after implementation is complete and before moving into `retro`.
- `moderate`, `complex`, `exhaustive`, `smart`: after verification passes and before accepting/completing `spec-verification` when that phase is active for the selected track.

When the session delivered a GitHub PR, the `AIDevVerifier` **PR delivery decision** runs first (see `<agent-dir>/skills/aidev-sdd/SKILL.md`, "PR delivery decision"). This checkpoint applies after every PR delivery choice, including `ignore_draft`; leaving a PR in DRAFT does not skip mandatory `retro`.

## User Question

Before asking, run `gate-check` and the required semantic review for the final delivery/evaluation gate. The native question must include the result as context, so the user is confirming an evidenced outcome. Ask a product-oriented question rather than exposing phase mechanics:

```text
Verification passed and no blocking findings remain.
Is the implemented result correct enough to close this session and move to retro?

Choose "Yes, move to retro" to continue, or type what you want changed.
```

Adapt the first sentence to the actual gate result and accepted risks/deferrals. Do not ask the pre-retro question while the gate has unresolved blockers; resolve or route those first.

Preferred bounded options:

- `Yes, move to retro` — recommended when verification passed and no blockers remain.

Allow the runtime's freeform/custom answer and treat any typed answer as a request for changes; the typed text is the requested change detail. Do not ask the user to pick an internal phase directly; classify the feedback yourself.

## State Handling

- If the user accepts: record the acceptance with `decision-add`, accept/complete the current gate normally, and advance to `retro`. Do not stop with a plain-text "next step is retro" message after the user has selected `Yes, move to retro`.
- If `simple` feedback stays within current scope: keep `implementation` open. Do not use `reroute` because there is no earlier active delivery phase.
- If feedback stays within current scope and `spec-verification` is active for the selected track: record `spec-verification` as failed with evidence summarizing the user feedback, then use the existing remediation loop/reroute rules to send the fix to the owning earlier phase.
- If the user requests a material new capability, a new contract after implementation has begun, or a change that would substantially alter the approved session goal: do not broaden the current session. Record the scope boundary decision and ask whether to close the delivered scope and start a new SDD session for the new work, or keep the current session blocked.
- In `autopilot`, stop and report at this checkpoint. The orchestrator must not self-accept on the user's behalf.
