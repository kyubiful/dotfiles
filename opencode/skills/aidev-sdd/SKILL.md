---
name: aidev-sdd
description: Standard Spec-Driven Development (SDD) workflow contract for Inditex agentic development. Use when starting, resuming, orchestrating, or validating an SDD session; when deciding the next SDD phase; when creating session state, traceability, spec validation, or workflow gates; or when a user asks for standard SDD, spec-driven development, SDD orchestration, spec lifecycle, or SDD framework guidance.
---

# aidev-sdd - Standard SDD Contract (Session-Based)

This skill defines the standard Spec-Driven Development workflow used by the AIDev SDD framework. It is the contract that orchestrators and specialist agents follow. Deliverables are the source of truth; GitHub issues, PRs, releases, and dashboards are projections of the workflow, not the workflow itself.

You will treat this as your framework and follow diligently the instructions, rules, and contracts defined here. When in doubt, refer back to this document for guidance on how to proceed. This is your source of truth for how to operate within the SDD framework.

## Skill resource paths

`<agent-dir>` is the agent installation directory that contains the `skills/` directory for this loaded skill. Its concrete path depends on the assistant currently running and must use that assistant's own resource layout inside `$CWD`; never hard-code or assume a layout for a particular assistant. `$CWD` is the directory where the assistant was started and therefore its working directory. Replace `<agent-dir>` with the runtime-specific directory before reading a resource or running a bundled script. Never pass the placeholder literally to a tool or shell.

## Core rules

- The framework defines phases, gates, artifacts, and transitions. `aidev-sdd` provides the contract, templates, and deterministic validation; it does not execute specialist phases itself.
- **Specs** are the stable, versioned source of truth. They live at `.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/spec.md` and survive across sessions until explicitly retired by a completed Retro.
- **Sessions** are time-bounded execution units. They live at `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{slug}/`. Each session has its own `sdd-state.yml`, `contracts.yml`, and traceability artifacts.
- Every session must have explicit state in `sdd-state.yml`; do not infer completion only from file presence.
- Every lifecycle timestamp written to `sdd-state.yml` must be the orchestrator's current UTC ISO-8601 timestamp at write time (for example, `2026-06-22T14:37:12Z`). Never persist template placeholders or zeroed `T00:00:00Z` defaults.
- Every new session must declare a `track` (`simple`, `moderate`, `complex`, `exhaustive`, or `smart`) chosen by the orchestrator during initialization. The track selects which phases are mandatory, skipped, or optional. See `<agent-dir>/skills/aidev-sdd/references/track-classifier.md`.
- Every acceptance criterion must be traceable to test design, implementation evidence, verification result, and release status, except when the session's track explicitly skips a phase and records the skip rationale as gate evidence.
- Backlog representation lives in `backlog-plan.yml`. GitHub issues must be generated from `backlog-plan.yml` and source specs, never maintained as an independent functional source.
- Presenting (offering) the change-aware backlog projection to the user is part of `functional-spec` planning whenever a projection is generated, and the user's publish decision must be recorded. Publishing is optional only in that the user may **decline** it — it is never forced on them. Once the user **approves** publishing, executing it (creating or updating the GitHub issues for the approved items) is part of completing `functional-spec` and must not be deferred or skipped. "Never required for the SDD critical path" means a _decline_ or a publish _failure_ does not halt SDD; it does not authorize ignoring an approved publish.
- Specialist agents own phase content and return minimal manifest paths. The orchestrator owns semantic gate judgment, sequencing, and track selection; the state CLI owns accepted writes to `sdd-state.yml` and derived `trace.md` views.
- The orchestrator mutates `sdd-state.yml` and `contracts.yml` **through the state CLI** (`<agent-dir>/skills/aidev-sdd/scripts/sdd-state.py`), never by hand-editing YAML. The CLI generates real UTC timestamps, validates every transition against the deterministic linter before committing (failing mutations roll back), and instruments `metrics.phases[]` automatically. Hand-editing is a fallback only when the CLI lacks the needed operation, and must be followed by `<agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py session`.
- Before the final delivery/evaluation gate can be accepted, the orchestrator must ask the user whether the implemented result is acceptable. This is a pre-retro checkpoint, not a phase or state transition override; record the answer in `decisions[]`, and record gate failure evidence only when the user requests changes.
- Before the session can be marked complete, the orchestrator must ask the user whether the retro result is acceptable and whether to finish the SDD session. This is a post-retro checkpoint, not a phase or state transition override; record the answer in `decisions[]`, and re-run `retro` when the user requests retro changes.
- Delegated specialists load `<agent-dir>/skills/aidev-sdd/references/specialist-contract.md` as their complete framework contract; this SKILL.md is the orchestrator playbook and is never injected into specialist prompts.
- Open questions from delegated specialists are workflow blockers, not optional conversation. The specialist writes a `subagent-question-envelope` file under its session `delegations/` directory and returns only that path. The orchestrator records the path in `sdd-state.yml` under `orchestration.pending_delegation` through the state CLI, keeps `current_phase` unchanged, marks the phase `blocked`, and marks the gate `paused` until the pending delegation is resolved.
- You operate inside of `$CWD`. All agents that have this skill must respect that contract and not read or write files outside of the current working directory and its subdirectories. If you read or write files over this boundary you risk breaking the contract with other agents and causing the workflow to fail in unexpected ways. `$CWD` is the only context you have access to. YOU must not look for files or directories outside of it.

## Stable spec packages

A spec is a stable functional definition stored at:

```
.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/
├── spec.md
└── changes/
    ├── changes.json
    └── {YYYYMMDD}-{session-slug}.md
```

- `{domain}` is the functional/business domain the spec belongs to (e.g. `checkout`, `inventory`, `identity`) — the product area that owns the capability, never a technical or catch-all bucket. There is **no default domain**; a value such as `general` is not allowed. When the spec's domain already exists under `specs/`, the spec simply resides inside that existing domain; a new domain directory is created only when the spec genuinely opens a new functional area. If the correct domain cannot be determined, resolve it with the user rather than inventing a placeholder.
- `{spec-name}` is the slug of the capability the spec defines, unique within its `{domain}`.
- `spec.md` is the approved spec with acceptance criteria. Once approved, it is the source of truth.
- `changes/` contains the changelog for that spec. `changes.json` is the registry of which sessions changed the spec, capturing per-change provenance (session, model, user, timestamp) and resource versioning (`spec_version`/`previous_version`). See **Approve spec changes**.
- `{YYYYMMDD}-{session-slug}.md` is a per-session change note explaining what changed, why, and briefly how.

