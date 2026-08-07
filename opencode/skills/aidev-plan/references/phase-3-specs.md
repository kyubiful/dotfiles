# Phase 3 — Spec Definition

> This file contains the complete instructions for Phase 3. Do not read other phase instruction files until this phase's gate is met.

## What a spec is

A spec is a **type-agnostic functional specification**: what the product does and why, with acceptance criteria. It is never a "user story", "bug", or "spike" — those are _issue_ types assigned later, when the spec's work is projected to the backlog (Step 7). Whatever work prompted it, every spec is authored from the same template (Step 4).

A planning session may produce one spec or several; inter-spec contracts are mapped in Step 2.

---

## Step 1 — Decompose & Draft

Before diving into the specs, step back and think about the plan as a whole. Write your thinking to `spec-drafts/{spec-name}.md` in the session — one draft file per planned spec. These are private scratchpads with no rigid format constraints.

For each spec, capture:

- **Scope**: what it covers, what it doesn't
- **Functional outcomes**: what must this spec deliver? Plain-language outcomes, not formal requirements — but specific enough that each names what happens and what it touches. E.g., “Health status computed from Harvey data”, “Health status visible in operations view”, “Harvey-unreachable preserves stale data.” They are refined into the template's sections in Step 4.
- **Affected artifacts**: which repositories or components are touched
- **Edge cases and open questions**: anything unresolved

For single-spec plans, the draft is lighter — but still write it. Separating “what is this spec about?” from “how do I fill each section thoroughly?” produces better specs.

Set status to `🔄 Spec Definition`.

---

## Step 2 — Map Contracts (multi-spec only)

From the drafts, identify every data flow, shared model, or capability that crosses a spec boundary. Create `spec-relations.md` in the session root — the **single source of truth** for inter-spec contracts.

Initial contracts may be provisional — field names get refined during deep-dive authoring. What matters is that **ownership and direction are established before specs define shared concepts**.

For single-spec plans: skip this step — do not create the file.

Column definitions:

- **Producer**: The spec that provides the capability
- **Consumer**: The spec that depends on the capability
- **Contract**: Brief name for what is exchanged
- **Information exchanged**: What information flows across the boundary, described in domain language — not technical types or field names. Name the concepts the consuming capability depends on for correctness (e.g., "datasource identifier, job status with values: pending/running/done/error"). Do not prescribe types, schemas, or serialization — those are implementation decisions for tech-plan.
- **Nature**: The kind of interaction from a user/product perspective (e.g., "user-initiated action with status tracking", "background data refresh", "on-demand query"). Do not prescribe exchange mechanisms (REST, events, etc.) — those are tech-plan decisions.

Format:

```markdown
# Spec Contracts

| Producer                   | Consumer                 | Contract         | Information exchanged                                                                  | Nature                                     |
| -------------------------- | ------------------------ | ---------------- | -------------------------------------------------------------------------------------- | ------------------------------------------ |
| Spec 1 — Datasource health | Spec 2 — Re-index action | Re-index trigger | Datasource identifier, job identifier, job status (pending/running/done/error)         | User-initiated action with status tracking |
| Spec 1 — Datasource health | Spec 3 — Operations view | Job listing      | List of jobs with: datasource identifier, status, creation time, error detail (if any) | On-demand query                            |
```

---

## Step 3 — Present Plan to User (multi-spec only)

Present the decomposition at plan level. The user validates the **logic and structure**, not template details. Keep it concise — the goal is a view the user can evaluate in under 2 minutes:

1. **Why this decomposition** — 2-3 sentences on why you drew the boundaries this way
2. **Spec overview** — one line per spec: name, scope in plain language
3. **Key relationships** — which specs depend on which, what flows between them
4. **Affected artifacts** — per spec, which artifacts are touched (one line each)
5. **Key decisions** — anything non-obvious the user should validate (tradeoffs, scope boundaries)

Ask for approval using the assistant's native interactive question tool:

_"Does this decomposition match what you need? If any boundaries are wrong, I'll adjust before writing the full specs."_

- "Looks good — proceed"
- "I have changes"

**In delegated mode this presentation travels inside the envelope**: the approval question's `context` must carry the five elements above (why this decomposition, spec overview, key relationships, affected artifacts, key decisions) as short bullets — the user approves only what is on screen.

