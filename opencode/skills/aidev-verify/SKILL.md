---
name: aidev-verify
description: AIDev spec verification and review workflow. Use when checking whether an implementation satisfies approved acceptance criteria, mapping ACs to executed or empirical evidence, producing the combined verification.md report, invoking technology verification adapters, or deciding whether a topic can move beyond verification in an AIDev lifecycle.
---

# aidev-verify - AIDev Spec Verification Contract

This skill verifies that an implementation satisfies the approved functional contract for the active AIDev framework. It is the quality gate after implementation: every acceptance criterion must have concrete evidence and a status, and any review contribution incorporated by the caller must have no blocking findings, before the topic can advance.

## Core rules

- Resolve the active framework before doing verification work.
- Write only the verification report owned by this phase. Do not edit framework state, trace files, specs, production code, or standalone review artifacts.
- Every acceptance criterion must appear exactly once in the verification matrix.
- A planned test, implementation intent, or `code.md` claim is not proof by itself. Evidence must be executed, observed, captured, or explicitly accepted as risk/deferred scope.
- Technology adapters own their own artifact capture and evidence-row semantics. This verifier invokes applicable adapters and includes their returned verification contribution blocks without reinterpreting adapter internals.
- Keep generated lifecycle artifacts and the minimal handoff manifest in English, even if the conversation is in another language.

## Inputs

- Active framework state or explicit caller-provided artifact paths.
- Approved spec file(s) from the active framework contract.
- Test design artifact.
- Implementation evidence artifact.
- Traceability artifact when the active framework provides one.
- Optional PR URL, local diff, executed command output, logs, screenshots, deployment evidence, or user/accountable-owner decisions.

## Output

Create or update the verification report at the active framework-defined verification path. In SDD this is `verification.md` in the current session.

The report must follow `assets/verification-template.md`. Each acceptance criterion must be marked as one of:

- `pass`
- `fail`
- `accepted-risk`
- `deferred`

## Evidence model

| Evidence ID   | Meaning                                                        |
| ------------- | -------------------------------------------------------------- |
| `EVID-TEST-N` | Executed evidence corresponding to a planned `TEST-N`          |
| `EVID-CODE-N` | Implementation evidence from diff, code journal, commit, or PR |
| `EVID-RUN-N`  | Direct verification command or externally supplied run log     |
| `EVID-SPA-N`  | Evidence produced by the SPA verification adapter              |
| `EVID-WSC-N`  | Evidence produced by the WSC/backend verification adapter      |

Rules:

- Every `AC-N` row must cite at least one nearby `EVID-*` ID.
- Evidence IDs must point to concrete sources: command logs, screenshots, videos, diffs, test reports, or explicit accountable-owner decisions.
- Do not mark an AC as `pass` when all evidence is planned, missing, stale, contradictory, or only indirectly related.
- Use `accepted-risk` only when the accountable owner explicitly accepts incomplete evidence.
- Use `deferred` only when the AC is explicitly moved out of current scope and the active framework can trace that decision.

## Workflow

### Step 1 - Resolve topic and evidence sources

1. Apply the active framework resolution rules above.
2. Read the active framework's test design, implementation evidence, and traceability artifacts.
3. Confirm required files exist. If a required file is missing, record a blocker unless the active framework or track explicitly skips it.

Gate:

- [ ] Active framework or explicit caller paths are resolved.
- [ ] At least one approved spec or spec-draft is available, unless the active framework explicitly allows no requirements for the active track.
- [ ] Test design, implementation evidence, and traceability are available when required by the active framework.

### Step 2 - Extract acceptance criteria

1. Read every approved spec from the active framework artifacts.
2. Extract every `AC-N` acceptance criterion in source order.
3. Preserve existing IDs and wording. Do not rewrite criteria to make verification easier.
4. Record any duplicated, missing, or malformed AC IDs as blockers.

Gate:

- [ ] Every AC has a stable `AC-N` ID.
- [ ] No acceptance criterion is skipped.

### Step 3 - Build the initial evidence matrix

For each AC:

1. Link planned tests from the test design.
2. Link implementation evidence from the code journal, trace artifact, PR, or local diff.
3. Link externally supplied logs or command outputs.
4. Mark evidence gaps, stale evidence, contradictions, or missing implementation proof.

Gate:

- [ ] Every AC appears exactly once in the matrix.
- [ ] Every AC has concrete evidence, an adapter target, or a documented evidence gap.

### Step 4 - Invoke technology adapters

Technology adapters are consolidated as progressive-disclosure references under `references/`. Load the matching adapter reference only after detecting its context, then follow that reference's own contract.

| Context               | Signals                                                                                                                                                                           | Adapter reference (load on demand) |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| SPA / web UI          | Browser-visible journey, route, page, form, component interaction, React, Angular, Vue, Svelte, Vite, webpack, Playwright, Cypress, Vitest, Jest, frontend `package.json` scripts | `references/aidev-verify-spa.md`   |
| WSC / backend service | `wsc-*`, backend API, service logic, REST/HTTP contract, controller, repository, queue, database, Maven, Gradle, npm backend, Go, Python service tests                            | `references/aidev-verify-wsc.md`   |

Loading is mandatory, not advisory. "Load" means you must open and read the reference file from disk in this run. Producing adapter-shaped output without first reading the matching reference file is a process failure, not a shortcut.