Specs are session-agnostic. They are referenced by sessions through `sdd-state.yml.specs[].path`. Specs are authored during `functional-spec` and may be expanded, refined, or created during `retro` when a session proves durable knowledge that belongs in the canonical contract; every such change follows **Approve spec changes**.

During an active session, the working version of a spec is a **session-local draft** at `sessions/{session-id}/specs/{domain}/{spec-name}/spec.md`. The draft carries the session's intent and is what `sdd-state.yml.specs[]` points to while delivery phases run. When Retro consolidates it at cycle close, transactional acceptance repoints that entry to the workspace-scoped canonical package.

**Spec existence rule:** A session's `sdd-state.yml` references the spec versions the session works on. A new or modified spec is authored as a session-local draft under `sessions/{session-id}/specs/{domain}/{spec-name}/spec.md`, approved at the `functional-spec` gate, and added to `sdd-state.yml.specs[]` pointing at that draft. After Retro acceptance, the entry points to the existing canonical workspace artifact instead. Every listed path must identify an approved file that exists on disk.

**Spec path format:** Each `sdd-state.yml.specs[]` entry declares `scope: session | workspace`; its relative `path` is resolved against that root and must not use `..`. Active drafts use `scope: session` with `specs/{domain}/{spec-name}/spec.md`. Consolidated canonical specs use `scope: workspace` with `.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/spec.md`.

**Removing a spec:** Dropping a draft the session was only working on deletes its session-local draft (and any staging file), its `backlog_items` entry, and its `sdd-state.yml.specs[]` reference. On a functional-spec revision, the planner declares the existing scoped reference in `spec_removals`, and `accept-handoff` applies it transactionally. Retiring a previously standardized spec is reflected as a `change_kind: removed` backlog item. At Retro, the specialist records the retirement in `retro.md`, removes the complete canonical package (including `changes/`), and declares the absent package plus the state reference through `spec_deletions`. Neither case acts on GitHub issues, so any previously published issue is left untouched.

## Session structure

A session directory contains:

```
sessions/{YYYYMMDD}-{slug}/
├── sdd-state.yml       # Orchestrator-owned session state
├── contracts.yml       # Input contract manifest
├── contracts/          # Raw contract files (images, PDFs, captured artifacts)
│   ├── screenshot.png
│   ├── designs/
│   └── ...
├── plan.md             # Planning session artifact
├── backlog-plan.yml    # Backlog projection
├── trace.md            # Orchestrator-owned traceability
├── research.md         # Discovery output (if applicable)
├── tech-plan.md        # Technical plan (if applicable)
├── test-plan.md        # Test design (if applicable)
├── code.md             # Coding journal
├── verification.md     # Spec verification matrix and review
├── retro.md            # Retrospective (if applicable)
├── delegations/        # Specialist-created question envelopes while pending
├── handoffs/           # Minimal reference-based specialist manifests
├── specs/{domain}/{spec-name}/
│   └── spec.md                          ← session-local spec draft (planner-owned)
└── spec-drafts/
    └── {spec-name}.md  # Draft specs (planner-owned)
```

The orchestrator is the lifecycle authority for `sdd-state.yml` and `trace.md`. Specialist agents write their owned artifacts and return a minimal manifest path; `accept-handoff` performs accepted writes and registers artifacts under `phases.<phase>.artifacts[]`. There is no root `artifacts` registry.

The canonical `specs/` packages are authored as session-local drafts during `functional-spec` and written to the canonical path at cycle close; the orchestrator records the resulting `sdd-state.yml` pointer changes.

## `contracts.yml`

`contracts.yml` is the session-level manifest of input contracts. No closed type system; `media_type` describes the content but does not constrain it.

Field definitions and the full semantic contract lifecycle are documented in `<agent-dir>/skills/aidev-sdd/references/contracts-guide.md`. Load that guide when processing or validating contracts. Delegated specialists honor relevant contract entries as read-only inputs and persist semantic mappings in their owned artifacts; only the orchestrator mutates `contracts.yml` or promotes new contract files.

Fields per contract entry:

- `id` — unique within the file
- `title` — human-readable name
- `path` — relative to session directory, no `..`; must be inside the `contracts/` subdirectory
- `media_type` — MIME type or descriptive string
- `sha256` — required for integrity
- `source` — origin description
- `captured_at` — ISO timestamp
- `links[]` — optional related paths (relative to session)
- `summary` — brief description
- `metadata` — free-form annotations

**Binding rule:** Every contract listed in `contracts.yml` is a non-negotiable requirement. It represents hard evidence — for example an OpenAPI definition, a UI screenshot, a PDF requirement document, or a data schema — that the spec must satisfy. If a contract does not apply, remove its entry from `contracts.yml` rather than marking it with a status.

If you are dealing with a freshly mentioned contract, review the guide at `<agent-dir>/skills/aidev-sdd/references/contracts-guide.md` to understand the lifecycle, traceability rules, and handling of unmappable contracts.

If you are dealing with an existing contract, make sure to take it into account accordingly regarding your task at hand and your target goal.

Contracts create no requirements by themselves. If something from a contract must be enforced, it must appear in a spec's acceptance criteria.

## Workspace preflight

Workspace preflight validates repository architecture and repo-local `AGENTS.md` guidance across `repos/`. The deterministic command `sdd-state.py preflight {session-dir} --validator {path}` persists `orchestration.workspace_preflight` atomically: `ready` when every repository passes and `blocked` with per-repository reasons otherwise. The validator accepts `--workspace {root}` and emits `PASS`/`FAIL` per repository plus a `summary:` line.

Preflight operates at `$CWD`, outside the per-session phase machine; `orchestration.workspace_preflight` is metadata, never a phase, gate, or trace artifact. The **AIDevOrchestrator** owns all preflight lifecycle decisions, including refresh, initialization, and handoff handling; the handoff shape is in `<agent-dir>/skills/aidev-sdd/references/workspace-preflight-handoff-contract.md`.

## Legacy layout migration

