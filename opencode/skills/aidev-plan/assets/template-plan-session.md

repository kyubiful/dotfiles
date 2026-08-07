# Plan Session Template

Use this template when creating `plan.md`. Copy the structure inside the inner code fence (```` ```markdown ```` to ```` ``` ````) and fill in each section incrementally as the planning progresses. Replace `[AIDEV_TODO]` tags with actual content — no placeholders should remain when the plan is complete.

---

```markdown
# Plan: <Title>

## Metadata
- **Session id**: {YYYYMMDD}-{session_slug}
- **Status**: 🔄 Understanding
- **Created**: YYYY-MM-DD
- **Input source**: Research handoff / Idea / Direct requirement
- **Research file**: <path to research.md, or "N/A">
- **Target repository**: <owner/repo resolved during Phase 1, or "N/A">

## Overview

[AIDEV_TODO]

<!-- What is being planned, why, and for whom. If coming from research, summarize the
     research objective and recommended direction. If from an idea or direct requirement,
     capture the problem statement and desired outcome. -->

## Research Context

[AIDEV_TODO — or "N/A" if no research handoff exists]

<!-- If planning was triggered from an `aidev-research` skill handoff, summarize the binding context here:
     - Research Objective (problem, target users, success criteria)
     - Key Findings (3-5 bullet points)
     - Recommendations (chosen direction with justification)
     - Risks (from research, with impact levels)
     - Open Questions (items requiring decisions during planning)
     - Internal Capabilities (relevant Inditex products, APIs, artifacts, teams)

     This section is READ-ONLY after initial population — it captures the research state
     at the moment of handoff. Planning decisions that diverge from research recommendations
     must be documented in ## Clarifications with explicit justification. -->

## Product Context

[AIDEV_TODO — or "N/A" if product context could not be resolved]

<!-- What the product does, who it serves, what capabilities each artifact contributes,
     and how they relate — all in domain/product language. Architecture and tech stack
     details are relevant only when they represent product-level constraints
     (e.g., "operates as two separate applications" is relevant; "uses Spring Boot
     with WebFlux" is not). Populated during context acquisition (Phase 1); SDD specs
are the canonical source and take priority
     over product MCP tools and code. -->

### Sources consulted

_No sources recorded yet._

<!-- As you consult SDD specs, product MCP tools, code, and other sources
     during planning, record each significant source here with a brief note on what
     it revealed. Start during Phase 1 (context acquisition) and extend throughout
     later phases. This is the primary pool from which spec-level context refs
     are selected.

     For MCP tool results, record the query and key findings.

     - <MCP tool query> — <what it revealed>
-->

## Clarifications

<!-- This section records clarifications obtained during the Deep Interview phase.
     Format: - **[Dimension]**: Q: <question> → A: <answer>
     Primary: User Journey, Done Criteria, Scope Boundaries, Behavioral Contracts,
     Tradeoff Tensions
     Secondary: Integration Surface, Failure & Recovery, Data Lifecycle,
     Operational Needs -->

### Session [YYYY-MM-DD]

_No clarifications recorded yet._

## Work Breakdown

<!-- Living, FUNCTIONAL hypothesis built during the Deep Interview (Phase 2): the units of
     user-facing work and open questions this idea implies. WHAT/why only — never components,
     endpoints, or technical tasks. Seeds the issue projection (Phase 3, Step 7). Refine each round.
     - **Unit**: <user-facing outcome> — candidate issue: user-story | bug
     - **Open question (functional/purpose)**: <uncertainty about what/why> — resolve in the interview, never a backlog item
     - **Open question (feasibility/how)**: <needs investigation to decide> — candidate spike -->

[AIDEV_TODO]

## Spec Registry

[AIDEV_TODO]

<!-- Populated during Phase 3 — Spec Definition.
     Each approved spec is written as a session-local draft under specs/{domain}/{spec-name}/spec.md (relative to the session).
     spec-drafts/{spec-name}.md contains the planning rationale for that spec.
     This registry tracks all approved specs with their session-relative draft paths.

     | # | Title | File |
     |---|-------|------|
     | 1 | Descriptive Name | specs/domain/spec-name/spec.md |
     | 2 | Descriptive Name | specs/domain/spec-name/spec.md |
-->

## Backlog Projection

[AIDEV_TODO]

<!-- Populated during Phase 3 after specs are approved.
     The canonical backlog projection is `backlog-plan.yml`.
     Each item is classified by `change_kind` (new/modified/unchanged/removed) against the canonical baseline, which maps to a GitHub action (create/update/none).
     GitHub issues are template-compliant projections generated from that file and the source specs.
     Do not copy full acceptance criteria, scope, or spec bodies into this section.

     | Backlog ID | Type | Title | Source Spec | Change | GitHub Action | GitHub Issue | Sync Status |
     |------------|------|-------|-------------|--------|---------------|--------------|-------------|
     | US-001 | user-story | Descriptive Name | specs/domain/spec-name/spec.md | new | create | not published | not-published |
-->

## Planning Notes

<!-- Record significant discoveries, surprises, or connections as they emerge during
     any phase. Keep notes brief (1-3 sentences each) and prefix with the phase:
     - [Phase 1] ...
     - [Phase 3] ...
     - [Phase 3] ... (spec authoring may surface new insights)
     These notes capture reasoning that would otherwise be lost between phases. -->

## Risks & Considerations

[AIDEV_TODO]

<!-- Identified risks with impact level and mitigations.

     | Risk | Impact | Mitigation |
     |------|--------|------------|
     | ... | High/Medium/Low | ... |

     Include:
     - Technical risks (complexity, unknowns, dependencies)
     - Organizational risks (team availability, skill gaps)
     - Timeline risks (blockers, external dependencies)
     - Risks inherited from research (if applicable)
-->

## Session Info

- **File path**: <absolute path to this plan.md>
- **Session id**: {YYYYMMDD}-{session_slug}
- **Research file**: <absolute path to research.md, or "N/A">
- **Target repository**: <owner/repo resolved during Phase 1, or "N/A">
```

