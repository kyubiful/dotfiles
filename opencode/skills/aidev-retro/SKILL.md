---
name: aidev-retro
description: "Standard knowledge-compounding and closure workflow. Use when closing a session: capturing product lessons and dead ends, writing durable knowledge into the target product's context, resources, consolidating canonical specs, and deciding whether the session can close."
---

# aidev-retro - Knowledge Compounding & Closure

This skill closes a session by turning its experience into **durable product knowledge written where future agents will read it**, so the next iteration on the same product or a related feature can take advantage of the compounding value of standardized knowledge. This is the **compound-engineering** core: each session must leave the canonical specs sharper, broader, and cheaper to build on than it found them.

> **Scope guardrail (non-negotiable).** This phase is about the _target product_ only. It must never reveal, discuss, evaluate, or propose anything about the framework itself — its phases, gates, agents (`AIDev*`), skills, linter, templates, or MCP. The teams using this framework are not expected to know or understand its internals. Any knowledge written into product context resources must read as native product engineering knowledge, with no or session markers.

The first artifact produced will be `retro.md`, a closing **journal**, not a team retrospective: it records what the session _observed_ and what it _decided to compound_ into the target product. Its value lives in the side effects it logs — enriched product `ARCHITECTURE.md`/`AGENTS.md`, **canonical specs built, expanded, or refined from the session's knowledge**, and the spec changelogs that make every spec change auditable — and the file itself is the ledger of those decisions. The skill routes each durable item to the smallest-scope surface of the **target product** that an agent already consults at the moment it is needed, and keeps everything else as session-local observations.

Unlike earlier phases, where the canonical specs are an _input_ authored during `functional-spec`, retro treats them as a **compounding target**: when the delivery proved something durable about the product's behavior or contracts, retro writes, refines, or retires the permanent canonical package. Canonical create/update content is derived from the immutable session-local spec draft plus durable session knowledge; retro must never modify the session draft. A retirement is recorded in `retro.md` before the complete canonical package is removed.

## Inputs

- `<framework-current-session-path>/sdd-state.yml`
- The canonical specs referenced by `sdd-state.yml.specs[].path` and their existing `changes/` packages (under `.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/`), which you write when consolidating
- The session-local spec drafts under `sessions/{session-id}/specs/{domain}/{spec-name}/spec.md`, read **only** as the source the canonical content is derived from; they are immutable and must not be modified
- The session reasoning artifacts that hold tacit knowledge: `research.md`, `plan.md`, `tech-plan.md`, `test-plan.md`, `code.md`, `verification.md`, `trace.md`
- The `ARCHITECTURE.md` and `AGENTS.md` of every repository the session changed (compounding targets)
- `aidev-sdd/assets/changes-template.json` and `aidev-sdd/assets/spec-change-note-template.md` (changelog scaffolds)

## Output

Create or update `<framework-current-session-path>/retro.md` following `assets/retro-template.md`, plus the durable side effects you write directly:

- Additive enrichments to the changed repositories' `ARCHITECTURE.md` (and `AGENTS.md` when an always-read rule is warranted).
- **Canonical specs built, expanded, or refined** from the session's durable knowledge, under `.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/spec.md`. These are written by retro and derived from the immutable session draft; the draft itself is never modified.
- For every spec create/update: an updated `changes/changes.json` registry entry and a per-session `changes/{YYYYMMDD}-{session-slug}.md` change note in the same package.
- For every spec retirement: a durable entry in `retro.md`, followed by physical removal of the complete canonical package, including `changes/`.

`retro.md` is the closing journal: it records the outcome, product observations and dead ends, the Compounding Ledger, spec consolidation/deletion, follow-ups, and closure decision. The minimal handoff references created/updated canonical files, classifies replacements, and declares deleted packages through `spec_deletions`; acceptance applies the state registry updates.

## Workflow

### Step 1 - Resolve session and closure readiness