Workspaces created by earlier framework versions may use a **legacy layout** — either topic directories straight under `.aicontext/deliverables/sdd/{topic}/` or specs grouped inside sessions (`sessions/{id}/specs/...`) — with no canonical, versioned `specs/` store. The orchestrator must not reconcile that itself — reading across every legacy directory and spec breaks its thin/read-restricted contract and burns context.

This check is **mandatory and runs on every session resolution** once `sdd-state.yml` exists. The startup order is fixed: after reading `sdd-state.yml`, the orchestrator resolves `orchestration.pending_delegation` first when present; once that blocker is clear, it runs the **cheap, listing-only probe** of `.aicontext/deliverables/sdd/` (one directory listing, no file-body reads) before any track classification, workspace preflight, validation, or phase routing. When legacy signals appear, it delegates the whole detection-plus-migration to a **generic subagent**. The probe rules, migration procedure, subagent invocation, handoff, and persistence all live in `<agent-dir>/skills/aidev-sdd/references/sdd-layout-migration.md`; load it whenever `orchestration.layout_migration` is absent or the listing shows anything other than `specs/` and `sessions/` directly under `sdd/`.

Like workspace preflight, this is **outside the phase machine**: never `current_phase`, `phases`, `gates`, or `trace.md`. The result is recorded only as `orchestration.layout_migration` metadata, and the orchestrator applies any active-session `specs[].path` repoints the subagent proposes. A recorded `migrated`/`no_migration_needed` result lets later resolutions skip the dispatch (the cheap listing still runs).

## Tracks

The framework supports five tracks inside the same contract. Tracks change which phases are mandatory; they do not change the artifact format, the linter, or the gate semantics.

| Track        | Mandatory phases                                                                                                                                                                                 | Skipped by default                                                                                      | Use for                                                                                                                                                                                                                                   |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simple`     | `bootstrap`, `implementation`, `retro`                                                                                                                                                           | `discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`, `spec-verification` | Trivial mechanical change a single implementation pass delivers and proves with inline diff evidence in `code.md` (typo, comment, log tweak, config constant, dependency patch bump). `retro` closes and compounds, as in every track.    |
| `moderate`   | `bootstrap`, `technical-plan`, `implementation`, `spec-verification`, `retro`                                                                                                                    | `discovery`, `functional-spec`, `spec-validation`, `test-design`                                        | Mechanical, low-risk changes that still deserve a lightweight plan and separate verification. `retro` is the closure/compound phase for this track.                                                                                       |
| `complex`    | `bootstrap`, `functional-spec`, `spec-validation`, `technical-plan`, `implementation`, `spec-verification`, `retro`                                                                              | `discovery`, `test-design`                                                                              | Balanced: functional spec plus validation followed by technical planning, coding, verification, and retro closure. Test evidence design is folded into `spec-verification` — the verifier designs and executes evidence in one roundtrip. |
| `exhaustive` | `bootstrap`, `discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`, `implementation`, `spec-verification`, `retro`                                                  | None                                                                                                    | Genuine-risk work: contract or schema changes, cross-team/multi-repo, security-sensitive, or scope the agent genuinely cannot pin down.                                                                                                   |
| `smart`      | Core (always): `bootstrap`, `implementation`, `spec-verification`, `retro`. Plus any user-selected subset of `discovery`, `functional-spec`, `spec-validation`, `technical-plan`, `test-design`. | The optional phases the user does not select                                                            | Adaptive delivery with no fixed phase set: the orchestrator recommends a phase set from the request and the user selects which to run. `spec-validation` and `test-design` require `functional-spec`. Set via `set-track smart --phases`. |

Rules that apply to every track:

- A skipped phase records `status: skipped` in both `phases` and `gates`. The gate must include an `evidence` entry that names the skip reason (for example: `skipped: track=moderate; mechanical formatting change`). The deterministic linter rejects any non-`pending` gate that lacks evidence, so the skip rationale is always auditable.
- Reclassification is allowed only for real scope or contract changes, or when the user explicitly requests a different track. Verification/review failures do not promote the track; they keep the same track and route remediation to the appropriate phase.
- Degradation requires an explicit decision recorded in `decisions[]` and is allowed only when no skipped phase had open blockers.
- The classifier (`<agent-dir>/skills/aidev-sdd/references/track-classifier.md`) is the canonical reference for track selection, including the Track Classification Checkpoint orchestration procedure. Run it whenever `track` is missing, malformed, explicitly overridden, or a reclassification trigger fires.

## Workspace cache

`.aicontext/.cache/` holds cross-session, regenerable working data that must never be treated as a deliverable. Standard entries:

| Cache path                                              | Producer                | Content                               | Invalidation                                                             |
| ------------------------------------------------------- | ----------------------- | ------------------------------------- | ------------------------------------------------------------------------ |
| `.aicontext/.cache/gh-issues/{owner}/{repo}/{issue}.md` | tech-planner and others | Cached GitHub issue bodies            | Refetch when the issue is the requirement source of a new session        |
| `.aicontext/.cache/repo-detection/{repo}.json`          | explore/init tooling    | Stack/build detection output per repo | Stale when the repo's lockfiles, build files, or `.tool-versions` change |
| `.aicontext/.cache/mcp-discovery.yml`                   | research                | Discovered MCP source inventory       | Stale after 7 days or when the configured MCP set changes                |

Agents consult the cache before re-running discovery/detection work and refresh entries they find stale. Cache reads are always optional — a missing cache entry simply means doing the work and populating it. Never store secrets or user decisions in the cache; decisions belong in `sdd-state.yml`.

## Session artifacts

| Artifact                | Required when          | Purpose                                                                                                                                |
| ----------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `sdd-state.yml`         | Bootstrap              | Session state, current phase, gates, phase artifact lists, decisions                                                                   |
| `contracts.yml`         | Bootstrap              | Input contract manifest for the session                                                                                                |
| `research.md`           | Discovery              | Validated problem context, constraints, alternatives                                                                                   |
| `plan.md`               | Functional Spec        | Planning session artifact and spec registry                                                                                            |
| `spec-drafts/{name}.md` | Functional Spec        | Draft specs during planning                                                                                                            |
| `spec-relations.md`     | Functional Spec        | Inter-spec relations (if multi-spec session)                                                                                           |
| `spec.md` (stable)      | Functional Spec        | Functional contract and acceptance criteria                                                                                            |
| `backlog-plan.yml`      | Functional Spec        | Backlog and roadmap projection derived from approved specs                                                                             |
| `trace.md`              | Spec Validation onward | AC to test to code to PR to release traceability                                                                                       |
| `tech-plan.md`          | Technical Plan         | Implementation approach derived from the active requirement source: stable spec, research, prompt, or track-specific mechanical change |
| `test-plan.md`          | Test Design            | AC-driven test matrix and expected evidence                                                                                            |
| `code.md`               | Implementation         | Coding journal and implementation evidence                                                                                             |
| `verification.md`       | Spec Verification      | AC pass/fail evidence matrix with functional, technical, bug, rules, and security review                                               |
| `retro.md`              | Retro                  | Lessons learned and framework improvement actions                                                                                      |

Session artifact paths in state remain session-relative list entries. Workspace-scoped artifacts use a `workspace:` prefix. Spec registry entries declare `scope: session | workspace` explicitly.

## Artifact signatures

Each specialist agent must sign its owned artifact by running `<agent-dir>/skills/aidev-sdd/scripts/signature-append.py` before returning its handoff — the script resolves the lock-derived fields and replaces an existing table idempotently; the agent self-reports only `--assistant` and `--model`. The signed/unsigned artifact list and the participant-extraction contract are defined in `<agent-dir>/skills/aidev-sdd/references/artifact-signature.md`.

## Persistent clarification state

Delegated specialist clarification state is represented by `orchestration.pending_delegation`.

`sdd-state.yml` may include `orchestration.workspace_preflight` metadata and `orchestration.pending_delegation` clarification state. The preflight metadata is owned by the orchestrator and is not part of the phase machine.

Pending delegation example:

```yaml
orchestration:
  pending_delegation:
    round: 1
    delegation_id: "planner.target_repo.2026-06-08"
    agent: AIDevTechPlanner
    phase: technical-plan
    envelope_artifact_path: .aicontext/deliverables/sdd/sessions/{session-id}/delegations/planner.target_repo.2026-06-08-questions.md
