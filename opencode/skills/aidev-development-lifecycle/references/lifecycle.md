# Delivery Workflow — Lifecycle

## Phase Execution (progressive disclosure)

The full, authoritative procedure for each phase lives in the skill references. **Before executing a development phase, load its reference file and follow it exactly** — the summaries below are an index, not the procedure. On re-entry, load the lifecycle reference and only the references for phases that are not yet terminal.

| Phase                  | Reference to load                                              | Summary                                                                                                              |
| ---------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1 — Setup              | `skills/aidev-development-lifecycle/references/setup.md`       | Run the setup CLI exclusively for delivery setup, branch grounding, repository reconciliation, and journal creation. |
| 2 — Coding             | `skills/aidev-development-lifecycle/references/coding.md`      | Implementation guide, runs CI handoffs, and persists journal updates after every batch.                              |
| 3 — PaaS Config Review | `skills/aidev-development-lifecycle/references/paas-review.md` | Load `paas-config`; review and place every configuration change, or document no changes required with justification. |
| 4 — Validation         | `skills/aidev-development-lifecycle/references/validation.md`  | Read-only validators, run the coding↔validation fix loop, and persist validation status.                            |
| 5 — Commit & Push      | `skills/aidev-development-lifecycle/references/commit.md`      | Load `conventional-commits`, commit and publish when allowed, leave PRs DRAFT, and persist terminal journal status.  |

### Routing rules

- Do not preload every phase reference. Resolve the session path, current `delivery_mode`, journal status, task dispositions, and next phase first.
- A phase reference is authoritative only while that phase is active or is explicitly being revalidated. Follow its procedure exactly rather than reconstructing steps from this index.
- Load a reference named by a phase reference only when that phase reaches the step that requires it. Do not load downstream phase references early merely to anticipate later work.
- On ordinary re-entry, load this file, inspect journal, and then load only references for phases that are not terminal.
- If a phase is blocked, load only the reference needed to diagnose or resolve that phase's blocker. Do not advance by consulting later-phase procedures.

## Progress Journal

One centralized progress journal is maintained at `<framework-session-path>/code.md`. If the invocation context includes `Session path: <path>`, use that as `<framework-session-path>` and derive `{session_slug}` from `basename(<framework-session-path>)` only for names and idempotency keys. Otherwise derive `<framework-session-path>` as `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}` from the tech-plan title (short kebab-case).

The journal provides resumability, unified progress across parallel coding work, decision traceability, and implementation evidence for SDD trace linking.

### Lifecycle

- **Create** it at the start of Phase 1 with the initial tech-plan task list, or one task derived from a no-plan request.
- **Update** it after every completed phase and every Implementation Report.
- **Read** it at the start of every invocation to detect re-entry and resume from the last checkpoint.
- Create it from `skills/aidev-development-lifecycle/assets/code-journal-template.md`.

### Journal checkpoint

Run a journal checkpoint after every completed phase, execution batch, validation aggregation, or fix pass and before any later phase, batch, or sub-agent starts. The checkpoint is the only phase-transition procedure for updating **Task Progress**, **Phase Status**, and the overall status.

1. Collect the completed work's stable task IDs, truthful dispositions, notes, and the current phase result.
2. Apply one payload with [scripts/journal_checkpoint.py](../scripts/journal_checkpoint.py). The payload contains `task_updates`, one `phase_update`, and optionally `overall_status`,
3. Re-read the journal after the command succeeds. Do not advance unless every requested task and phase update is present.
4. Stop as `blocked` when an update cannot be applied or verified. Never continue with completed work recorded as `pending`.

The checkpoint validates these invariants:

- A task update uses a known stable task ID and an allowed Task Progress disposition.
- `deferred`, `n/a`, and `accepted-risk` task dispositions have concrete notes.
- Phase 2, Phase 4, and Phase 5 cannot become `done` while any Task Progress row remains `pending`, `partial`, `blocked`, or `failed-validation`.
- `complete` requires every task to be `done`; `complete-with-follow-ups` requires every task to have a terminal disposition.

Record implementation evidence, decisions, CI handoffs, validation reports, and commit details in their journal sections before the checkpoint that advances beyond the related work. The checkpoint preserves those sections while atomically updating progress state.

### Re-entry

Before trusting any previous status, resolve `<framework-session-path>`, the current tech plan (or its absence), current target repositories, and current `delivery_mode`. When the journal exists, read its `Delivery mode` line, **Repositories**, and **Backlog Links** tables and reconcile them against the current invocation.

A prior `1 — Delivery Setup = done` is advisory until every current target repository's required setup is re-verified. Rerun Phase 1 if the journal uses a different `delivery_mode`. Read **Task Progress** by stable `id`; only `pending`, `partial`, `blocked`, and `failed-validation` rows remain in Phase 2 scope. A missing journal is a fresh run.

## Continuation Iterations