If the user requests changes (different boundaries, missing specs, wrong scope), adjust drafts.md and spec-relations.md before proceeding.

For single-spec plans: skip this step — proceed directly to Step 4.

---

## Step 4 — Deep-Dive Spec Authoring

Now fill the full specs. The structural decisions are settled — which specs exist, what each covers, and how they connect. The detail work happens here: each section is authored fresh, not copied from the draft.

For each spec:

1. **Re-read** the current spec draft in `spec-drafts/{spec-name}.md` and `spec-relations.md` (if multi-spec) to re-anchor in the whole picture.
2. **Author** the spec by loading `skills/aidev-sdd/assets/spec-template.md` and filling every section per its inline guidance, following the authoring rules below. Build content fresh from draft outcomes, contracts, and interview clarifications.
3. **Write** the spec draft to its own file under the session's `specs/` folder (see §Writing specs to individual files).
4. **Update relations live**: if a new shared concept emerges during authoring, update `spec-relations.md` FIRST — then use that definition in the spec draft. Do NOT modify already-written spec drafts; they will be reconciled in Step 5.
5. **Generate design prototype (Step 4a — conditional)**: see below.

#### Design Prototype (conditional)

After writing the spec draft, decide whether to generate a SewingAI HTML prototype for the spec:

- Always generate one when the user has asked for a prototype or design at any point in the session.
- When the spec's **Scope** describes a screen, view, or user-facing component, you **may ask** the user whether they want a prototype — but never generate one unprompted, and never insist. Only make this proactive suggestion when the execution mode is interactive; if the state is not interactive, skip it silently.

Steps:

1. Load `skills/sewingai-design-create/SKILL.md` and follow its workflow.
   - Derive the prototype prompt from the spec's **Purpose**, **Scope**, and **Visual Structure** sections.
   - Use `IOPDS` as the default design system unless the spec or user specifies another registered key (`ZARA`, `ZARAHOME`).
2. Save both prototype artifacts to `<framework-session-path>/artifacts/`: the generated HTML from `getDesignScreen` at `{spec-name}-prototype.html`, and the screen image downloaded from the response's `imageUrl` at `{spec-name}-prototype.<ext>` (keep the source extension, e.g. `.webp` or `.png`).
3. Record the prototype URL (pattern: `https://devtools.inditex.com/sewingai/web/prototype/<prototypeId>`) and both local artifact paths (HTML and image) in `## Planning Notes` of the spec draft, prefixed with `[Prototype]`.
4. Add both artifact paths to the spec's row in `## Spec Registry` in `plan.md`.
5. When running under SDD, persist the prototype decision in `plan.md` and add the prototype as a named manifest artifact. The orchestrator decides with the user whether to promote that referenced file to a session contract; do not write `contracts.yml` or `contracts/` yourself.

Skip this step silently if:

- The `SewingAI` MCP is not available in the current runtime — record `[Prototype] Skipped: SewingAI MCP unavailable` in `## Planning Notes`.
- The spec has no visible UI (pure backend, data-only, or infrastructure spec).

### Authoring rules

- **English only** — spec content must always be written in English, regardless of the language used to communicate with the user.
- One spec per capability, product-level scope.
- Never invent missing information — **ask** during spec authoring. If information doesn't exist in the plan, note the gap in `## Planning Notes`.
- Use the template's inline guidance to judge whether each section is adequately covered. Never leave a section empty or carrying an `[AIDEV_TODO]` placeholder.
- Spec content must be functional product context — what the product does and why this spec matters. Do not copy source links or code references into any spec section; those live in `### Sources consulted` in plan.md. If you discover new sources while defining a spec, add them to `### Sources consulted`, not to the spec body.
- Record in `## Planning Notes` any significant discoveries during spec scoping — particularly cross-spec connections, shared components, or constraints that aren't obvious from the specs alone. Prefix with `[Phase 3]`.
- For multi-spec plans, `spec-relations.md` is the single definition of shared concepts. Specs consume those definitions — same names, same ownership. Never redefine a contracted concept independently in a spec.
- After completing each spec, verify internal consistency: Scope, Acceptance Criteria, Edge Cases, and Error Scenarios must agree — every behavior named in Scope is covered by at least one AC, and no AC introduces scope absent from Scope/Purpose.