```

When this block is present:

- `pending_delegation.phase` must equal `current_phase`.
- `phases.<current_phase>.status` must be `blocked`.
- `gates.<current_phase>.status` must be `paused` and include evidence.
- The orchestrator must resolve `pending_delegation` before routing or advancing any other phase.
- Keep a question envelope immutable while it is pending. `resume-handoff` transfers its complete context to the active request, clears `pending_delegation`, and deletes the consumed envelope atomically before the specialist is re-entered.

## Delegated-question integration

The delegated-question lifecycle—immutable-envelope validation and registration, user presentation, answer mapping, transient resume-packet construction, resolution, and subsequent rounds—is owned by the appropriate skill.

This skill owns the persistent SDD data contract above and the `pause-handoff`/`resume-handoff`/`retry-handoff` CLI operation semantics in **State mutation CLI**.

## Standard phase machine

The orchestrator uses this table as the authoritative dispatch reference. `bootstrap` and `spec-validation` are orchestrator-owned; the orchestrator performs those steps directly rather than delegating to a specialist.

| Phase               | Agent to invoke                                                        | Artifact produced                                      | Gate                                                                                                                                                                                                                                                                                                                                                            | Orchestration notes                                                                                                                                                                                                                                                                                                                                                             |
| ------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bootstrap`         | `AIDevOrchestrator` (session init) + `AIDevInit` (workspace preflight) | `sdd-state.yml`, `contracts.yml`, `trace.md`           | `sdd-state.yml`, `contracts.yml`, and `trace.md` exist, session identity is set, workspace preflight is initialized and valid, and bootstrap is explicitly marked complete                                                                                                                                                                                      | Orchestrator creates session state with `current_phase: bootstrap`; `AIDevInit` runs workspace preflight. Move to `discovery` after initialization.                                                                                                                                                                                                                             |
| `discovery`         | `AIDevResearcher`                                                      | `research.md`                                          | Research is validated or explicitly skipped for direct specs                                                                                                                                                                                                                                                                                                    | Skip and advance to `spec-validation` when the user provides an already-approved spec.                                                                                                                                                                                                                                                                                          |
| `functional-spec`   | `AIDevPlanner`                                                         | `plan.md`, `spec-drafts/{name}.md`, `backlog-plan.yml` | Spec approved, ACs complete, and — when specs are planned for roadmap — the backlog projection is generated **and offered** with the publish decision recorded; and when the user **approved** publishing, the approved items are actually published (issue reference present, `sync_status: synced`) or the publish failure is recorded as an explicit blocker | Planner must map every contract in `contracts.yml` to ≥1 AC or escalate as a blocker if unmappable. The projection offer is part of planning. Publishing is optional only in that the user may decline it; an approved publish must be executed before the gate passes — `sdd-lint.py backlog` verifies that approved items carry an issue reference and `sync_status: synced`. |
| `spec-validation`   | `AIDevOrchestrator` (no delegation)                                    | — (validates and advances state)                       | Spec, backlog plan, derived trace, and coverage pass deterministic validation                                                                                                                                                                                                                                                                                   | Run the deterministic validation contract and advance; no specialist handoff exists for this phase.                                                                                                                                                                                                                                                                             |
| `technical-plan`    | `AIDevTechPlanner`                                                     | `tech-plan.md`                                         | Tech plan approved and tied to the spec                                                                                                                                                                                                                                                                                                                         | —                                                                                                                                                                                                                                                                                                                                                                               |
| `test-design`       | `AIDevTester`                                                          | `test-plan.md`                                         | Each AC has planned test/evidence coverage                                                                                                                                                                                                                                                                                                                      | Derive AC-driven test evidence before implementation begins.                                                                                                                                                                                                                                                                                                                    |
| `implementation`    | `AIDevCoder`                                                           | `code.md`                                              | Build, lint, PaaS configuration, validation, commit, and coding journal evidence pass                                                                                                                                                                                                                                                                           | Begins once test design exists or is deferred with rationale.                                                                                                                                                                                                                                                                                                                   |
| `spec-verification` | `AIDevVerifier`                                                        | `verification.md`                                      | Each AC has pass, accepted-risk, or deferred status and no blocking review findings remain open                                                                                                                                                                                                                                                                 | Prove every AC has evidence, then append the final review. When a GitHub PR exists, run the **PR delivery decision** before the pre-retro checkpoint.                                                                                                                                                                                                                           |
| `retro`             | `AIDevRetro`                                                           | `retro.md`                                             | Durable product knowledge compounded into product context resources and specs consolidated                                                                                                                                                                                                                                                                      | Capture product lessons and dead ends, compound durable knowledge into the target product's `ARCHITECTURE.md`/`AGENTS.md`, consolidate canonical specs, and close the session. Never write SDD-framework internals into product resources.                                                                                                                                      |