Use this procedure only when a follow-up changes or revalidates work already recorded in the current session's `code.md`.

### Path selection

- **Small change** — the request is narrow, the current branch is trustworthy, and pre-existing evidence still applies.
- **Validation only** — no code change is needed; only specific checks or evidence must be refreshed.
- **Full delivery** — the request is broad, risky, unclear, or invalidates earlier work.
- **Blocked** — the request or repository state is unsafe or unclear.

Select **Full delivery** when the change affects a public contract, API, schema, migration, permission, security control, dependency, build tooling, shared configuration, or more than one bounded context. Select it whenever reuse is not clearly safe.

When the current request has no persisted iteration, returns the selected path and rationale in its Implementation Report, then stops before changing code or refreshing validation. It never persists lifecycle artifacts. Once the caller persists that iteration, the selected phase procedure continues without a second classification; reclassify only when the request changes again.

### Persist the iteration

Before any continuation phase work, code change, or validation refresh, the caller adds and persists one **Continuation Iterations** row. Record the selected journal strategy, requested change, evidence baseline, all five phase dispositions, validation scope, and any blocker.

Encode **Phase Dispositions** as a semicolon-separated, numbered list: `1=reused; 2=rerun; 3=rerun; 4=rerun; 5=rerun`. The numbers always mean Delivery Setup, Coding, PaaS Config, Validation, and Commit.

| path            | Journal strategy        | Phase Dispositions                                             |
| --------------- | ----------------------- | -------------------------------------------------------------- |
| Small change    | `incremental`           | `1=reused; 2=rerun; 3=rerun; 4=rerun; 5=rerun`                 |
| Validation only | `targeted-revalidation` | `1=reused; 2=not-applicable; 3=rerun; 4=rerun; 5=reused`       |
| Full delivery   | `full-delivery`         | `1=rerun; 2=rerun; 3=rerun; 4=rerun; 5=rerun`                  |
| Blocked         | `blocked`               | Mark every affected phase `blocked`; do not signal completion. |

**Disposition rules**:

- `rerun` — load and execute the phase reference. A Full delivery reruns Phase 1 through idempotent reconciliation: verify and refresh recorded setup rather than creating duplicate issues, branches, or PRs.
- `reused` — load the phase reference only to perform its stated reuse verification. Record the Phase Status as `done` with `[Iteration N] reused — {evidence}` in Notes; do not repeat the phase's mutating work.
- `not-applicable` — do not execute that phase's implementation work. Record its Phase Status as `done` with `[Iteration N] not-applicable — {reason}` in Notes. This disposition is currently valid only for Phase 2 in a Validation only iteration.
- `blocked` — set the affected Phase Status to `blocked`, set the overall journal status to `blocked`, and use the native question mechanism when user action is needed.

Phase Status values are not dispositions. They remain `pending`, `in-progress`, `done`, `partial`, or `blocked`; the **Continuation Iterations** row and the Phase Status Notes record whether the current iteration reran, reused, or did not require a phase. This preserves the final exit check requirement that all five Phase Status rows are `done` before completion.

For a Validation only iteration, Phase 3 still reruns as an impact assessment and records `done — no configuration changes required`; it does not apply configuration solely because the iteration is running. Phase 5 may be `rerun` or `reused`, but never `not-applicable`.

### Status vocabulary

`in-progress` is the only non-terminal value. Terminal values are:

- `complete` — all required phase work is complete with nothing outstanding.
- `complete-with-follow-ups` — required phase work is complete, but named `deferred`, `n/a`, or `accepted-risk` task dispositions remain.
- `blocked` — a phase requires user action.
- `failed` — a phase reached its allowed limit without passing.

Signal completion only when the journal status is `complete` or `complete-with-follow-ups`. The agent's **Pre-Completion Exit Check** remains the sole authority for completion or pass recommendations.

**Task Progress** uses `pending`, `partial`, `blocked`, `done`, `failed-validation`, `deferred`, `n/a`, and `accepted-risk`. A `deferred`, `n/a`, or `accepted-risk` row requires a concrete reason in its Notes cell and requires the overall status `complete-with-follow-ups` when the delivery otherwise completes.

## Final Report

After Phase 5, summarize GitHub issues/branches/draft PRs for `github-delivery` or reused local branches for `local-only`; implemented files and features; CI handoffs; validation reports and final status per repository mapping; PaaS results; commit SHAs and messages; and draft PR links where applicable.

## Cross-Phase Rules

- Use the **Journal checkpoint** before advancing to another phase, batch, or the end of the run.
- Never resolve the journal relative to `local_repo_path`; with `Session path`, it is always `<framework-session-path>/code.md`.
- Do not leave a stale waiting note after its prerequisite is done; advance the phase or truthfully record a deferral.
- Completion is authorized only by the agent's **Pre-Completion Exit Check**. Phase-level builds, tests, and structural checks are not completion.