### Writing specs to individual files

Each approved spec is authored as a **session-local draft** inside the current session. The draft is the working copy of the spec for this session: it carries the session's intent and rationale and is the version every downstream phase reads while the session is alive. The draft is promoted to a canonical stable package only at cycle close (owned by the retro phase); this skill never writes to the canonical `specs/` root.

- **Path**: `<<framework-spec-path>/{spec-name}/spec.md`
- **Recorded path**: when the spec is registered (in `backlog-plan.yml` `source_spec` and, under SDD, in `sdd-state.yml.specs[].path`), use the session-relative path `<framework-spec-path>/{spec-name}/spec.md`. It is resolved relative to the session directory and must not use relative navigation (`..`).
- **Naming**: `{spec-name}` is a short kebab-case identifier derived from the approved spec title. If the domain is ambiguous, pause and resolve it with the user. Never use a placeholder or default domain.
- Create the session spec draft directory if it does not exist.
- The spec file is the **complete approved spec**: every template section filled, no `[AIDEV_TODO]` left. The draft IS the spec contract for this session.
- **Update the Spec Registry** in plan.md: after writing each spec draft, add an entry to `## Spec Registry` in the session file with the spec number, title, and the session-relative path.

---

## Step 5 — Reconcile (multi-spec only, automatic)

After all spec drafts are written, spec-relations.md may have evolved during deep-dives (new fields, refined types, shifted ownership). Sweep through and ensure every spec reflects the final state:

1. Read `spec-relations.md` in full.
2. For each contract, verify the producer spec's Scope and Acceptance Criteria define what it produces, and the consumer spec's Scope references what it consumes.
3. Fix any spec that is behind `spec-relations.md` — add missing fields, correct ownership statements, align terminology.

This is a directed sweep, not a re-evaluation. The contracts are the source of truth; the specs must match.

For single-spec plans: skip this step.

---

## Step 6 — Present & Gate

Present the complete plan to the user. The goal: the user sees the whole picture and can judge whether this plan solves their problem. Frame everything from the user's perspective — what they get, what they don't get, what could be wrong.

**Multi-spec presentation:**

1. **Why this plan** — 2-3 sentences on what we're building and why these pieces
2. **Spec overview** — a scannable table:

   | #   | Name | Scope (1 line) | Key deliverable |
   | --- | ---- | -------------- | --------------- |

3. **What you'll be able to do** — 3-5 user-facing outcomes when all specs are implemented. Not AC language — plain outcomes. E.g., "Trigger a re-index from the SPA and monitor its progress in real time."
4. **What’s NOT covered** — aggregated Out Of Scope from all specs. This is where users catch missing scope fastest.
5. **Key dependencies** — which specs block which, critical path across the plan. Not every contract — just what matters for sequencing and risk.
6. **Risks & assumptions** — what could be wrong, what was assumed. Users are great at spotting wrong assumptions.

**Single-spec presentation:**

1. **What and why** — 2-3 sentences
2. **Scope** — what's in, what's out
3. **What you'll be able to do** — user-facing outcomes
4. **Risks & assumptions** — what could be wrong

End with a structured approval using the assistant's native interactive question tool:

_"Does this match what you need? If anything is missing or wrong, I'll adjust the specs before we continue."_

- "Looks good — proceed"
- "I have changes"

**In delegated mode this presentation travels inside the envelope**: the approval question's `context` must carry the presentation itself (spec overview, user-facing outcomes, what's NOT covered, risks & assumptions) as short bullets — the user approves only what is on screen, and the out-of-scope list is where they catch missing scope fastest.

If the user requests changes, modify the affected spec file(s), update `spec-relations.md` if needed, and re-present the changed elements.

**Revising or removing a spec draft.** If the user wants to drop a spec entirely (not just edit it):

- Delete the session-local draft directory `<framework-session-path>/specs/{domain}/{spec-name}/` (and any staged issue file produced for it).
- Remove its row from the Spec overview, and remove its `backlog_items` entry from `backlog-plan.yml` if one was already generated.
- Reconcile `spec-relations.md` — drop dependencies that referenced the removed spec.
- Under the full SDD flow, add its existing scoped path to the handoff manifest's `spec_removals`; `accept-handoff` applies the removal transactionally. The planner never edits `sdd-state.yml` directly.
- A ready functional-spec handoff must still classify at least one retained spec. If the user drops the final spec, do not emit a removal-only ready manifest; pause to cancel or reframe the session because there is no functional contract left to validate.
- No GitHub action is involved: removing a spec only affects spec files and session state, never GitHub issues. To retire a spec that was already standardized in a prior cycle, record a `change_kind: removed` backlog item instead (Step 7) — it reflects the retirement but still performs no GitHub action.