## Initialize a session

When the orchestrator creates a new SDD session, it follows:

1. Derive `{slug}` as short kebab-case from the user's goal, then run `sdd-state.py init {sessions-root} {slug} --name "{name}"`. The CLI derives the date, forms the session id, rejects collisions, and fills identity plus real UTC timestamps from the template.
2. Classify the session using `<agent-dir>/skills/aidev-sdd/references/track-classifier.md` and present the proposal inside the consolidated kickoff batch. Bias toward the lightest track that safely fits; reserve `exhaustive` for genuine risk rather than mild uncertainty.
3. Run `sdd-state.py set-track {session-dir} {track} --rationale "..." [--phases ...] [--signals ...]`. The CLI atomically: sets `track` and `track_classification`, marks every skipped phase/gate with skip-reason evidence, copies the matching trace template (`exhaustive`/`complex`/`moderate`/`simple`, or the pruned exhaustive base for `smart`), completes bootstrap with its artifacts registered, sets `current_phase` to the first non-skipped phase, and records the decision. For `smart`, `--phases` carries the user-selected optional phases.
4. Persist the execution mode: when the user requests unattended execution, run `sdd-state.py set-mode {session-dir} autopilot`; otherwise leave the template default (`execution_mode: interactive`). The mode governs chained delegation and is reported by every `status`/`next`/`accept-handoff` output, so it survives session resumes.
5. Fill the trace `Session` section fields known at bootstrap (session id, track, current phase, `Source spec` when an approved spec already exists). Replace `[AIDEV_TODO]` with `N/A`/`skipped` only in sections owned by skipped phases; leave placeholders in sections owned by phases the track will run.
6. **Lazy contracts:** register input contracts with `sdd-state.py contract-add` at the first moment a contract is actually provided or referenced — never ceremonially at bootstrap. The CLI creates `contracts.yml` from the template, computes the sha256, and registers the manifest under bootstrap artifacts. A missing `contracts.yml` means an empty manifest.
7. Start the first delegated phase with `sdd-state.py phase-start {session-dir} {phase}` (metrics start automatically).

## State mutation CLI

`<agent-dir>/skills/aidev-sdd/scripts/sdd-state.py` is the single public CLI for lifecycle state, contracts, specialist request construction, resumption, and manifest materialization. Generated requests preserve `<agent-dir>` as a specialist-resolved placeholder and use workspace-relative paths. **This section is the single source for CLI command syntax.**

```bash
# Handoff request, pause/resume, and result materialization
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py create-handoff {session-dir} --expect-phase {phase} --need "..." [--context {path} "..."] [--policy {key} "..."]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py pause-handoff {session-dir} {phase} {agent} {delegation-id} {envelope-path}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py resume-handoff {session-dir} --expect-phase {phase} --answer {id} {selected|none} "..." [--answer ...]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py retry-handoff {session-dir} --expect-phase {phase} --finding "..." [--finding "..." ...]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py submit-handoff {session-dir} --expect-phase {phase} --status {ready|blocked} [phase-specific repeated flags]

# Session lifecycle
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py init {sessions-root} {slug} --name "{name}"
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py set-track {session-dir} {track} --rationale "..." [--signals a,b]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py status {session-dir}          # compact read — use instead of reading the YAML
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py set-mode {session-dir} {interactive|autopilot}  # persist the session execution mode
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py session-complete {session-dir}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py metrics {session-dir}

# Phase transitions (metrics auto-instrumented)
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py phase-start {session-dir} {phase}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py gate {session-dir} {phase} pass --evidence "..."
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py phase-complete {session-dir} {phase}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py advance {session-dir}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py reroute {session-dir} {target-phase} --reason "..."  # remediation loop after a failed gate — never hand-edit the rollback
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py loop-budget {session-dir} {n}  # set the bounded remediation loop budget (max_iterations); default 3
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py validate-handoff {session-dir} --file {manifest.yml}  # staged, read-only validation
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py accept-handoff {session-dir} --file {manifest.yml} --gate {pass|conditional-pass} [--evidence "..."] [--chain]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py next {session-dir}   # advisory routing for resumes

# Registries and delegation
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py artifact-add {session-dir} {phase} {path}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py decision-add {session-dir} --decision "..."
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py spec-add {session-dir} {path} [--scope session|workspace] [--relation primary|dependency|reference]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py spec-repoint {session-dir} {old} {new} [--old-scope session|workspace] [--new-scope session|workspace] [--relation primary|dependency|reference]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py contract-map {session-dir} {contract-id} --spec {path} --scope {session|workspace} --ac {AC-N} [--ac {AC-N} ...]
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py question-round {session-dir} {phase}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py contract-add {session-dir} {file} --title "..."  # computes sha256, lazy manifest

# Workspace preflight (deterministic tier — see Workspace preflight section)
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py preflight {session-dir} --validator skills/aidev-explore/scripts/validate-workspace-guidance.py [--allow-no-repos]

# Validation composites
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py gate-check {session-dir} [--phase {phase}]  # full validation contract for the phase, one verdict
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py layout-probe {session-dir}                  # deterministic legacy-layout probe (exit 2 on legacy)
```

## Handoffs

Before constructing or executing any command in the handoff lifecycle (`create-handoff`, `pause-handoff`, `resume-handoff`, `retry-handoff`, `submit-handoff`, `validate-handoff`, or `accept-handoff`), load `<agent-dir>/skills/aidev-sdd/references/specialist-invocation.md` and follow its command syntax and lifecycle instructions. Do not infer handoff syntax from memory or replace the documented argument structure with free-form alternatives.

## Deterministic validation