## Section Guidelines

### Metadata
- Update **Status** as planning progresses through phases:
  - `🔄 Understanding` → Phase 1
  - `🔄 Interview` → Phase 2
  - `🔄 Spec Definition` → Phase 3
  - `✅ Complete` → Phase 4 (finalization)
- Use actual dates.
- **Input source** must reflect how the plan was triggered.

### Research Context
- Only populate if a research handoff exists.
- Copy binding context verbatim from the research session file — do not reinterpret.
- Mark as read-only after initial population. Any divergence from research recommendations must be explicitly justified in ## Clarifications.

### Product Context
- Write in domain/product language — describe what the product does and what each artifact contributes, not how it is implemented internally. Code-based sources (product MCP tools, code analysis) are input to your reasoning; translate every insight into functional terms before writing it here.
- When an approved SDD spec exists for the topic, it is the authoritative source — it must not be overridden by product MCP tools or code.
- Architecture and tech stack details belong only when they represent product-level constraints visible to the user or stakeholder (e.g., "operates across two separate applications" is relevant context; "uses Spring Boot with WebFlux" is not).
- `### Sources consulted` paths/links are references and can be technical, but the descriptions next to them should explain what each source revealed in product terms.

### Clarifications
- Group by session date.
- Every answer must reference the interview dimension.
- Clarifications that change prior decisions should note what changed and why.

### Planning Notes
- A living section — add notes throughout Phases 1-3 whenever you encounter something worth remembering.
- Each note should be 1-3 sentences, prefixed with the phase where it was captured.
- Focus on insights that would be lost if not written down: surprises, connections, rejected alternatives, non-obvious conventions.
- This is NOT a work log. Skip routine observations. Capture only what matters for understanding the plan.

### Spec Registry
- Each approved spec is written as a session-local draft under `specs/{domain}/{spec-name}/spec.md` (relative to the session) — the registry is an index, not the spec content.
- Every spec follows the same template structure — there is one type-agnostic spec template.
- Never leave a spec partially specified — if information is missing, record it in ## Clarifications as pending.

### Backlog Projection
- `backlog-plan.yml` is the source of truth for roadmap/backlog metadata.
- The projection references spec files by path instead of duplicating functional content.
- Each item carries a `change_kind` (new/modified/unchanged/removed) computed against the canonical baseline, which maps to a GitHub action (create/update/none).
- GitHub issue URLs and project metadata are recorded here after publication or synchronization.

### Risks & Considerations
- Include risks from all sources: research, interview, and context acquisition.
- Every risk must have a proposed mitigation, even if the mitigation is "Accept and monitor".