---

## Step 7 — Generate Backlog Projection

After the user approves the plan, project the work into backlog items. **Issue type is assigned here, never in the spec.** One spec's iteration may yield **one or more** issues. Derive the issue set from `## Work Breakdown` in plan.md: functional units → user-stories, defects → bugs, and _feasibility/how_ open questions → spikes. _Functional/purpose_ open questions were resolved during the interview and are already folded into the specs — they never become issues. Every issue references its parent spec via `source_spec`.

The projection is a roadmap/backlog index, not a copy of the specs. It is **change-aware**: each item is classified by how this session's spec draft compares to the canonical baseline, so it can later be surfaced as GitHub issues to **create** or **update**.

1. Read the structure in `skills/aidev-sdd/assets/backlog-plan-template.yml`.
2. Create `<<framework-current-session-path>/backlog-plan.yml`.
3. Classify each item's `change_kind` against the canonical baseline at `<framework-spec-path>/{spec-name}/spec.md`:
   - `new`: no canonical spec exists for that `{domain}/{spec-name}` → **create** a GitHub issue.
   - `modified`: a canonical spec exists and the draft differs → **update** the existing issue.
   - `unchanged`: a canonical spec exists and the draft is identical → no GitHub action; recorded for completeness.
   - `removed`: a previously-standardized spec is being retired this session → no GitHub action (GitHub issues are never deleted or deprecated); the canonical file is removed at cycle close (retro). Dropping a spec you were only drafting this session is **not** `removed` — just delete it (see Step 6).
   - A canonical baseline only exists once a spec has completed a previous cycle and been consolidated at retro. Until then the item is `new`.
4. For each issue, add one `backlog_items` entry:
   - `id`: type-prefixed stable ID (`US-001`, `BUG-001`, `SP-001`).
   - `type`: `user-story`, `bug`, or `spike` — decided here from the work-breakdown.
   - `title`: the issue title.
   - `source_spec`: parent spec path, `specs/{domain}/{spec-name}/spec.md` (relative to the session; no `..`). **Multiple issues may share one `source_spec`.** A `removed` item has no draft — set `source_spec` to the `{domain}/{spec-name}` identity being retired (the linter skips the on-disk check for `removed`).
   - `change_kind`: computed in step 3.
   - `roadmap`: planning metadata only. Use `null` for unknown priority, size, milestone, or project fields. Do not invent values.
   - `github`: publication metadata. Use `null` and `sync_status: not-published` until a GitHub issue exists. For a `modified` item whose baseline was already published, record the known `issue_number`/`issue_url` so the projection can target an update.
5. Do NOT copy acceptance criteria, summaries, scope, or context into `backlog-plan.yml` — `source_spec` stays the source of truth. Each issue's published shape comes from `skills/backlog-management/assets/template-{type}.md`, filled at publication from the spec and `## Work Breakdown` — never duplicated here.
6. Update `## Backlog Projection` in `plan.md` with a concise registry table (one row per issue), including each item's `change_kind` and the resulting GitHub action (create / update / none).

## Gate

Before proceeding, verify:

- `spec-drafts/` exists with per-spec decomposition rationale
- `spec-relations.md` created with all inter-spec contracts (if multi-spec plan)
- All spec drafts written under the session, each filling every template section
- Spec Registry in plan.md populated
- `backlog-plan.yml` exists and references every projected issue with a `change_kind` classification and without duplicating spec body content
- `## Backlog Projection` in plan.md points to `backlog-plan.yml`
- Reconciliation complete — all specs match final `spec-relations.md` (if multi-spec plan)
- User has approved the plan via Step 6 presentation

Announce: **“Phase 3 complete — all specs drafted and approved, and the backlog projection is generated. Proceeding to Phase 4 — Finalize.”** Then read `phase-4-finalize.md` and execute.
