# SDD Layout Migration Contract

This contract is used by `AIDevOrchestrator` when it detects that a workspace was created under a **legacy SDD layout** (topic directories straight under `sdd/`, or specs grouped inside each session, with no canonical spec store) and must be brought up to the **current layout** (canonical specs at the root, session-local drafts under each session).

It exists so the orchestrator never performs the migration itself. Migrating means reading many legacy directories and spec files; doing that inside the orchestrator both violates its thin/read-restricted contract and burns large amounts of context. Instead, the orchestrator runs a **cheap structural probe**, and when legacy signals appear it delegates the whole detection-plus-migration to a **generic subagent** using the self-contained invocation in this file.

The file has two audiences:

- **Orchestrator-facing guidance** ("Cheap detection probe", "When to trigger", "Generic subagent invocation", "Orchestrator persistence") tells the orchestrator how to detect, dispatch, and persist. It is never copied into the subagent prompt except for the invocation template.
- **Subagent-facing contract** ("Layouts", "Migration boundaries", "Migration procedure", "Conflict handling", "Required handoff") is the complete, self-contained instruction set the generic subagent executes. It is injected verbatim through the invocation template's `{{MIGRATION_CONTRACT}}` placeholder.

The migration is **outside the per-session SDD phase machine**, exactly like workspace preflight. It must not be added to `current_phase`, `phases`, `gates`, or `trace.md`. The orchestrator records the result only as orchestration metadata under `orchestration.layout_migration`.

---

## Layouts

The current layout has exactly two directories directly under `.aicontext/deliverables/sdd/`: `specs/` (the canonical, versioned spec store) and `sessions/` (time-bounded execution units). **Any other directory at that level is a legacy grouping** that must be migrated.

### Legacy layout A — topic-grouped at the root

Earlier framework versions placed each topic in its own directory straight under `sdd/`, mixing specs and execution artifacts with no canonical store and no `sessions/` folder at all. **A topic directory is effectively an old session**: it holds execution artifacts (`plan.md`, `research.md`, `tech-plan.md`, `code.md`, …) and **one or more** specs.

```
.aicontext/deliverables/sdd/
├── {topic-a}/                          ← topic dir straight under sdd/ (not specs/, not sessions/)
│   ├── plan.md  research.md  tech-plan.md  code.md   ← execution artifacts
│   └── specs/
│       ├── spec-1-{slug}.md                          ← MULTIPLE specs per topic
│       ├── spec-2-{slug}.md
│       ├── spec-3-{slug}.md
│       ├── contracts.md  drafts.md  issue-spec-*.md   ← supporting material
├── {topic-b}/
│   ├── spec.md                                        ← OR a single root spec.md
│   └── code.md  tech-plan.md
└── ...
```

The spec content lives in **any** of these shapes and the migration must capture **every** one, not just the first it finds:

- a single root `spec.md`;
- multiple enumerated specs under `{topic}/specs/spec-N-{slug}.md`;
- nested `{topic}/specs/**/spec.md`.

Supporting files under `{topic}/specs/` are **not** canonical specs and must not become spec packages: `drafts.md` (working drafts), `contracts.md` (contract manifest), and `issue-spec-*.md` (backlog/issue projections). They are relocated with the rest of the topic, never promoted.

### Legacy layout B — session-grouped specs

A later version added `sessions/` but specs still lived only inside each session, so the same capability could be redefined per session and canonical truth was impossible to trace.

```
.aicontext/deliverables/sdd/
└── sessions/
    ├── {session-1}/
    │   ├── sdd-state.yml
    │   ├── specs/...              ← spec(s) bound to this session only
    │   └── <other artifacts>
    └── {session-2}/
        ├── sdd-state.yml
        ├── specs/...              ← a possibly newer copy of the same spec
        └── <other artifacts>
```

Variants the subagent must also accept as legacy:

- Session specs stored flat (`sessions/{id}/specs/{spec-name}/spec.md` or `sessions/{id}/specs/{spec-name}.md`) without a `{domain}` level.
- Sessions whose `sdd-state.yml.specs[].path` points outside the session (for example `../../specs/...`) or to a path that no longer resolves.
- `sdd-state.yml` carrying an older `schema_version` than the template at `<agent-dir>/skills/aidev-sdd/assets/sdd-state-template.yml`.

### Target layout (canonical specs + session drafts)