The orchestrator is the only actor that runs `sdd-lint.py` during SDD orchestration. Specialist agents do not execute lifecycle lint commands; they persist evidence and decisions in owned artifacts, run the generated `submit-handoff` command, and let the orchestrator validate the references and decide the gate.

Use the bundled linter for repeatable checks:

```bash
# Single-file modes
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py session .aicontext/deliverables/sdd/sessions/{id}/sdd-state.yml
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py trace .aicontext/deliverables/sdd/sessions/{id}/trace.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py trace-gate .aicontext/deliverables/sdd/sessions/{id}/trace.md {current_phase}
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py backlog .aicontext/deliverables/sdd/sessions/{id}/backlog-plan.yml
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py research .aicontext/deliverables/sdd/sessions/{id}/research.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py tech-plan .aicontext/deliverables/sdd/sessions/{id}/tech-plan.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py test-plan .aicontext/deliverables/sdd/sessions/{id}/test-plan.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py code .aicontext/deliverables/sdd/sessions/{id}/code.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py verification .aicontext/deliverables/sdd/sessions/{id}/verification.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py retro .aicontext/deliverables/sdd/sessions/{id}/retro.md
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py contracts .aicontext/deliverables/sdd/sessions/{id}/contracts.yml
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py changes .aicontext/deliverables/sdd/specs/{domain}/{spec-name}/changes/changes.json
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py metrics .aicontext/deliverables/sdd/sessions/{id}/sdd-state.yml

# Spec package (stable specs)
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py spec-package .aicontext/deliverables/sdd/specs/{domain}/{spec-name}/spec.md

# Directory mode (cross-artifact AC traceability)
python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py coverage .aicontext/deliverables/sdd/sessions/{id}/
```

The `coverage` mode extracts every `AC-N` from the scoped specs listed in `sdd-state.yml.specs[]` and verifies that each AC is referenced in the applicable derived trace sections, `test-plan.md`, and `verification.md` when those artifacts exist. It is permissive when a downstream artifact does not yet exist and strict when the artifact exists but the AC is missing — the case that signals real drift. When a `simple`, `moderate`, or `smart` session has no specs because formal functional-spec/spec-validation are skipped, coverage is N/A and passes.

Use `trace` for bootstrap and draft trace structure. Use `trace-gate` when a phase gate depends on trace evidence. Pass the current phase as the third argument (`trace-gate {path} {current_phase}`) so the check is phase-scoped: it rejects `[AIDEV_TODO]` only in trace sections owned by the current or an earlier phase, and tolerates placeholders in sections owned by phases that have not run yet. Calling `trace-gate` without a phase argument falls back to the strict whole-file check (no `[AIDEV_TODO]` anywhere), which is appropriate only at the final gates.

Each trace section is owned by the phase that must resolve its `[AIDEV_TODO]` placeholders. The orchestrator fills a section only when its owning phase (or an earlier one) is reached, and the linter gates the same way:

| Trace section             | Owning phase      |
| ------------------------- | ----------------- |
| Session                   | functional-spec   |
| Input Contract Trace      | spec-validation   |
| Acceptance Criteria Trace | functional-spec   |
| Backlog Trace             | spec-validation   |
| Technical Plan Trace      | technical-plan    |
| Test Design Trace         | test-design       |
| Implementation Trace      | implementation    |
| Verification Trace        | spec-verification |
| PR / Review Trace         | spec-verification |

During `validate-handoff` and `accept-handoff`, the CLI derives each due trace section from the referenced canonical artifacts. It replaces a section only when that section exists in the trace template selected for the active track; it never adds sections from other tracks. The manifest never repeats trace rows. Future-phase sections remain untouched; any due placeholder left after deterministic derivation blocks acceptance.

The linter is intentionally conservative. It checks structural readiness and common contract violations; specialist agents still perform semantic review.

### Orchestrator validation contract

When accepting a handoff, the orchestrator validates the artifact owned by the phase and then runs the cross-artifact checks required to advance:

| Phase               | Artifact lint mode                                   | Cross checks before advancing                                                                                            |
| ------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `discovery`         | `research`                                           | `session`                                                                                                                |
| `functional-spec`   | `spec-package`, `backlog` when present               | `session`, `contracts` (ensure all contracts in contracts.yml map to ACs per `contracts-guide.md`), derived `trace-gate` |
| `spec-validation`   | `spec-package`, `backlog` when present, `trace-gate` | `session`, `contracts` (validate Input Contract Trace completeness per `contracts-guide.md`), `coverage`                 |
| `technical-plan`    | `tech-plan`                                          | `session`, `coverage`                                                                                                    |
| `test-design`       | `test-plan`                                          | `session`, `coverage`, derived `trace-gate`                                                                              |
| `implementation`    | `code`                                               | `session`, `coverage`, code journal six-phase terminal check, derived `trace-gate`                                       |
| `spec-verification` | `verification`                                       | `session`, `coverage`, `trace-gate`                                                                                      |
| `retro`             | `retro`                                              | `session`                                                                                                                |

Always invoke `trace-gate` with the current phase as the third argument so it tolerates `[AIDEV_TODO]` in sections owned by phases that have not run yet (see the trace section ownership table above). Reserve the phase-less strict `trace-gate` for the final `spec-verification`/`retro` gates, where every section must be resolved.

## Semantic review

Deterministic validation is necessary but not sufficient. When a phase gate depends on evidence quality, load `<agent-dir>/skills/aidev-sdd/references/semantic-review-checklist.md` and apply it before advancing. Use it especially after functional spec, technical plan, test design, implementation, spec verification with review, and retro.

Semantic review must answer whether acceptance criteria are observable, test evidence is executable, implementation evidence is current, and verification is not circular. If the checklist exposes weak evidence, the orchestrator records a blocker, accepted risk, or deferral in `sdd-state.yml` and `trace.md`.

## Delegated specialist state

Specialist agents may read `sdd-state.yml` and `trace.md` for context, but must not edit them. They write semantic phase artifacts and run the generated handoff command; they never author manifest YAML. The orchestrator validates references, performs semantic review, and delegates lifecycle persistence to `accept-handoff --file`.

## Orchestrator asset manifest

The orchestrator must load every asset at the exact path shown below. Do not assume a path not listed here.

