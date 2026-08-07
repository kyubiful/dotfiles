# SDD Kickoff Protocol

The kickoff consolidates everything a new session needs from the user into **one interaction round**, instead of spreading track confirmation, source confirmation, and the first scoping questions across separate stops. Time-to-first-question is the metric this protocol optimizes: the user should face a single, well-organized question batch as early as possible, and nothing before it should burn tokens on ceremony.

# Kickoff sequence

## Resolve session

Resolve the user's intent before reading session state:

- For an explicitly named or requested resume session, read only that session's state (prefer the state CLI's `status` operation) and follow its pending-delegation and routing rules.
- For a **new feature/session request**, do **not** initially list or read any prior session, including its `sdd-state.yml`, to check whether it awaits continuation. Classify from the user's request and run the new-session `init`/kickoff flow directly. The `init` operation handles collisions.
- If the user does not make clear whether they intend a resume or a new session, ask that single routing question through the native ask mechanism before reading any session state.

## 1. Minimal state first (no ceremony)

Create only what routing needs, through the state CLI:

- `sdd-state.py init {sessions-root} {slug} --name "{name}"` — session directory + `sdd-state.yml` with identity and real UTC timestamps in one command.
- Do **not** create `trace.md` yet — `set-track` copies the right template after classification.
- Do **not** create `contracts.yml` or `contracts/` yet — `contract-add` creates them lazily at the first contract actually provided or referenced. A session that never receives contracts never materializes them; the linter treats a missing `contracts.yml` as an empty manifest.

## 2. Classify cheaply (no user roundtrip yet)

- Run `<agent-dir>/skills/aidev-sdd/references/track-classifier.md` against the user's stated goal only. Never read repository content to classify.
- Produce: proposed track, 1-line rationale, skipped phases list.

## 3. One consolidated kickoff batch (the only pre-phase user stop)

Present **a single batch** through the native ask mechanism containing, in this order:

1. **Track proposal** — proposed track + what it skips (one line per track meaning, per the classifier's Step 3), as a confirm/override question.
2. **Scope confirmation** — only if the goal has a genuine ambiguity that changes routing (one question max; skip entirely when the goal is clear).
3. **Known inputs** — only if the user mentioned specs, issues, PDFs, screenshots, or contracts: confirm the pointers in the same batch instead of a later stop.

Rules:

- Maximum 5 questions in the batch; fewer is better. If the goal is unambiguous and no inputs were mentioned, the batch is just the track confirmation.
- Never ask anything a specialist will ask better later — the kickoff collects routing facts, not requirements. Requirement interviews belong to discovery/functional-spec specialists.
- On deferral, proceed with the proposed track (per classifier rules) and record the deferral.

## 4. Persist and route immediately

- Apply the confirmed track with one command: `sdd-state.py set-track {session-dir} {track} --rationale "..." [--signals ...]`. It atomically sets track + classification, marks skips with evidence, copies the trace template, completes bootstrap, sets `current_phase`, and records the decision.
- Start the first delegated phase with `sdd-state.py phase-start {session-dir} {phase}` (metrics start automatically) and delegate **in the same turn** whenever the runtime allows it. The user's next contact after the kickoff batch should be the first specialist's question round (discovery/planning interview) or a completed-phase report — never another orchestration stop.

# First-interview fast path (discovery / functional-spec sessions)

When the first delegated phase is `discovery` or `functional-spec`, the orchestrator must include in `{{CONTEXT_FILES}}` every fact the kickoff already gathered (goal, confirmed inputs, track rationale) so the specialist's **first envelope round already contains substantive interview questions** instead of re-asking scope basics. Specialists must not re-confirm facts recorded in the kickoff.

# What the kickoff must never do

- Never explore the workspace, read code, or read architecture files.
- Never split track confirmation and input confirmation into separate user stops.
- Never render kickoff questions as plain text — always the native ask mechanism.
- Never delay the first specialist delegation to "summarize the session so far".