```
.aicontext/deliverables/sdd/
├── specs/
│   └── {domain}/{spec-name}/
│       ├── spec.md               ← canonical, versioned source of truth
│       └── changes/
│           ├── changes.json      ← append-only provenance + version registry
│           └── {YYYYMMDD}-{session-slug}.md
└── sessions/
    └── {YYYYMMDD}-{slug}/
        ├── sdd-state.yml
        ├── specs/{domain}/{spec-name}/spec.md   ← session-local draft
        └── <other artifacts>
```

The defining gap of the legacy layout is the **absence of the canonical `specs/` store**: the durable, versioned spec packages with a `changes/` history. Migration reconstructs that store from the per-session specs while leaving the historical sessions intact as the evidence trail.

---

## Cheap detection probe (orchestrator)

When a session already exists, run the bundled probe instead of hand-rolling the listing — `python3 <agent-dir>/skills/aidev-sdd/scripts/sdd-state.py layout-probe {session-dir}` reports `layout=clean` or `layout=legacy` with the offending root entries (exit 2 on legacy) and never reads file bodies. `sdd-state.py preflight` runs the same probe as its first step and blocks on legacy layouts. Before any session exists, fall back to the manual listing described below.

The orchestrator runs this **listing-only** probe on every session resolution, right after reading `sdd-state.yml` and before track classification, preflight, validation, or phase routing. It must not read spec bodies or repository content — that depth belongs to the subagent.

The probe is a **single directory listing** of `.aicontext/deliverables/sdd/`. The current layout contains only `specs/` and `sessions/` there. Treat the workspace as a **migration candidate** when any of these holds:

1. **Legacy layout A** — the listing contains any directory other than `specs/` and `sessions/` directly under `sdd/` (a topic-grouped directory). This fires even when `sessions/` does not exist yet.
2. **Legacy layout B** — `sessions/` exists, one or more sessions contain spec files under `sessions/{id}/specs/`, and the canonical store `.aicontext/deliverables/sdd/specs/` is absent or empty (or a closed session references a spec that has no canonical package under `specs/{domain}/{spec-name}/`).
3. `orchestration.layout_migration` is absent and the listing is not already exactly `{specs/, sessions/}`.

Cheap supporting signals (any one strengthens the candidacy; none alone is required):

- A `sdd-state.yml` whose `schema_version` is lower than the current template.
- A `specs[].path` value containing `..`.
- A session `specs/` tree with no `{domain}` nesting level.

### When to trigger

- **Trigger migration** once pending delegation is clear when the workspace is a candidate by the rule above. Dispatch the generic subagent with this contract; do not classify the track, run preflight, validate, or route to any specialist phase until the migration handoff is accepted or the subagent reports `no_migration_needed`.
- **Do not trigger** when the listing under `sdd/` is already exactly `specs/` and `sessions/` and the only session-local specs belong to the **active, not-yet-consolidated** session (functional-spec ran but retro has not consolidated). That is expected current-layout behavior, not legacy drift.
- **When unsure**, dispatch the subagent in assessment mode anyway: confirmation is cheap for it and it returns `no_migration_needed` when nothing must change. The subagent is the authority on whether migration is required; the orchestrator's probe only decides whether to ask.

---

## Migration boundaries (subagent)