1. Read `<framework-current-session-path>/sdd-state.yml` first.
2. Verify `current_phase` is `retro` or that the orchestrator explicitly invoked this skill.
3. Read `<framework-current-session-path>/sdd-state.yml.specs[].path` and the session reasoning artifacts: `research.md`, `plan.md`, `tech-plan.md`, `test-plan.md`, `code.md`, `verification.md`, `review.md`, and `trace.md`. Release or observation artifacts are optional; read them only if they exist for this session.
4. Identify the repositories the session changed (from `code.md` and `trace.md`). These are the compounding targets.
5. Identify unresolved blockers, follow-ups, or accepted risks.

Gate:

- [ ] Session state exists.
- [ ] The available session reasoning artifacts have been read.
- [ ] The changed repositories are identified.
- [ ] Open blockers and follow-ups are known.

### Step 2 - Explore the session for durable knowledge

Look across the artifacts for knowledge a future iteration would otherwise rediscover the hard way:

1. **Lessons learned** — what the delivery proved about the product: its domain, architecture, contracts, or code.
2. **Dead ends and rejected approaches** — approaches that were tried or assumed and failed, especially anything that triggered a reopen, a blocking review finding, or a verification fail. Capture _what was tried, why it failed, and what to do instead_. This negative knowledge is the highest-value compounding because it prevents the next agent from re-exploring the same failed path.
3. **Tacit decisions** — non-obvious choices with rationale and rejected alternatives recorded in `code.md` Key Decisions, `tech-plan.md` Design Decisions, and review findings.
4. **Codebase constraints/gotchas** discovered during delivery — hidden coupling, framework quirks, contract semantics, environment behavior.

Keep every item framed as product knowledge. Do not include anything that is only about the framework or the workflow itself — it is out of scope for this phase and must not be recorded anywhere.

Items that fail the filter still belong in the journal as `Observations`; they are simply not compounded into product context resources.

Gate:

- [ ] Observations and dead ends are captured, or an explicit `None` is recorded.
- [ ] Every item marked durable passed all checks.

### Step 3 - Compound knowledge into context resources

Route each durable item to the smallest-scope surface of the target product that an agent already reads at the moment it is needed, and enrich it there:

| Knowledge type                                                              | Target surface                 | Where                                                                                                                                            |
| --------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Repo-specific gotcha, constraint, pattern, data-flow, or contract semantics | `repos/<repo>/ARCHITECTURE.md` | Matching existing section (`Constraints & Gotchas`, `Conventions`, `Runtime & Data Flow`, `Architecture & Patterns`, `Contracts & Integrations`) |
| Rule an agent must see before any change to the repo                        | `repos/<repo>/AGENTS.md`       | A single appended line, only when always-read visibility is warranted                                                                            |

Knowledge that is only about the framework or the workflow is out of scope and is not written anywhere — not in product docs and not in `retro.md`.

Rules for repository-doc enrichment:

- **Additive only**: append to the relevant existing section; never restructure, reorder, or rewrite the document. `ARCHITECTURE.md` and `AGENTS.md` are owned by `aidev-explore`; stay compatible with its section contract so its validators still pass.
- **Native product voice**: write each note as product engineering knowledge. Never mention, its phases, agents, gates, the linter, or this session's machinery in `ARCHITECTURE.md`/`AGENTS.md`, and do not tag product docs with or session markers.
- **Deduplicate**: if the knowledge is already present, skip it or tighten the existing wording; never append a near-duplicate across sessions.
- **Provenance stays internal**: record which session produced each note only in the `retro.md` Compounding Ledger, never inside the product doc.
- **No invention**: write only what the session actually evidenced.
- **Auditable**: log every applied edit (file, section, one-line summary) in the `retro.md` Compounding Ledger. The manifest references `retro.md`; it does not duplicate the ledger.

Gate:

- [ ] Every durable product item is either compounded to its product target surface or kept as an `Observations` entry in `retro.md`.
- [ ] No product context resource mentions, its phases, agents, gates, tooling, or session markers.
- [ ] Every compounding decision (applied, skipped-duplicate, or kept-local) is logged in the Compounding Ledger.

### Step 4 - Consolidate knowledge into the canonical specs

This is the compound-engineering step. Take the durable product knowledge surfaced in Steps 2-3 and fold it into the **stable specs that live outside the session**, so the next iteration starts from a sharper contract. You write the canonical specs and their changelog directly; the immutable session draft is only the source you derive the canonical content from — never edit it.

**Decide the spec deltas.** For each durable, spec-level item (a clarified behavior, a new contract, a corrected acceptance criterion, a discovered constraint that belongs in the contract, or a capability the delivery proved should exist), decide the smallest change that captures it:

- **update** — the knowledge sharpens, corrects, or extends an existing canonical spec referenced in `sdd-state.yml.specs[]`.
- **create** — the knowledge describes durable product behavior that no canonical spec yet covers and that future sessions will need. Materialize a new stable package at `specs/{domain}/{spec-name}/spec.md`, following the spec structure `aidev-plan` produces (frontmatter, Purpose, Scope, Acceptance Criteria, etc.).
- **delete** — the canonical spec describes behavior the delivery proved is gone or permanently superseded. Record the retired identity and reason in `retro.md`, then remove the complete canonical package, including `spec.md` and `changes/`.

Only act on items grounded in this session's artifacts (`code.md`, `verification.md`, `review.md`, `test-plan.md`, `tech-plan.md`, `research.md`, `trace.md`). Never invent contract behavior the session did not evidence. If delivered behavior drifted from the canonical spec but you cannot resolve it confidently, record it as a follow-up instead of guessing.

**Write the canonical spec.** For creates/updates, apply the delta directly to canonical `spec.md`, deriving it from the immutable session draft plus durable knowledge. Never modify the session draft. Keep acceptance criteria observable and preserve IDs; bump patch/minor/major according to the behavioral change. For deletion, do not create a replacement or tombstone file: record the retirement in `retro.md` and remove the package.

**Write the changelog in the spec package.** For every create/update, write both changelog artifacts in the same spec folder, following `aidev-sdd`'s **Approve spec changes** procedure. Deletions have no surviving package changelog; `retro.md` is their durable record.

**Compile participant signatures.** Before writing `changes/changes.json`, read each session artifact that exists for this session's track (`research.md`, `plan.md`, `tech-plan.md`, `test-plan.md`, `code.md`, `verification.md` — skip artifacts belonging to phases skipped by the track). For each file, locate the last `---` divider and extract the signature table below it per `skills/aidev-sdd/references/artifact-signature.md`'s. Build a `participants` list from the results. If a file has no signature table, skip it without failing.

1. **Registry — `changes/changes.json`** (scaffold: `aidev-sdd/assets/changes-template.json`). Append one entry to the `changes` array capturing the provenance, resource versioning, and participant signatures for this change:

   | Field              | Meaning                                                                                                                                             |
   | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `session_id`       | `{YYYYMMDD}-{session-slug}` of the closing session                                                                                                  |
   | `session_slug`     | the session slug only                                                                                                                               |
   | `date`             | `YYYY-MM-DD` of the change                                                                                                                          |
   | `timestamp`        | ISO-8601 UTC timestamp of the change                                                                                                                |
   | `change_type`      | `created` or `updated`                                                                                                                              |
   | `spec_version`     | the spec resource version after this change                                                                                                         |
   | `previous_version` | the version before this change (`null` for `created`)                                                                                               |
   | `agent`            | the SDD agent writing this changelog entry (`AIDevRetro`)                                                                                           |
   | `assistant`        | the assistant runtime self-reported by AIDevRetro (e.g. `copilot`, `opencode`)                                                                      |
   | `model`            | the model self-reported by AIDevRetro (e.g. `Claude Sonnet 4.6`)                                                                                    |
   | `commit`           | first 7 chars of the rules package SHA from `aicontext.lock` (use `signature-extract.py AIDevRetro`)                                                |
   | `version_ref`      | rules package branch/version from `aicontext.lock`                                                                                                  |
   | `user`             | the user who participated in the session                                                                                                            |
   | `change_note`      | one-line summary of the change                                                                                                                      |
   | `change_note_path` | relative path to the per-session change note, `changes/{session-id}.md`                                                                             |
   | `participants`     | array compiled from session artifact signature tables — one entry per signed artifact: `{ agent, assistant, model, commit, version_ref, artifact }` |

   Create `changes.json` from the template if the spec has none. Never rewrite or reorder prior entries; append only.

