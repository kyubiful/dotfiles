# SDD Track Classifier

The orchestrator runs this classifier during session initialization to decide which SDD track applies. Tracks are not separate frameworks — they select which phases are mandatory, skipped, or optional inside the same standard SDD contract.

## Classification philosophy

Classify confidently: pick the **lightest track that safely fits** and keep the session streamlined. Speed is a feature — do not buy ceremony you will not use.

- `exhaustive` is for **genuine risk** (contracts, persisted schema, security-sensitive paths, cross-team coordination), not for mild uncertainty. Reaching for `exhaustive` because a request feels slightly fuzzy is the failure mode this classifier exists to prevent.
- A capable agent **infers a clear acceptance criterion** from a normal feature request instead of escalating; only escalate when the scope genuinely cannot be pinned down.
- Mid-session **reclassification is cheap and expected**. Starting light and promoting when real scope appears is the preferred path, far better than front-loading every phase "just in case."
- When two tracks both fit, choose the lighter one and let the evidence prove whether more rigor is needed.

## Tracks

| Track        | When to use                                                                                                                                                                                                                                                                                                                                  | Mandatory phases                                                                                                                                                                                 | Skipped by default                                                                                      | Required artifacts                                                                                                                |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `simple`     | Trivial mechanical change a single implementation pass can deliver and prove with a diff: typo, comment fix, log message tweak, config constant, dependency patch bump with green build. No functional decision, no research, no separate plan needed.                                                                                       | `bootstrap`, `implementation`, `retro`                                                                                                                                                           | `discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`, `spec-verification` | `sdd-state.yml`, `code.md` (with inline verification evidence: diff + validation command), `retro.md`, diff                       |
| `moderate`   | Mechanical, low-risk change that still deserves a lightweight plan and separate verification: formatting sweep, multi-file rename without API impact, dependency minor bump needing a validation pass.                                                                                                                                       | `bootstrap`, `technical-plan`, `implementation`, `spec-verification`, `retro`                                                                                                                    | `discovery`, `functional-spec`, `spec-validation`, `test-design`                                        | `sdd-state.yml`, `tech-plan.md`, `code.md`, `verification.md`, `retro.md`, diff                                                   |
| `complex`    | Spec-driven delivery: the work deserves a functional spec and its validation (with backlog/issue projection) before technical planning, but still avoids a separate discovery phase and the formal test-design phase. Test evidence design is folded into `spec-verification` (the verifier designs and executes evidence in one roundtrip). | `bootstrap`, `functional-spec`, `spec-validation`, `technical-plan`, `implementation`, `spec-verification`, `retro`                                                                              | `discovery`, `test-design`                                                                              | `sdd-state.yml`, `plan.md`, `backlog-plan.yml`, spec drafts, `trace.md`, `tech-plan.md`, `code.md`, `verification.md`, `retro.md` |
| `exhaustive` | Genuine-risk work: cross-team, contract changes, multi-repo, security-sensitive, regulated paths, or scope the agent genuinely cannot pin down after a reasonable attempt.                                                                                                                                                                   | All active lifecycle phases                                                                                                                                                                      | None                                                                                                    | All SDD artifacts                                                                                                                 |
| `smart`      | Adaptive delivery when the request does not map cleanly to one fixed track, or the user wants explicit control over which phases run. The orchestrator recommends a phase set and the user selects.                                                                                                                                          | Core (always): `bootstrap`, `implementation`, `spec-verification`, `retro`. Plus the user-selected subset of `discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`. | The optional phases the user does not select                                                            | Core artifacts (`sdd-state.yml`, `code.md`, `verification.md`, `retro.md`) plus the artifacts of every selected optional phase    |

Skipped phases must be recorded in `sdd-state.yml` with `status: skipped` and an evidence entry that names the reason (for example: `skipped: track=moderate; mechanical README change`). The deterministic linter already enforces that any non-`pending` gate carries evidence, so the skip rationale is auditable.

## Step 1 — Deterministic heuristics (first filter)

Apply these rules in order. The first match wins.

### Forced `exhaustive`

Override any other heuristic and choose `exhaustive` when **any** of the following holds. Keep this list to true risk signals — do not invent additional reasons to escalate:

- The change touches a public API, network contract, persisted schema, or message broker payload.
- The change crosses repository or team boundaries.
- The change touches paths the workspace marks as regulated or security-sensitive (configurable per workspace).
- The change requires a genuine product decision or stakeholder approval that the agent cannot responsibly make on its own. A request the agent can scope into a clear acceptance criterion does **not** qualify.
- The user request lacks a definable acceptance criterion and the agent genuinely cannot infer one after a reasonable attempt. Mild fuzziness that a senior engineer would resolve by stating the obvious success condition does **not** qualify.
- A previous session on the same area was reopened due to missing evidence.