- Operate strictly inside `$CWD`, and within it only inside `.aicontext/deliverables/sdd/`. Never read or write repository source, tests, architecture files, `AGENTS.md`, or anything under `repos/`.
- **Write under** `.aicontext/deliverables/sdd/specs/**` (the canonical store you build) and `.aicontext/deliverables/sdd/sessions/**` (the reconstructed sessions you create from legacy topics), including the reconstructed sessions' own `sdd-state.yml` and `trace.md`. This is a **scoped exception**: it applies only to the historical sessions this migration creates, which are inert archives written once.
- **Never write the active session's** `sdd-state.yml` or `trace.md`. Return active-session repoints as structured `active_session_spec_repoints`; the orchestrator remains the sole lifecycle writer.
- **Relocate, never lose.** Every legacy file is moved into the new layout (its topic's reconstructed session, or — for spec bodies — extracted into the canonical store). Content is preserved by relocation, then the **emptied legacy topic directory is removed** so nothing is left behind under `sdd/`. Never discard a file whose content has not been relocated.
- **Append-only** for `changes/changes.json`: never rewrite, reorder, or drop existing entries.
- **Idempotent:** a spec that already has an up-to-date canonical package is skipped, not rewritten; a legacy topic already relocated is not relocated again. Re-running the migration on an already-migrated workspace must produce `no_migration_needed`.
- **No invention:** preserve the acceptance criteria, scope, and wording found in the legacy specs. Do not author new ACs, tighten scope, or "improve" content. Migration relocates and versions existing truth; it does not redesign it.

---

## Migration procedure (subagent)

### 1. Inventory

Migration is **exhaustive**: every legacy grouping and every spec inside it must be processed. Do not stop after the first spec or the first topic.

- List the directories directly under `.aicontext/deliverables/sdd/`. Classify each as `specs/` (canonical store), `sessions/` (execution units), or a **legacy grouping** (anything else — a topic-grouped directory from legacy layout A). Build the full worklist before changing anything.
- For **each legacy layout A** topic directory, enumerate **every** spec file it contains across all shapes: the root `spec.md`, every `specs/spec-N-{slug}.md`, and any nested `specs/**/spec.md`. A topic commonly holds several specs — capture all of them. Exclude the supporting files (`drafts.md`, `contracts.md`, `issue-spec-*.md`). For each spec record its path, its derived `{domain}/{spec-name}` (domain = the functional/business area the spec belongs to, inferred from the spec content and its originating topic — there is no default domain and `general` is not an acceptable value; when the domain cannot be inferred, raise a conflict per **Conflict handling** instead of inventing a placeholder; spec-name = the spec's own slug — the topic name for a root `spec.md`, or the `{slug}` after the `spec-N-` prefix for enumerated specs), and the originating topic. Also record the topic's execution artifacts and supporting files so they can be relocated. Capture any timestamp evidence (file dates, embedded dates, signatures) to order changes.
- For **each legacy layout B** session under `sessions/`, read `sdd-state.yml` (`session.id`, `session.date`, `status`, `track`, retro/closure state, `specs[]`) and enumerate every session-local spec file, recording its path, its `{domain}/{spec-name}`, and the owning session.
- Read the existing canonical `specs/` store if any, so already-migrated specs are detected and skipped (idempotency).
- Establish a chronological order across all contributing sources (sessions by `session.id` then `created_at`/`updated_at`; topics by any recoverable timestamp evidence, else by listing order).

Process **every** item on the worklist before moving to verification. If anything cannot be processed, record it as a blocker rather than silently dropping it.

### 2. Group by canonical identity

- Group every legacy spec (from topic directories and/or sessions) by its canonical `{domain}/{spec-name}`.
- Within each group, order the contributing sources chronologically. The **latest** chronological version is the canonical content; earlier versions become change-history entries.

### 3. Build each canonical package

For every group that has no current canonical package (or whose canonical package is missing pieces):

1. Write `specs/{domain}/{spec-name}/spec.md` from the latest chronological session draft. Conform its front-matter and section structure to `<agent-dir>/skills/aidev-sdd/assets/spec-template.md` while preserving the original ACs, scope, edge cases, and wording verbatim.
2. Build `specs/{domain}/{spec-name}/changes/changes.json` from `<agent-dir>/skills/aidev-sdd/assets/changes-template.json`, append-only, one entry per contributing source (topic or session) in chronological order:
   - First contributing source → `change_type: created`, `spec_version: 1.0.0`, `previous_version: null`.
   - Each later source → `change_type: updated` with a semantic version bump derived from the observed delta: **major** for breaking changes or removed ACs, **minor** for additive behavior or new ACs, **patch** for clarifications/wording. When the delta is unclear, default to `minor` for additive content and `patch` otherwise — never fabricate a larger bump.
   - Populate provenance (`user`, `participants[]`) from each source's artifact signature when present (use `<agent-dir>/skills/aidev-sdd/scripts/signature-extract.py`); when a field cannot be recovered, set it to `"unknown"` rather than guessing.
3. Write one per-source change note `specs/{domain}/{spec-name}/changes/{source-id}.md` from `<agent-dir>/skills/aidev-sdd/assets/spec-change-note-template.md`, in native product voice, describing what that source changed in the spec. For the creating source, describe the initial capability.

### 4. Reconstruct a session for each legacy topic

Each legacy layout A topic directory is an old session and must end up under `sessions/`, with nothing left at the root. For each topic:

1. Choose a session id `{YYYYMMDD}-{topic-slug}`, where `{topic-slug}` is the topic directory name and `{YYYYMMDD}` is the best recoverable date (artifact/signature date, else the migration date). On collision with an existing session, suffix the slug minimally; never overwrite an existing session.
2. Create `sessions/{session-id}/` and **move** the topic's execution artifacts and supporting files into it (`plan.md`, `research.md`, `tech-plan.md`, `code.md`, `specs/drafts.md`, `specs/contracts.md`, `specs/issue-spec-*.md`, …), preserving their content verbatim.
3. Place each of the topic's specs as a **session-local draft** at `sessions/{session-id}/specs/{domain}/{spec-name}/spec.md` (normalized identity from step 1), matching the canonical baseline you wrote in step 3.
4. Write a reconstructed `sdd-state.yml` and `trace.md` for the session, marked as a **migrated historical session**: `status: closed` (archived), `track` inferred from the artifacts present, `current_phase` set to the furthest phase evidenced by the artifacts (e.g. `code.md` → implementation, only `research.md` → discovery), each phase status derived from artifact presence, `specs[]` pointing at the normalized drafts, and a `decisions[]` entry noting it was reconstructed by layout migration and not re-validated. These historical files are written by you under the scoped exception in the boundaries; the deterministic linter is not a gate for archived sessions.
5. Once every file under the legacy topic directory has been relocated (artifacts moved, spec bodies extracted to the canonical store and mirrored as drafts), **remove the now-empty legacy topic directory**.

For legacy layout B sessions, leave the session directory in place (it is already under `sessions/`) and only normalize its spec drafts to `{domain}/{spec-name}` identity to match the canonical store.

### 5. Reconcile the active session

- For the session the orchestrator is currently running, ensure its `specs/{domain}/{spec-name}/spec.md` draft exists in the normalized location and matches the canonical baseline you wrote.
- Return one `active_session_spec_repoints` entry for each active-session spec that moved, with `old_path`, normalized session-relative `new_path`, and `relation`. Do not edit the active session's `sdd-state.yml` or `trace.md` yourself.

### 6. Verify completeness

- Re-list `.aicontext/deliverables/sdd/`. The only directories that may remain are `specs/` and `sessions/`. **Any surviving legacy grouping means the migration is incomplete** — finish it or record a blocker; do not report `migrated` with legacy directories still present.
- Confirm every canonical `spec.md` passes `<agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py spec-package` and every `changes.json` passes `<agent-dir>/skills/aidev-sdd/scripts/sdd-lint.py changes`. Report the count of specs and sessions migrated as evidence. (Running the linter for verification is permitted here because this is a one-off migration, not a lifecycle gate.)

---

## Conflict handling (subagent)

Follow the delegated envelope contract from `skills/aidev-agent-questions/SKILL.md` instead of guessing when a human decision is genuinely required, for example:

- Two same-named specs whose latest versions diverge in incompatible ways, so the canonical content cannot be chosen mechanically.
- A spec whose `{domain}` (the functional/business area it belongs to) cannot be inferred from its content or originating topic. There is no default domain, so it cannot be placed mechanically.
- An existing canonical package that conflicts with the session evidence (e.g. a newer canonical version than any session, or a `changes.json` whose history contradicts the sessions).

The envelope's `phase` must be set to the orchestrator-provided current phase. The orchestrator persists it under `orchestration.pending_delegation` and pauses, exactly as for any delegated question.

---

## Generic subagent invocation (orchestrator)

The orchestrator dispatches a **generic** subagent (the runtime's native subagent mechanism — not a named SDD specialist). Fill the placeholders and inject the result verbatim; add nothing outside the placeholders.

```text
You are invoked as a generic migration subagent inside an orchestrated Spec-Driven Development (SDD) workspace.

A workspace built under a legacy SDD layout (topic directories straight under `sdd/`, or specs grouped inside sessions, with no canonical spec store) may need to be migrated to the current layout (canonical specs at the root with a versioned changes history, session-local drafts under each session). Detect whether migration is required and, if so, perform it.

## Operating mode
- interaction_mode: "delegated".
- Load `<agent-dir>/skills/aidev-sdd/SKILL.md` and `skills/aidev-agent-questions/SKILL.md` before any work.
- Follow the migration contract below exactly. It is self-contained and authoritative for this task.
- Do not ask the user directly. When you need a human decision, follow the delegated envelope contract from `aidev-agent-questions`, with its `phase` set to: {{CURRENT_PHASE}}.
- Do not edit `sdd-state.yml` or `trace.md`. Return active-session repoints as structured `active_session_spec_repoints` in the migration handoff.

## Workspace
- SDD root: .aicontext/deliverables/sdd/
- Active session path: {{SESSION_PATH}}
- Current phase (for the envelope, if you must pause): {{CURRENT_PHASE}}

## Migration contract
{{MIGRATION_CONTRACT}}

## Required handoff
Return exactly one YAML block with the `sdd_layout_migration_handoff` shape defined in the contract above and nothing after it. If you are blocked on a human decision, follow the delegated envelope contract instead.
```

Fill `{{MIGRATION_CONTRACT}}` with the **subagent-facing** sections of this file (`Layouts`, `Migration boundaries`, `Migration procedure`, `Conflict handling`, and `Required handoff`). Fill `{{SESSION_PATH}}` with the active session directory (relative to `$CWD`) and `{{CURRENT_PHASE}}` with the session's `current_phase`.

---

## Required handoff

When the migration completes, the subagent returns:

```yaml
sdd_layout_migration_handoff:
  status: migrated | no_migration_needed | blocked
  legacy_signals: # the legacy markers actually observed; [] when none
    - "<signal description>"
  specs_migrated: # one per canonical package created/completed; [] when none
    - spec: "{domain}/{spec-name}"
      canonical_path: ".aicontext/deliverables/sdd/specs/{domain}/{spec-name}/spec.md"
      version: "<final canonical version>"
      contributing_sources: ["{topic-or-session-id}", "..."]
      changes_registry: ".aicontext/deliverables/sdd/specs/{domain}/{spec-name}/changes/changes.json"
      lint: "spec-package: pass; changes: pass"
  specs_skipped: # already-current canonical packages; [] when none
    - spec: "{domain}/{spec-name}"
      reason: "already migrated"
  sessions_reconstructed: # one per legacy topic relocated into sessions/; [] when none
    - source_topic: "{topic-slug}"
      session_id: "{YYYYMMDD}-{topic-slug}"
      session_path: ".aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{topic-slug}"
      artifacts_relocated: ["plan.md", "research.md", "..."]
  legacy_dirs_removed: # emptied legacy topic dirs deleted after relocation; [] when none
    - "{topic-slug}"
  remaining_root_dirs: # directories still directly under sdd/ after migration
    - "specs"
    - "sessions"
  active_session_spec_repoints: # structured active-session repoints; [] when none
    - old_path: "<previous session-relative path>"
      new_path: "specs/{domain}/{spec-name}/spec.md"
      relation: primary
  blockers: # [] when none
    - "<blocker summary>"
  validation_summary: "<concise summary: counts of specs/sessions migrated and legacy dirs removed>"
```

`status: migrated` is valid only when `remaining_root_dirs` contains nothing but `specs` and `sessions` — a surviving legacy grouping means the work is incomplete. `status: no_migration_needed` means the workspace is already on the current layout (or has nothing to migrate). `status: blocked` is paired with a non-empty `blockers` list or, when user input is required, with the `subagent-question-envelope` instead of this handoff.

---

## Orchestrator persistence

The orchestrator persists the accepted handoff as orchestration metadata. It is not a phase, gate, or trace artifact.

```yaml
orchestration:
  layout_migration:
    status: migrated | no_migration_needed | blocked
    completed_at: <orchestrator UTC ISO-8601 timestamp>
    specs_migrated: []
    specs_skipped: []
    sessions_reconstructed: []
    legacy_dirs_removed: []
    remaining_root_dirs: []
    blockers: []
    validation_summary: ""
```

Rules:

- Apply accepted `active_session_spec_repoints` to `sdd-state.yml` after persisting the metadata; the subagent never writes the active session's state itself. This migration-only metadata is outside the standard specialist handoff manifest.
- Treat a `migrated` handoff whose `remaining_root_dirs` still lists a legacy grouping as **incomplete**: do not persist it as `migrated`, surface it, and re-dispatch the subagent to finish.
- A `migrated` or `no_migration_needed` record lets the orchestrator skip re-dispatching the migration for this workspace unless the user explicitly requests a refresh or a new legacy signal appears.
- If `status: blocked` (or the subagent returned a question-envelope path response), the orchestrator stops before specialist phase delegation, surfaces the blockers/questions, and keeps the current SDD phase unchanged.
- Migration is **exhaustive and leaves nothing behind**: the subagent extracts **every** spec from **every** legacy grouping (a topic directory often holds several specs under `{topic}/specs/spec-N-*.md`), reconstructs each legacy topic as a session under `sessions/`, and removes the emptied legacy directories. A `migrated` result is accepted only when the listing under `sdd/` contains nothing but `specs/` and `sessions/`; if any legacy grouping survives, the orchestrator treats the result as incomplete and re-dispatches.