2. **Change note — `changes/{YYYYMMDD}-{session-slug}.md`** (scaffold: `aidev-sdd/assets/spec-change-note-template.md`). Write the human-readable changelog for this session's change to the spec: **what** changed (sections/ACs added, edited, removed), **why** (the session evidence that motivated it), and **briefly how** (the shape of the change). One note per spec per session; if the session touches several specs, write one note in each spec package.

Keep the canonical spec and both changelog artifacts strictly about the product; never mention the framework, its phases, agents, or this session's machinery inside spec bodies or change notes (provenance fields like `model`/`session_id` in `changes.json` are metadata, not product narrative).

Gate:

- [ ] Every durable, spec-level item is created/updated, retired with a `retro.md` deletion entry, or recorded as a follow-up.
- [ ] The session draft and its committed copy were not modified.
- [ ] Every spec create/update has both changelog artifacts; every deletion is recorded in `retro.md` and its complete package is absent.
- [ ] `changes.json` entry includes `agent`, `assistant`, `model`, `commit`, `version_ref`, and `participants` (empty array is valid when no signed artifacts were found).
- [ ] No canonical spec or change note contains framework or session markers.
- [ ] No spec behavior was invented beyond what the session evidenced.

### Step 5 - Author the closing journal

1. Read `assets/retro-template.md`.
2. Create `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/retro.md`.
3. Fill every section: `Outcome Summary`, `Observations` (with its `Dead Ends & Rejected Approaches`), the `Compounding Ledger` (what durable knowledge was written where, with status per row), `Spec Consolidation`, and `Follow-Ups`. Use `None` for any section the session legitimately has nothing for.
4. Do not leave placeholders such as `TBD`, `TODO`, or `[PENDING]`.
5. Persist the closure decision, context-resource edits, spec consolidation, publication outcomes, and follow-ups in `retro.md`. The handoff manifest references the resulting artifacts instead of repeating their content.

Gate:

- [ ] `retro.md` exists.
- [ ] The Compounding Ledger and Spec Consolidation status are recorded (each as content or an explicit `None`).
- [ ] Closure decision is `complete`, `complete-with-follow-ups`, or `reopen`.

### Step 6 - Commit and push compounded repository guidance

Persist applied repository-local `ARCHITECTURE.md` and `AGENTS.md` enrichments on the target product repositories' existing delivery branches. Canonical SDD artifacts remain local deliverables; do not commit or push `.aicontext/deliverables` in this phase. Do not create branches or pull requests.

1. Load the `conventional-commits` skill (`SKILL.md`).
2. For every `ARCHITECTURE.md` or `AGENTS.md` Compounding Ledger entry marked `applied`:

- Resolve its product repository from the ledger target `repos/<repo>/...` as `<workspace_root>/repos/<repo>`. Verify that it exists and is a Git repository.
- Read the session `code.md` Repositories table to identify the repository's delivery branch. Verify that the product repository is already checked out on that exact branch. If the repository, branch mapping, or checkout cannot be verified, record that repository's publication as `blocked`; do not create or switch branches.
- Inspect `git -C <product-repo> diff --cached --name-only`. If it contains a path other than the explicit applied `ARCHITECTURE.md` / `AGENTS.md` targets for that repository, record publication status `blocked`; do not reset, unstage, or commit another actor's work.
- Stage only those explicit guidance-file paths with `git -C <product-repo> add -- <path>...`. Never use `git add -A` or `git add .`. If their staged diff is empty, record publication status `no-changes` for the repository.
- Otherwise, commit with `docs(<repo>): record delivery knowledge`, adding the session slug or issue reference in the body or footer when available, then push the verified delivery branch to its configured upstream. Capture the commit SHA. If the commit or push fails, record publication status `blocked`, the failure reason, and any created local SHA.