### Suggested `simple`

Choose `simple` when **all** of the following hold:

- The change is trivially mechanical with a single obvious success condition the diff itself proves (typo, comment, log message, config constant, dependency patch bump).
- One repository, expected diff ≤30 LOC and ≤3 files.
- No behavior, API, schema, or contract changes; existing build/tests are enough validation.
- No plan is needed beyond the request sentence itself — a competent engineer would just make the change.

In `simple`, the implementation delegation records inline verification evidence in `code.md` (diff plus validation command) and there is no separate technical-plan or verification delegation. `retro` remains the closure/compound phase, as in every track.

### Suggested `moderate`

Choose `moderate` when **all** of the following hold and `simple` did not fit:

- Diff is expected to be small and self-contained.
- The work is mechanical, or a small well-understood behavioral change that maps to a single obvious acceptance criterion (documentation, comments, formatting, dependency bumps, configuration constants, trivial renames, or a localized fix/tweak with no contract impact).
- No new behavior crosses a public API, schema, or contract, and no existing acceptance criterion changes meaning.
- Existing tests cover the area or it is trivially testable, and a lightweight technical plan can describe the intended diff so verification/review can validate correctness.

### Default `complex`

If neither forced `exhaustive` nor suggested `moderate` matched, propose `complex` — this is the confident default for ordinary feature work. The semantic step only promotes to `exhaustive` when it surfaces concrete risk, not on mild uncertainty.

### When to offer `smart`

Offer `smart` when the deterministic and semantic filters do not converge on one fixed track, or when the user wants explicit control over which phases run. `smart` keeps the mandatory core (`bootstrap`, `implementation`, `spec-verification`, `retro`) and lets the user pick any subset of the optional phases (`discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`).

Do not offer `smart` to dodge a clear classification — when a fixed track plainly fits, propose it. Use `smart` for genuinely mixed needs (for example, a change that wants a technical plan and test design but no functional spec) or when the user asks to choose the phases.

When proposing `smart`, compute a **recommended phase set** from the same signals used for the fixed tracks, present it as the default selection, and let the user add or remove optional phases:

- Recommend `functional-spec` (and `spec-validation`) when the work needs an agreed acceptance contract or backlog/issue projection.
- Recommend `technical-plan` when the change benefits from a written implementation approach before coding.
- Recommend `test-design` when tests should be designed up front (requires `functional-spec`).
- Recommend `discovery` when the problem needs research before a spec.

Dependencies enforced by the CLI: `spec-validation` and `test-design` require `functional-spec`.

## Step 2 — Semantic confirmation (LLM)

Only runs when Step 1 did not force `exhaustive`. Answer each question decisively — a senior engineer commits to an answer rather than hiding behind "unsure." Promote one level (`simple` → `moderate`, `moderate` → `complex`, `complex` → `exhaustive`) only when **two or more** answers are "no" or genuinely "unsure"; a single soft doubt keeps the proposed track.

1. Can a single, observable acceptance criterion describe success?
2. Is the change reversible by a simple revert with no data migration?
3. Are existing automated tests sufficient to catch regressions, or is the affected area trivially testable?
4. Is the blast radius limited to the changed module?
5. Is there no need for product, security, or release approval beyond the verification?

## Step 3 — User confirmation

Show the proposed track, the rationale, and the skipped phases. Always include a one-line explanation of what each track means so the user can make an informed choice instead of just seeing track names:

- **`simple`** — Trivial mechanical change delivered by a single implementation pass with inline diff evidence (typo, comment, log tweak, config constant, dependency patch bump), closed by retro. Everything else is skipped.
- **`moderate`** — Mechanical, low-risk change with no functional decision (formatting sweep, rename without API impact, minor dependency bump). Skips discovery, functional spec, spec validation, and test design; goes straight from a lightweight technical plan to implementation and verification.
- **`complex`** — Balanced delivery: the work deserves a functional spec plus its validation (with backlog/issue projection) before planning, but still avoids a separate discovery phase and the formal test-design phase.
- **`exhaustive`** — Full SDD flow for genuine-risk work: cross-team or contract changes, multi-repo, security-sensitive, regulated paths, or scope that genuinely cannot be pinned down. All active phases are mandatory.
- **`smart`** — Adaptive: always runs coding, verification, and retro (plus bootstrap), and you choose which of research, functional spec, spec validation, technical plan, and test design to run. Use it when the work mixes needs or you want to pick the phases.

When referencing these phases, you must always explain them in a clear, and simple manner, without trying to over-complicate the explanation.

