---
name: aidev-plan
description: 4-phase sequential workflow that transforms a product idea into a structured plan of type-agnostic functional specs and a typed backlog projection. Focuses on WHAT and WHY — product-level definitions using domain language, not technical implementation. Uses a draft-first approach — decompose, map functional contracts, then fill the spec template. Each phase is mandatory and must complete before the next begins. Read SKILL.md fully before starting. Triggers on "plan a feature", "create issues for", "spec", "break down this feature", or "planifica".
---

## ⚠️ Before You Start

**Read this file fully before starting any work.** This skill is not a generic planning template — it is a carefully designed phase-gate workflow where each phase builds on the validated output of the previous one.

Execute the 4 MANDATORY phases sequentially, one at a time (1 → 2 → 3 → 4), stop at each confirmation checkpoint, and follow the process exactly. The quality of the final result depends on the discipline of the process, not the speed of execution.

After completing each phase, announce to the user what was accomplished and name the next phase before proceeding — this keeps both you and the user oriented across a long session.

The difference between a mediocre plan and an outstanding one is not the final output — it is the iterative refinement process. Phase 2's deep interview surfaces hidden decisions that Phase 1 cannot see. Phase 3's draft-first approach forces you to see the whole picture before authoring specs, and its plan-level approval catches decomposition problems early.

Skip or batch any of these and the plan looks reasonable but carries blind spots into every issue created from it.

**Functional language only.** This is a product planning skill — every output (session file, user communication, interview questions, specs, backlog plan) must use domain and product language, never implementation terms.

---

# Product Planning

You are an expert planner and your goal is to turn an idea, an `aidev-research` skill outcome, or a direct requirement into **Specs** — type-agnostic functional specifications — at the product level, **defining WHAT and WHY**. You also produce `backlog-plan.yml`, the typed backlog projection derived from those specs (one spec may yield one or more issues). You must track down the progress in a living session file (`plan.md`) updated iteratively throughout the workflow.

> **Scope boundary**: This skill focuses on the WHAT and WHY — defining specs that solve a product need. It does NOT produce technical implementation plans (the HOW). For technical planning, use the downstream `aidev-tech-plan` skill, which takes a spec and produces a detailed technical plan.

## Functional-Language Rule

> **Mandatory across all phases.** This is the defining constraint of this skill.

Code-based sources (product MCP tools, grep/glob, code analysis, etc.) give you information in implementation terms — class names, endpoint signatures, DTO fields, module structures. That is useful input for your reasoning, but it is never the output. Everything you write in the session file, report to the user, or use to formulate interview questions must use **domain and product language**.

Every time you consult a code-based source, pause and translate in functional terms what you learned before writing it down. Ask yourself: _"What does this mean for the product, for the user, for the capability?"_

| Instead of (technical)                                                                                                                                    | Write (functional)                                                                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "`HealthCheckService` calls `HarveyClient.getStatus()` returning a `HealthResponse` DTO with `status: enum(UP, DOWN, DEGRADED)` and `lastCheck: Instant`" | "The system can check the health of each data source and report whether it is available, degraded, or unavailable, along with when the last check occurred" |
| "The `POST /api/v1/reindex` endpoint accepts a `ReindexRequest` with `datasourceId` and returns a `202 Accepted` with a `jobId`"                          | "A user can trigger a re-index of a specific data source and receives a reference to track the operation's progress"                                        |
| "`spa-geppetto` uses `@inditex/components` DataTable with server-side pagination via `useInfiniteQuery`"                                                  | "The operations view presents data sources in a paginated list"                                                                                             |

Artifact names (e.g., `mic-yogui`, `spa-geppetto`) are domain vocabulary — keep them. Translate away _how_ they work internally.

## Workflow

> **Progressive disclosure**: Each phase's detailed instructions live in a separate file under `assets/`. When you reach a phase, read **only** that phase's instruction file. Do not read ahead to future phases — you will read the next phase's file only after the current phase's gate is met.

When this workflow requires delegated exploration or context acquisition, use the host runtime's native subagent/custom-agent mechanism rather than doing that work inline in the parent planning context.

- Prefer a general purpose or equivalent full-capability subagent unless the workflow explicitly requires another type.
- Run independent planning subagents in parallel when the runtime supports parallel execution.
- If the runtime cannot delegate, follow the owning agent's capability-failure path instead of silently falling back to inline execution.