Gate:

- [ ] Each applied repository-local guidance file was staged and committed only in its verified target product repository and delivery branch.
- [ ] Existing staged work outside an explicit publication path set blocked that repository's publication without being altered.
- [ ] Every repository-guidance publication has status `pushed`, `no-changes`, or `blocked`, with a commit SHA when a commit was created.
- [ ] No branch, GitHub issue, or pull request was created or mutated by this step.

### Step 7 - Return orchestrator handoff

1. Do not edit `trace.md` or `sdd-state.yml` directly; those remain orchestrator-owned. You have already written the canonical specs and their changelog yourself.
2. If an orchestrator provided a response contract, follow that contract exactly. Otherwise, return a concise completion report for the caller.
3. Run the generated Retro handoff command with repeated `--spec`, `--replace-spec`, `--artifact`, and `--delete-spec` flags for the actual results. Never write the manifest YAML manually or reference deleted files.
4. Return `status: ready` only when `retro.md` records `complete` or `complete-with-follow-ups` and every publication is `pushed` or `no-changes`. When publication or consolidation is blocked, persist a blocker ID in `retro.md` and return `status: blocked` with `blocker_refs`.

Gate:

- [ ] `retro.md` contains closure, compounding, consolidation, publication, and follow-up details without duplicating them in the manifest.
- [ ] The manifest references every created/updated canonical spec and changelog; each removed package is absent and declared in `spec_deletions`.
- [ ] Each consolidated spec declares the session spec it replaces.
- [ ] A blocked publication does not propose final topic completion.

## Constraints

- Never reveal, discuss, evaluate, or propose anything about the framework itself — its phases, gates, agents, skills, linter, templates, or MCP — in `retro.md` or in any product resource. This phase is about the target product only.
- Do not create follow-up issues unless the user explicitly asks.
- Do not hide unresolved blockers.
- Do not mark the topic complete when verification, observation, or release failed without an accepted closure decision. Missing observation alone is acceptable when verification and trace evidence are sufficient for closure.
- Do not create new product scope inside retro; record follow-up candidates instead.
- Enrich `ARCHITECTURE.md`/`AGENTS.md` additively only; never restructure, reorder, or rewrite documents owned by `aidev-explore`, never duplicate knowledge already present, and never add or session markers.
- When consolidating into canonical specs, only fold in knowledge the session evidenced. Create/update canonical files and changelogs from immutable session drafts; for deletion, record the retirement in `retro.md` and remove the whole canonical package. Never modify a session draft. Record uncertain drift as a follow-up instead of guessing.
- Do not invent knowledge; every compounded note must be evidenced by the session artifacts.
- Publish applied repository-local `ARCHITECTURE.md` and `AGENTS.md` files only from their verified target product repository and existing delivery branch. Never stage, commit, or push `.aicontext/deliverables`; never stage broadly or create GitHub delivery artifacts during retro.
- Keep the output in English, even if the conversation is in another language.

## Completion response

Report:

1. Retro report path.
2. Closure decision.
3. Durable product knowledge compounded, with the target files and sections.
4. Canonical specs created/updated, with version and changelog paths; canonical packages deleted, with their retired identity and removal result from `retro.md`.
5. Product follow-up actions count.
6. Repository-guidance publication outcomes, including every product repository, branch, commit SHA when present, and reason.
7. Proposed final topic status for the orchestrator to persist.