When the proposal is `smart`, also present the recommended optional phases (pre-selected) and let the user toggle them through the native ask mechanism (multiple-choice / multi-select when available), then pass the confirmed optional phases to `set-track` via `--phases`.

The user can:

- Accept the proposal.
- Force a different track (`--track=simple|moderate|complex|exhaustive|smart` or equivalent natural-language instruction; for `smart`, also name the optional phases to run).
- Defer the decision; the orchestrator then proceeds with the **proposed track** (the lightest one that safely fits). Fall back to `exhaustive` only when a forced-`exhaustive` signal from Step 1 applied — deferral is not a reason to escalate ordinary work.

Record the decision in `sdd-state.yml`:

- `track: <chosen>`
- `track_classification.decided_by`, `decided_at`, `rationale`, `signals` (list the heuristics or answers that drove the choice).
- An entry in `decisions[]` with the same rationale.

## Reclassification

- **Amendments (no extra state):** when a request modifies behavior an existing spec already covers, do not model it as a separate session kind — the session-local draft plus phase reopening already cover it. Reopen the owning phase (`discovery`, `functional-spec`, or `technical-plan`), modify the spec draft there, and continue forward through the normal machine; the retro consolidation records the change against the canonical spec with its version bump.

- **Reclassification** is allowed when a specialist finds new ambiguity, hidden scope, contract impact, cross-repository coordination, or another real scope/contract change. The orchestrator materializes any newly required artifacts and records the transition in `decisions[]`.
- **Verification/review failures do not promote the track.** Keep the existing track and route remediation to the appropriate phase: `implementation` for code/test/AC or blocking review findings, `spec-verification` for incomplete verification evidence, or `technical-plan` when the plan itself is insufficient.
- **Degradation** is allowed only when the user or orchestrator can justify it explicitly and no skipped phase had open blockers or unresolved acceptance criteria.
- **Automatic reclassification triggers**:
  - The diff materially exceeds the track budget (simple: >30 LOC or >3 files; moderate: >120 LOC or >5 files) and the extra surface carries real risk.
  - A change appears in API, schema, or contract files.
  - Cross-repository coordination becomes necessary.
  - The request turns out to modify behavior covered by an existing canonical spec.
  - The user explicitly requests a different track.

## Failure modes to avoid

- Choosing `moderate` to skip evidence for a change that affects users — this is a process violation, not a shortcut.
- Marking a phase as `skipped` without the reason in evidence; the linter will reject the gate.
- Mixing tracks across topics that should be split — when in doubt, split into two topics rather than picking the wrong track.

## Track Classification Checkpoint (orchestration procedure)

The orchestrator runs this checkpoint **only** when `track` is missing, malformed, explicitly overridden, or a reclassification trigger fires above. Do not run it on every resume when a valid track already exists in `sdd-state.yml`.

1. Apply Step 1 and Step 2 above to the user's stated goal only. Do not read repository content, source code, or architecture files to inform classification — that is specialist work.
2. If any forced-`exhaustive` rule matches, choose `exhaustive` and stop.
3. If the classifier is ambiguous, ask the user immediately using the native ask mechanism. Do not explore the workspace first.
4. Show the proposed track, the rationale, and the list of phases it will skip. Also include a one-line explanation of what each track means (Step 3 above) so the user understands the options instead of only seeing the track names. When the proposal is `smart`, present the recommended optional phases pre-selected and let the user toggle them. Wait for user confirmation; on refusal or deferral proceed with the proposed track, and fall back to the default.
5. Apply the classification with one CLI command:

   ```bash
    python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py set-track {session-dir} {track} --rationale "..." [--phases a,b] [--signals a,b] [--skip-reason "..."]
   ```

   It atomically sets `track` and `track_classification`, marks every skipped phase/gate with a skip-reason evidence entry, completes bootstrap with its artifacts registered, sets `current_phase` to the first non-skipped phase, records the `decisions[]` entry, and copies the matching trace template (`exhaustive`/`complex`/`moderate`/`simple`, or the pruned exhaustive base for `smart`) to `session/trace.md`. For `smart`, pass the user-selected optional phases via `--phases` (comma-separated): the CLI keeps the mandatory core active, marks unselected optional phases skipped, and prunes the trace to the selection. For a **reclassification** of an existing session (track already set), apply the changed fields through the CLI registry commands (`gate`, `decision-add`) and hand-edit only what no command covers, keeping already-produced artifacts registered.

Gate:

- [ ] `track` is one of `simple | moderate | complex | exhaustive | smart` and matches the classifier output or the explicit user override.
- [ ] `trace.md` matches the chosen track.
- [ ] Skipped phases each carry a skip-reason evidence entry.