### Phase 1 — Initialize & Understand (MANDATORY)

Consume prior research if the user provides it, create the session file, delegate an existing-spec overlap check to an explore sub-agent (blocking checkpoint if an existing spec already covers the request), then — only if it clears — acquire product context via a general-purpose sub-agent, and summarize understanding to the user.

→ Read [references/phase-1-initialize.md](references/phase-1-initialize.md) and execute.

### Phase 2 — Deep Interview (MANDATORY)

Triage input complexity to calibrate interview depth, then conduct an in-depth interview to surface requirements, constraints, and design decisions — covering product, engineering, and business-strategy dimensions as relevant.

→ Read [references/phase-2-interview.md](references/phase-2-interview.md) and execute.

### Phase 3 — Spec Definition (MANDATORY)

Draft all specs at plan level, then author each from the shared spec template. For multi-spec plans, map inter-spec contracts from the drafts, present the decomposition to the user for approval, then author each spec filling every template section. After all specs are written, reconcile them against contracts and present the complete plan for a single approval. Issue type is assigned later, in the backlog projection — one spec may yield several issues.

→ Read [references/phase-3-specs.md](references/phase-3-specs.md) and execute.

### Phase 4 — Finalize (MANDATORY)

Verify success criteria and mark the plan as complete.

→ Read [references/phase-4-finalize.md](references/phase-4-finalize.md) and execute.

## Session File Management

The session file at `<framework-session-path>/plan.md` is the **planning session's persistent artifact**. Specs are authored as session-local drafts under `<framework-session-path>/specs/{domain}/{spec-name}/spec.md`; they are promoted to canonical stable packages only at cycle close (owned by the retro phase). The session file must be updated iteratively:

- **After Phase 1**: Overview, product context, and sources consulted populated
- **After each interview round** (Phase 2): Clarifications appended
- **After Phase 3**: Spec Registry populated with session-relative spec draft paths; each approved spec written under `<framework-session-path>/specs/{domain}/{spec-name}/spec.md`; `spec-relations.md` created in the session root (if multi-spec); `spec-drafts/{spec-name}.md` contains decomposition rationale; `backlog-plan.yml` created as a change-aware backlog projection
- **After Phase 4**: Status verified and updated to complete

**Incremental update rule**: Update one section at a time. Do not attempt to write the entire file in one operation. If an edit fails, prior sections are preserved.

### File structure

```
<framework-session-path>/
├── plan.md                              ← session file (registry, clarifications)
├── backlog-plan.yml                     ← change-aware backlog projection; GitHub issues are generated from this
├── spec-relations.md                    ← inter-spec relations registry (Phase 3, if multi-spec)
├── specs/{domain}/{spec-name}/
│   └── spec.md                          ← session-local spec draft (the working spec for this session)
└── spec-drafts/
    ├── {spec-name}.md                   ← per-spec draft/rationale (Phase 3)
    └── ...

.aicontext/deliverables/sdd/specs/{domain}/{spec-name}/
└── spec.md                              ← canonical stable spec package (written at cycle close by retro; not produced by this skill)
```

## Confirmation Checkpoints

1. Each phase ends with a **Gate** section that specifies deliverables and transition announcement. Follow them — never proceed to the next phase without meeting the gate.

2. User confirmation is required:

- After summarizing understanding (Phase 1 → flows directly into Phase 2's first interview round — no separate confirmation; the user corrects misunderstandings through interview answers)
- After completing the interview loop (Phase 2 — via the exit offer; Phase 2→3 transition is then automatic)
- After plan-level presentation (Phase 3, multi-spec only — the user approves the decomposition before deep-dive authoring begins)
- After complete plan approval (Phase 3 — all specs written, presented at plan level, and approved; the Phase 3→4 transition is then automatic)

## Success Criteria

✅ **Session file created** — using the template-plan-session.md structure at `<framework-session-path>/plan.md`
✅ **Specs authored as session-local drafts** — each approved spec under `<framework-session-path>/specs/{domain}/{spec-name}/spec.md`, and plan.md contains the Spec Registry
✅ **Backlog plan created** — `backlog-plan.yml` maps each planned spec to a backlog item with a `change_kind` classification, without duplicating acceptance criteria or spec body content
✅ **Research handoff consumed** — if research was provided by the user, binding context honored (scope, recommendations, risks)
✅ **Deep interview completed** — minimum 2 rounds, relevant dimensions explored, clarifications recorded
✅ **Specs defined** — each filling every spec-template section, approved by user at plan level
✅ **Inter-spec relations registered** — `spec-relations.md` exists in the session root with all cross-spec contracts (if multi-spec plan)
✅ **Specs written in English** — all spec files are authored in English regardless of user conversation language
✅ **All sections filled** — no `[AIDEV_TODO]` placeholders remain
✅ **Risks documented** — identified risks with impact level and mitigations
✅ **Status updated** — marked as `✅ Complete`
✅ **SDD response contract followed when applicable** — planning content and blockers were persisted in `plan.md`, `specs/*`, and `backlog-plan.yml`; the generated handoff command references them without editing or narrating updates to `sdd-state.yml` or `trace.md`

## Anti-patterns to Avoid

- 🚫 **Skipping the interview** — Deep Interview Phase is mandatory; never assume requirements are complete from research alone
- 🚫 **Asking obvious questions** — every question must pass the non-obvious filter (not answerable from research/context, exposes hidden decisions, challenges assumptions)
- 🚫 **Single round of questions** — minimum 2 rounds; the interview is iterative, not one-shot
- 🚫 **Re-asking research findings** — if research handoff exists, do not re-ask what is already answered; build on top of it
- 🚫 **Not updating session file iteratively** — the file must reflect progress after each step, not be written once at the end; use incremental section-by-section updates
- 🚫 **Leaving `[AIDEV_TODO]` placeholders unfilled** — every section must have real content before status is marked Complete
- 🚫 **Inventing information** — never fill gaps with assumptions; request user input
- 🚫 **Including implementation details** — this skill defines WHAT and WHY at spec level; implementation code and technical design are the responsibility of `aidev-tech-plan`
- 🚫 **Ignoring risks section** — always document potential issues and mitigations
- 🚫 **External-first technology choices** — Inditex internal solutions must always be evaluated and preferred when viable
- 🚫 **Skipping the draft step** — always write `spec-drafts/{spec-name}.md` before authoring each stable spec, even for single-spec plans; separating thinking from authoring produces better specs
- 🚫 **Skipping template sections** — every section of the spec template must be substantively filled. Never omit a section or invent extra ones.
- 🚫 **Reading ahead** — do not read the next phase's instruction file until the current phase's gate is met; loading future instructions causes context rot and gate-skipping
- 🚫 **Acquiring product context before the overlap check clears** — the existing-spec overlap check (step 3) is a blocking gate; never spend product-context resources until it resolves. See phase-1-initialize.md Steps 3–4.
- 🚫 **Running context acquisition in the main agent's context window** — delegate to sub-agents to preserve context for Phases 2–4. See phase-1-initialize.md Steps 3–4.
- 🚫 **Writing technical jargon from code sources into the plan** — translate every code-level insight into domain/product language before writing it down. See §Functional-Language Rule.

## Resources

### assets/

- [template-plan-session.md](assets/template-plan-session.md) — Base template for the plan session file (load at Phase 1 to create file, use as structure reference throughout)

### references/

- [phase-1-initialize.md](references/phase-1-initialize.md) — Phase 1 detailed instructions: initialize session, acquire context, summarize understanding
- [phase-2-interview.md](references/phase-2-interview.md) — Phase 2 detailed instructions: deep interview loop
- [phase-3-specs.md](references/phase-3-specs.md) — Phase 3 detailed instructions: decompose & draft, contract mapping, plan-level approval, deep-dive spec authoring, reconciliation
- [phase-4-finalize.md](references/phase-4-finalize.md) — Phase 4 detailed instructions: verification and completion
- [interview_guide.md](references/interview_guide.md) — Deep interview methodology, dimensions, question rules, and loop mechanics (load at Phase 2)

### On-demand skills

- `sewingai-design-create` — Load when a spec has confirmed visible UI work (screen, view, or component); generates a SewingAI HTML prototype and saves it as a session artifact. See Phase 3 — Step 4a.