Once loaded, the adapter reference defines its own evidence capture and verification contract. Follow that contract exactly, including any visual/manual confirmation steps, and do not reinterpret the adapter's internal artifacts.

1. Detect applicable technology contexts from specs, test plan, implementation evidence, repo files, and user-provided evidence.
2. For each matched context, load the corresponding adapter reference from the table above and execute it with the active framework/session inputs and adapter-specific inputs. Do not load a reference whose context is not present.
3. Let each adapter capture its own artifacts according to its own contract.
4. Use the adapter's structured contribution block as verification-ready evidence. Do not inspect or reinterpret adapter-specific artifact internals unless the adapter asks for visual/manual confirmation as part of its own contract.
5. If a matched context has no available adapter reference, record the gap and rely on safe executed evidence.

Gate:

- [ ] Every matched context was handled by its adapter reference or recorded as a gap.
- [ ] Only the adapter references whose context was detected were loaded.
- [ ] Adapter results are present for every invoked adapter.

### Step 5 - Execute remaining safe evidence

Run only specific commands that are:

- named by the test plan, code journal, or caller;
- not already owned by an invoked adapter;
- safe for the current environment; and
- necessary to close an AC evidence gap.

Capture command, result, log source, and linked ACs. Do not run broad, destructive, deployment, migration, or environment-mutating commands.

Gate:

- [ ] Runnable evidence was executed or explicitly documented as not runnable.
- [ ] No AC remains without a status.

### Step 6 - Author verification sections

1. Read `assets/verification-template.md`.
2. Create or update the active framework's verification report.
3. Fill the verification-owned sections with concrete evidence and status decisions:
   - Topic
   - Verification Summary
   - Artifact Index
   - Adapter Reference Disclosure
   - Acceptance Criteria Verification
   - Evidence Reviewed
   - Empirical Evidence
   - SPA/WSC or other adapter evidence
   - Command Results
   - Adapter Results
   - Open Findings
   - Gate Decision with verification status
   - VCP Screenshot Annex when applicable
4. Do not write the `## Review` section yet.
5. Do not leave placeholders such as `[AIDEV_TODO]` in any verification-owned section.
6. Reference every artifact as a clickable filename-only link (for example `[verify-login.webm](verification_artifacts/videos/verify-login.webm)`), never as a raw path in plain text. Register only verification-produced artifacts in the `## Artifact Index` section with an **Open** link.

Gate:

- [ ] The verification-owned sections of `verification.md` exist and the ones not owned by it remain unwritten.
- [ ] Every AC is `pass`, `fail`, `accepted-risk`, or `deferred`.
- [ ] Every AC row cites concrete `EVID-*` evidence or an accepted/deferred decision.
- [ ] Every referenced verification-produced artifact uses a filename-only link and appears once in the `## Artifact Index`. Repository source files are linked inline and excluded from the index.
- [ ] Tests, VCPs, adapter evidence, command evidence, and empirical evidence are captured or explicitly documented before review starts.

### Step 7 - Finalize combined verification report

1. Ensure adapter-provided section additions, evidence rows, and AC status suggestions remain in the verification-owned sections without changing their meaning.
2. Update the combined gate decision so it reflects both AC verification and review findings.
3. Persist the AC summary, evidence IDs, command outcomes, review result, risks, and blocker IDs in `verification.md`, then return the minimal verification manifest.

Gate:

- [ ] The verification report exists.
- [ ] The combined gate decision reflects both AC verification and review findings.
- [ ] No section contains placeholders such as `[AIDEV_TODO]`.

## Constraints

- Do not modify production code.
- Do not rewrite specs or acceptance criteria.
- Do not mark an AC as `pass` without concrete evidence.
- Do not ignore missing tests or missing adapter proof.
- Do not create or update `review.md`.
- Do not pass the combined gate while any AC is `fail`.
- Do not pass the combined gate while the run is `process-incomplete` because a detected adapter context's reference was not read.
- Do not pass the combined gate while any review finding is blocking.
- Do not treat generated adapter artifacts as self-validating if the adapter reports `fail` or `blocked`.

> **Artifact reference convention.** Always reference an artifact as a clickable filename link that shows only the file name, e.g. `[verify-login.webm](verification_artifacts/videos/verify-login.webm)` instead of pasting the raw `verification_artifacts/videos/verify-login.webm` path as plain text. Every verification-produced artifact you cite must also appear exactly once in the [Artifact Index](#artifact-index) with an **Open** link. Repository source files must be linked inline and must not be registered in the [Artifact Index](#artifact-index).

## Asset manifest

| Asset                            | Path                                                  | Load when                                                                                                         |
| -------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Verification template            | `skills/aidev-verify/assets/verification-template.md` | Before writing the verification-owned sections of `verification.md`                                               |
| SPA verification adapter         | `skills/aidev-verify/references/aidev-verify-spa.md`  | Mandatory read when a SPA / web UI context is detected in Step 4, before any SPA adapter-backed work              |
| WSC/backend verification adapter | `skills/aidev-verify/references/aidev-verify-wsc.md`  | Mandatory read when a WSC / backend service context is detected in Step 4, before any backend adapter-backed work |

## Completion response

Report:

1. Verification report path.
2. AC status summary.
3. Evidence reviewed, including adapter summaries.
4. Open blockers, accepted risks, or deferrals.
5. Gate recommendation and whether the topic can move to the next non-skipped phase when accepted by the orchestrator.