| Asset                                                                 | Exact path                                                                                   | Load when                                                                                                  |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| State mutation CLI                                                    | `<agent-dir>/skills/aidev-sdd/scripts/sdd-state.py`                                          | Every state/contracts mutation and compact status reads                                                    |
| Handoff commands                                                      | `<agent-dir>/skills/aidev-sdd/scripts/sdd-state.py`                                          | Create initial requests, pause/resume questions, and submit manifests                                      |
| Handoff command guide                                                 | `<agent-dir>/skills/aidev-sdd/references/specialist-invocation.md`                           | Interactions with specialists are needed                                                                   |
| Specialist contract (delegated-mode framework contract)               | `<agent-dir>/skills/aidev-sdd/references/specialist-contract.md`                             | Never loaded by the orchestrator — referenced by the invocation template for specialists                   |
| Kickoff protocol                                                      | `<agent-dir>/skills/aidev-sdd/references/kickoff-protocol.md`                                | When starting a new session                                                                                |
| Track classifier (includes Track Classification Checkpoint procedure) | `<agent-dir>/skills/aidev-sdd/references/track-classifier.md`                                | At Track Classification Checkpoint                                                                         |
| Workspace preflight handoff contract                                  | `<agent-dir>/skills/aidev-sdd/references/workspace-preflight-handoff-contract.md`            | When delegating to `AIDevInit`                                                                             |
| Semantic review checklist                                             | `<agent-dir>/skills/aidev-sdd/references/semantic-review-checklist.md`                       | When a gate depends on evidence quality                                                                    |
| Bounded remediation loop (playbook + contract)                        | `<agent-dir>/skills/aidev-sdd/references/remediation-loop.md`                                | When a `spec-verification` gate fails and the fix belongs to an earlier phase in the window                |
| Pre-retro acceptance checkpoint                                       | `<agent-dir>/skills/aidev-sdd/references/pre-retro-acceptance-checkpoint.md`                 | Before `retro` starts and the implemented result must be accepted by the user                              |
| Post-retro closure checkpoint                                         | `<agent-dir>/skills/aidev-sdd/references/post-retro-closure-checkpoint.md`                   | After the retro handoff is available and before accepting/completing `retro` or running `session-complete` |
| SDD layout migration contract                                         | `<agent-dir>/skills/aidev-sdd/references/sdd-layout-migration.md`                            | When the post-pending-delegation layout probe flags any legacy-layout candidate                            |
| Contracts guide                                                       | `<agent-dir>/skills/aidev-sdd/references/contracts-guide.md`                                 | When processing or validating contracts                                                                    |
| SDD state template                                                    | `<agent-dir>/skills/aidev-sdd/assets/sdd-state-template.yml`                                 | When initializing a new session                                                                            |
| Contracts template                                                    | `<agent-dir>/skills/aidev-sdd/assets/contracts-template.yml`                                 | At first contract capture (lazy)                                                                           |
| Trace template (exhaustive)                                           | `<agent-dir>/skills/aidev-sdd/assets/trace-template-exhaustive.md`                           | Track Classification → `exhaustive`                                                                        |
| Trace template (complex)                                              | `<agent-dir>/skills/aidev-sdd/assets/trace-template-complex.md`                              | Track Classification → `complex`                                                                           |
| Trace template (moderate)                                             | `<agent-dir>/skills/aidev-sdd/assets/trace-template-moderate.md`                             | Track Classification → `moderate`                                                                          |
| Trace template (simple)                                               | `<agent-dir>/skills/aidev-sdd/assets/trace-template-simple.md`                               | Track Classification → `simple`                                                                            |
| Trace template (smart)                                                | `<agent-dir>/skills/aidev-sdd/assets/trace-template-exhaustive.md` (pruned to the selection) | Track Classification → `smart`                                                                             |

## Orchestrator protocol

When an orchestrator uses this skill:

1. Read the session state — prefer `sdd-state.py status {session-dir}` (compact summary) over reading `sdd-state.yml` in full; open the YAML only when a field the summary lacks is genuinely needed.
2. Run the **Legacy layout migration** probe with `sdd-state.py layout-probe {session-dir}` (or before a session exists, a single listing of `.aicontext/deliverables/sdd/`) before anything else. If `orchestration.layout_migration` is absent and the probe reports `layout=legacy`, load `<agent-dir>/skills/aidev-sdd/references/sdd-layout-migration.md` and dispatch the generic migration subagent; do not classify the track, run preflight, validate, or route any phase until the migration handoff is accepted or the subagent reports `no_migration_needed`. `sdd-state.py preflight` also runs this probe and blocks on legacy layouts.
3. Run `sdd-lint.py session` before deciding the next transition.
4. Inspect the current phase and its gate status.
5. Before advancing past `spec-validation`, `test-design`, `implementation`, or `spec-verification`, run `sdd-lint.py coverage` against the topic directory and treat any failure as a blocker. When trace evidence is part of the gate, also run `sdd-lint.py trace-gate`.
6. Apply `<agent-dir>/skills/aidev-sdd/references/semantic-review-checklist.md` when a gate depends on evidence quality, not just artifact presence.
7. If the gate is incomplete, explain the missing evidence and apply the specialist lifecycle protocol.
8. If `orchestration.pending_delegation` is present, follow the pending delegation instructions before determining the next phase. Do not apply unrelated transitions.
9. Follow `specialist-invocation.md` for initial, question-resume, and failed-validation retry handoffs; use only the selected command's printed pointer prompt. When the specialist returns `My handoff is in: {path}`, run `validate-handoff {session-dir} --file {path}`. It validates artifacts plus candidate state/trace without mutating lifecycle files.
10. If the specialist returns a delegated question response, follow the delegated question protocol and do not advance.
11. Apply semantic review to the referenced artifacts and resolve any mandatory user checkpoint due before this phase can be accepted. In particular, obtain pre-retro acceptance before the final delivery/evaluation handoff is accepted and post-retro closure approval before the retro handoff is accepted. Record those explicit decisions separately. Only then run `accept-handoff --file {path} --gate {pass|conditional-pass}`; it registers artifacts/specs, derives trace, completes the phase, and advances. A pending delegation must already have been resolved through `resume-handoff`. Route a blocked manifest, rejected checkpoint, or semantic failure without accepting it.
12. If a gate **fails** and remediation belongs to an earlier phase (for example `spec-verification` failures caused by implementation defects), record the failure with `sdd-state.py gate {session-dir} {phase} fail --evidence "..."`, then run `sdd-state.py reroute {session-dir} {target-phase} --reason "..."`. The CLI atomically repoints `current_phase`, resets the re-run phases and gates to pending (preserving evidence history), and records the decision. Never hand-edit `sdd-state.yml` for phase rollbacks. When the failed gate is `spec-verification`, this reroute is one turn of the bounded remediation loop (load `<agent-dir>/skills/aidev-sdd/references/remediation-loop.md`): the CLI counts the iteration and refuses once the budget is exhausted, at which point you stop looping and escalate instead.
13. A successful `accept-handoff` already advances. Apply the specialist lifecycle defined for the resulting next phase.

## Remediation loop

When a `spec-verification` gate fails and the fix belongs to an earlier phase, the orchestrator drives a bounded verify→refine loop.

Load `<agent-dir>/skills/aidev-sdd/references/remediation-loop.md` for the full playbook and loop contract — root-cause routing, the `reroute`/`loop-budget` CLI sequence, execution-mode behavior, and the token-efficiency rules — whenever you enter or resume this loop.

## Pre-retro user acceptance checkpoint

Before `retro` starts, the user must confirm whether the implemented result is acceptable. Load `<agent-dir>/skills/aidev-sdd/references/pre-retro-acceptance-checkpoint.md` when this checkpoint is reached; it contains the timing, native question shape, and state handling rules.

## Post-retro session closure checkpoint

Before the session can be marked complete, the user must confirm whether the retro result is acceptable and whether to finish the SDD session. Load `<agent-dir>/skills/aidev-sdd/references/post-retro-closure-checkpoint.md` when this checkpoint is reached; it contains the timing, native question shape, and state handling rules.

## Backlog projection rules

When a session needs roadmap or backlog representation:

1. Keep functional content in the spec (the session-local draft while the session runs; the canonical stable spec once consolidated). Generated GitHub issue bodies may project that content for publication, but they must never become the source of truth.
2. Create or update `backlog-plan.yml` from the approved spec drafts.
3. Each backlog item must point to `source_spec` (a spec path resolved relative to the session) and declare a `change_kind` (`new`, `modified`, `unchanged`, or `removed`) computed by comparing the session draft against the canonical baseline. When no canonical baseline exists yet, the item is `new`. `removed` records that an already-standardized spec is being retired this session; it maps to no GitHub action.
4. The projection is **change-aware**: `new` maps to creating a GitHub issue, `modified` to updating the existing issue, `unchanged` to no GitHub action, and `removed` also to no GitHub action (it only records the retirement of a standardized spec — GitHub issues are never deleted or deprecated). Generating the projection is **not** the end of `functional-spec`: whenever a projection is generated, the planner must **offer** it to the user (presenting each item's `change_kind` and its resulting create/update/none action) and record the publish decision before the phase can complete. Declining to publish is a valid outcome — the projection stays in `backlog-plan.yml` for a later publish — but the offer itself is not optional. When the user approves publishing, creating or updating the GitHub issues for the approved items is required to complete the phase: each approved item is marked `publish_decision: approved` and, once published, its `github` block carries the issue reference (`issue_url`/`issue_number`) and `sync_status: synced`. A publish _failure_ is surfaced as an explicit blocker, never silently deferred to a later phase or to the orchestrator. A _decline_ or a _failure_ does not halt the rest of SDD, but neither authorizes skipping an approved publish.
5. Store roadmap metadata in `backlog-plan.yml`: priority, size, milestone, status, project fields, and publication state. Publication state includes, per item, the user's `publish_decision` (`pending`, `approved`, `declined`, or `not-applicable`) and the `github` sync fields (`issue_url`, `issue_number`, `sync_status`), so the publish outcome is verifiable from the artifact alone.
6. Generate GitHub issues as projections that link back to `backlog-plan.yml` and the source spec.
7. If a GitHub issue changes functional scope, sync the change back into the source spec first, then republish the issue view.

### Prototype request

If the user asks for a prototype, clarify type of prototype and scope between:

- SewingAI prototype
  - Use a generic agent to launch a prototype session with sewing ai design and prototyping tool for spec and backlog projection. Make sure to include the right skills and relevant context to the agent.
  - This prototypes can only be generated by the AIDevPlanner agent during the functional-spec phase. The prototype is not a separate phase; it is a possibledeliverable of the functional-spec phase.
- Code prototype
  - Register this as a requirement in the backlog projection and let the implementation phase handle it.

#### Late prototype request

If the user asks for a prototype, validate that:

- current track allows for prototypes
- Current phase allows for prototypes
  - If current phase does not allow for prototypes but going back to a previous phase is possible, perform the corresponding phase change
  - If current phase does not allow for prototypes and going back to a previous phase is not possible, suggest the user to create a new session for the prototype OR continue without one.

## Approve spec changes

When a session creates, updates, or deletes a stable spec, `AIDevRetro` writes the change at cycle close from the immutable session-local draft. Retro references each canonical change in its minimal manifest so transactional acceptance can repoint `sdd-state.yml.specs[]`; it does not repeat canonical content in the handoff. To apply a change:

1. Apply creates and updates to `specs/{domain}/{spec-name}/spec.md`, deriving content from the session-local draft and bumping its resource version. For a deletion, record the retirement in `retro.md` and then remove the complete canonical package, including `spec.md` and `changes/`.
2. For creates/updates only, write a per-session change note at `specs/{domain}/{spec-name}/changes/{session-id}.md` explaining **what** changed, **why**, and **briefly how**.
3. For creates/updates only, append the session entry to `specs/{domain}/{spec-name}/changes/changes.json`, preserving prior entries. A deletion has no surviving package changelog; `retro.md` is its durable record.
4. For creates and updates, the Retro manifest classifies the workspace-scoped canonical spec and names the session-scoped spec it replaces. For deletions, `spec_deletions` names the registered state reference and the workspace package that must already be absent. `accept-handoff --file` validates and applies only the state change.

## Current implementation status

The foundation contract, templates, linter, orchestrator, backlog projection, and all standard SDD specialist phases are implemented: `test-design`, `spec-verification` with review, and `retro`.
