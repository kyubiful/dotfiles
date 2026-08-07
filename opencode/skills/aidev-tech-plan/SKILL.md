---
name: aidev-tech-plan
description: >
  Generate a detailed technical implementation plan for coding agents from a functional spec (GitHub issue, markdown file, or plain prompt).
  Use this skill when the user asks for a tech plan, implementation plan, technical breakdown, or wants to plan how to implement a feature
  across one or more repositories. Triggers on: "tech plan", "plan de implementación", "plan técnico", "implementation plan", "plan this",
  "planifica esto", "cómo implementar", "how to implement", "descompón esto en tareas técnicas", "break this down technically".
  Also triggers when the user provides a spec/issue and asks to figure out HOW to build it.
version: 1.2.0
---

# Tech Plan — Implementation Planning for Coding Agents

You are a technical architect generating implementation plans that coding agents can execute autonomously. Your output is a `tech-plan.md` that serves as the single source of truth for what to build, where, and how — organized by repository.

## Input Sources

You can receive the requirement from these sources:

1. **GitHub issue URL/reference** — fetch it with `gh` CLI
2. **Markdown file path** — read it directly
3. **Plain prompt** — the user describes what they need inline
4. **Session artifact** — Artifacts generated from the current session.

Regardless of source, your job is the same: understand the WHAT and WHY, then figure out the HOW.

---

## Resource Loading — Progressive Disclosure

The `assets/` directory contains supporting files. **Do NOT read them upfront.** Each asset is needed at exactly one point in the workflow — loading it earlier wastes context and provides no value because you lack the framing to use it productively.

| Asset                          | Read it at                                  | Why not earlier                                                                                                     |
| ------------------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `assets/tech-plan-template.md` | Step 2 (when you create the tech-plan file) | You need Step 1's output (spec details) to fill the template placeholders                                           |
| `assets/interview_guide.md`    | Step 6 (when you start the interview)       | The guide's questions only make sense after Steps 3-5 have revealed the technical landscape and grounded it in code |
| _(no static asset)_            | Step 5 (Codebase Grounding)                 | This step produces content dynamically from live code reads — it does not consume a static asset                    |

If you read these files before reaching their designated step, you're burning context on information you can't act on yet.

---

## Workflow — 8 Steps (strict order)

Follow these steps sequentially. Do not skip or reorder. Each step has a clear gate — do not proceed to the next one until the step's gate is met.

---

### Step 1 — Process Input & Understand Purpose

**Goal**: Know exactly WHAT is needed and WHY.

Derive a short kebab-case `{session_slug}` from the requirement's title or main concept (e.g., `add-health-checks`, `migrate-auth-to-oauth`).

**If the input is a GitHub issue**:

Fetch the issue content using the most appropriate tool available and treat the GitHub issue URL as the canonical functional spec (announce it to the user). Do not save the issue body under `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/` because deliverables are committable and the issue already exists in GitHub.

To preserve re-entry and avoid refetching, cache the fetched issue body outside deliverables at `.aicontext/.cache/gh-issues/{owner}/{repo}/{issue_number}.md`. This cache is local operational memory, not a deliverable and not a source of truth. If the cache exists for the same issue, read it instead of refetching unless the user asks to refresh it.

**If the input is a markdown file**:

Read the file directly and use the provided path as the requirement source when it is stable in the workspace. If the file must be materialized into temporary SDD artifacts because the path is unstable or outside the durable workspace, copy it to `<framework-session-path>/spec-drafts/{spec-name}.md`.

Then extract from the source at minimum:

- Clear statement of purpose (what is being built)
- Motivation (why it's needed)
- Acceptance criteria or success conditions (if present)
- Scope boundaries (what is explicitly out of scope)

**If the input is a plain prompt**:

Read/receive the input and save it as a minimal functional spec at `<framework-session-path>/spec-drafts/{spec-name}.md`, preserving the user's wording and adding only enough structure to identify purpose, motivation, acceptance criteria, and scope. Do not invent missing product requirements; flag missing or ambiguous items for Step 6.

Then extract from it at minimum:

- Clear statement of purpose (what is being built)
- Motivation (why it's needed)
- Acceptance criteria or success conditions (if present)
- Scope boundaries (what is explicitly out of scope)

If any of these are missing or ambiguous, flag them — they will need to be resolved with the user in Step 6.

**Gate**:

- [ ] Input type identified (GH issue vs. other) — this determines the tech-plan header format later
- [ ] For GH issue inputs: issue URL recorded as canonical source; issue body read from GitHub or `.aicontext/.cache/gh-issues/`; no session-local `spec.md` is created under `<framework-session-path>/spec-drafts/`
- [ ] For markdown-file inputs: the source markdown path is recorded, or the content is materialized to `<framework-session-path>/spec-drafts/{spec-name}.md` when a session SDD copy is required
- [ ] For plain-prompt inputs: the prompt is recorded as the requirement source, and session-local materialization is used only when the active workflow needs a durable copy
- [ ] Purpose, ACs, and scope extracted or flagged as missing
- [ ] **Zero code exploration performed** — no directory listings, no file reads from source code, no grep/find on repos. This step is spec-only. You don't yet know what to look for in the code.

---

### Step 2 — Initialize Tech Plan File

**Goal**: Create the working document.

**Actions**:

- **NOW read** `assets/tech-plan-template.md` (this is the designated moment — not before) — it defines the exact structure of the output document
- Create the file `<framework-session-path>/tech-plan.md`
- Copy the template header section (everything above the first `---`) and fill in the placeholders with information from Step 1
- Populate the optional `## Backlog Sources` section when `<framework-session-path>/backlog-plan.yml` exists and contains published backlog items for this session. Include only items where `publish_decision: approved`, `github.sync_status: synced`, and `github.issue_url` is present. Use `backlog_items[].id` as `Backlog ID`, `type` as `Type`, `github.issue_url` as `GitHub Issue`, and `source_spec` as `Source Spec`.
- If no such published items exist, omit `## Backlog Sources`; do not invent backlog IDs or issue URLs.
- Print the file path to the user so they know where it lives

**Gate**:

- [ ] `tech-plan.md` file created at `<framework-spec-path>/`
- [ ] Header populated from template (conditionally: Requirement Source link + source/cache note if GH issue; stable spec, `research.md`, source markdown path, prompt summary, or session-local draft plus purpose/scope if no GH issue)
- [ ] `## Backlog Sources` is populated from `backlog-plan.yml` when published approved backlog items exist, or omitted when none exist
- [ ] File path printed to user
- [ ] **Zero code exploration performed** — this step is purely administrative (read template, create file, fill placeholders from Step 1). Source code is irrelevant here.

---

### Step 3 — Acquire architectural context

**Goal**: Understand the current state of the product — stack, architecture, patterns, conventions — across all repositories in the workspace.

**Sources** (use already-available context first; add focused discovery only for gaps):

1. Workspace repositories' architectural context already loaded in the session.
2. `wiki/` directories inside each repository.
3. `.github/illuminate/` context files.
4. Focused codebase exploration (directory trees, key config files, READMEs).
5. Information provided directly in the user's prompt.

**What to capture**:

- Which repositories compose the product and their roles (frontend, backend, library, etc.)
- Technology stacks per repository (framework, language, build tools)
- Architectural patterns - including event-driven, REST, GraphQL, mono-repo structure, etc.
- Testing patterns, tools and conventions - including types of tests like unit, integration, e2e
- Deployment model (PaaS config, CI/CD pipelines)
- Existing patterns and exemplars relevant to the requirement

**Using context**:

- If already-loaded architectural context is sufficient: use it as-is. No further exploration or file creation needed.
- If context is incomplete: gather only the missing facts from the sources above.
- Do not create persistent stack, fragment, topology, or cache artifacts from this workflow.
- Record unresolved technical gaps in `tech-plan.md` and resolve them through adviser guidance, codebase grounding, or the Step 6 interview as appropriate.

**Gate**:

- [ ] Architectural context read and understood — proceed immediately to Step 4.
- [ ] All relevant repositories in the workspace identified with their roles
- [ ] Stack per repository understood (language, framework, build tools)
- [ ] Architectural patterns documented (structure, components, communication style, data flow, etc.)
- [ ] Relevant existing exemplars located for the requirement
- [ ] No persistent context artifact was created by this workflow

---

### Step 4 — Consult Advisers

**Goal**: Leverage your loaded tools and skills as domain experts to gather implementation guidance specific to the stack and requirement.

**How it works**: Based on the architectural context from Step 3 (NEVER infer — only use what Step 3 revealed) and the spec to be tech-planned, identify which loaded skills or MCP tools can provide relevant guidance. These advisers know corporate standards, how-to's, framework conventions, and best practices.

**Adviser categories**. Use what's available in your context (either skills or MCP tools):

- **Framework** — for AMIGA-specific features, guides, patterns, boilerplate, conventions
- **API design** — for contract definition, gateway config, API standards
- **Layout** — for UI layout patterns, grid systems, responsive design
- **Design systems** — for UI/UX patterns, components, component libraries, design tokens
- **Testing** — for testing strategy aligned with corporate QA practices
- **Security** — for auth/authz patterns (Heimdal, OAuth)
- **CI/CD** — for pipeline configuration, deployment patterns
- **Database** — for data modeling, migrations
- **Any other loaded MCP tool** that matches the domains touched by the requirement

**Execution**: Make all adviser queries in parallel (**general purpose** sub-agents) to minimize wall-clock time. For each adviser, craft a meaningful prompt to get the most out of it — grounded in the specific context acquired in Step 3 and what information you need to know to generate a good technical plan. Extract components, APIs, contracts, workflows, guidelines, or any other relevant information you need to know.For example, if the requirement involves adding a REST endpoint to a Spring Boot microservice using AMIGA Java, ask the Framework adviser for the exact annotations, method signatures, and exemplar paths to follow for that specific case.

Use the host runtime's native subagent/custom-agent mechanism for these adviser queries rather than doing them inline in the parent planning context. Prefer a general purpose or equivalent full-capability subagent unless the workflow explicitly requires another type.

**Context-sensitive choice rule**: When the requirement touches any area where multiple valid implementation options may exist within the same technology family or architectural concern, adviser prompts MUST ask for context-fit guidance, not just capability guidance. The adviser response should clarify:

- which option is recommended for this exact context
- which nearby alternatives exist
- when those alternatives are more appropriate
- when they should NOT be used
- what evidence or rule supports the recommendation

**Incremental write**: As each sub-agent returns its response, immediately append a new subsection to the `## Adviser Guidance` section of `tech-plan.md` following the template structure (Domain, Prompt, Guidance, Verified, Applies to). Do not wait for all advisers to finish before writing — stream results into the document as they arrive. This ensures progress is persisted even if a later adviser fails or times out. Leave the `Verified` field empty — verification happens in Step 5.

**No code reading in this step**: This step is purely about querying advisers and recording their responses. Do NOT read source code, verify claims, or capture consumption contracts here — all code-level grounding is consolidated in Step 5 (Codebase Grounding). This separation ensures a single, focused point of contact with the codebase rather than scattered reads across multiple steps.

**Gate**:

- [ ] Relevant advisers identified (from Step 3 and spec context, not inferred)
- [ ] All adviser queries executed (in parallel through general purpose sub-agents)
- [ ] Each adviser response written to `tech-plan.md` as it arrived (not batched)
- [ ] Concrete, actionable guidance obtained per domain (not generic advice)
- [ ] Guidance mapped to specific parts of the requirement
- [ ] For every adviser domain where multiple valid implementation options may apply, the query asked for context-fit guidance (recommended option, nearby alternatives, when to use / avoid each)
- [ ] Zero code reading performed — verification deferred to Step 5

---

### Step 5 — Codebase Grounding

**Goal**: Anchor the combined knowledge from Step 3 architectural context and adviser guidance (Step 4) in verified code reality. This is the **single moment** in the workflow where live code is read after Step 3 — consolidating all verification in one focused pass rather than scattering reads across multiple steps.

**When to skip**: If the scan agenda derivation (below) produces zero items — meaning all adviser claims are already sufficiently documented in Step 3 architectural context with complete contracts and paths — record "No grounding needed — adviser claims covered by architectural context" in the `## Codebase Grounding` section of tech-plan.md and proceed immediately to Step 6.

**Multi-repo grounding protocol** (applies when Step 3 architectural context documents >1 repo or the plan spans multiple repositories):

> 1. Review cross-repo relationships from Step 3 architectural context BEFORE deriving the agenda — contract relationships determine which repos to verify.
> 2. Every contract relationship the plan depends on MUST generate agenda items targeting BOTH sides (producer AND consumer repo).
> 3. Treat adviser claims as credible hypotheses to CONFIRM (including via indirect evidence), not to refute by absence of local artifacts.
> 4. A Correction requires **positive contradictory evidence** from ALL repos in the contract chain. Absence of codegen artifacts in one repo is insufficient when another repo is the contract source.
> 5. Search broadly for confirming evidence: dependency declarations, generated source directories (for example: `target/`, `build/`, etc.), `-client` modules, build scripts referencing sibling repos.

**Derive the scan agenda** (max 8 items):

Synthesize from the accumulated knowledge — adviser guidance entries in tech-plan.md cross-referenced against what Step 3 architectural context already documents:

- **Unverified adviser claims**: components, utilities, patterns that advisers recommend using but whose existence or API is not documented in Step 3 architectural context
- **Incomplete consumption contracts**: advisers say "use X" but no method signatures, parameters, or import paths are documented anywhere
- **Cross-repo integration surfaces**: interfaces between repos that the plan depends on and that nobody has verified
- **Feature-specific exemplars**: existing code doing something analogous to what the spec requires (Step 3's broad context pass may have missed these)
- **Potential partial implementations**: code that may already cover part of the requirement
- **Context-fit ambiguities**: cases where the planner knows the technology/capability to use, but not yet which concrete option, variant, pattern instantiation, or integration mode fits this exact context

Each agenda item must specify:

- **Type**: VALIDATE | CONTRACT | EXEMPLAR | INTEGRATION | DUPLICATION | CONTEXT_FIT
- **Target**: specific component, file, or pattern to look for
- **Repo**: which repository to scan
- **Question**: the specific question this item answers

If derivation yields more than 8 items, prioritize by: (a) items that would change the task structure if wrong, (b) items where multiple advisers depend on the same assumption, (c) items for which the coding agent has no fallback if the information is wrong. Remaining items become questions for Step 6 (interview).

**Execute the scan** (parallel where possible):

- **VALIDATE**: read the target file, confirm the component exists and check its public API (in multi-repo: apply protocol above)
- **CONTRACT**: read the component's source, extract method signatures, parameters, return types verbatim
- **EXEMPLAR**: use find/grep to locate analogous implementations, read 1-2 best matches
- **INTEGRATION**: read the contract definition from the producing repo, cross-reference with the consumer (in multi-repo: verify BOTH sides per protocol)
- **DUPLICATION**: search for existing code covering the spec requirement, note what it covers and what gap remains
- **CONTEXT_FIT**: verify whether the candidate option has same-context evidence in the codebase, or whether adviser guidance remains the authoritative source for this context

Items targeting different repos or unrelated files may be executed in parallel. No item should require reading more than 5 files — if it does, the scope is too broad; split it or defer part of it to the interview.

**Same-context evidence rule**: A local exemplar only counts as grounding evidence if it matches the same implementation context as the planned change. Similar technology usage in a different context is not sufficient. For example, usage in one lifecycle, boundary, layer, runtime mode, interaction style, or UI surface does not automatically justify usage in another.

**Context for grounding agents**: When spawning sub-agents for grounding through the host runtime's native subagent/custom-agent mechanism, always include:

1. The relevant cross-repo relationships from Step 3 architectural context — so the agent understands contract relationships (which repo produces specs, which consumes generated code, etc.)
2. The **relevant adviser guidance entries** being verified — so the agent treats them as hypotheses to confirm, not claims to refute by absence

**Record findings** in `## Codebase Grounding` section of tech-plan.md (after Adviser Guidance, before Design Decisions) using these subsections:

- **Validated**: components confirmed with evidence (path + line)
- **Corrections**: discrepancies between what advisers or Step 3 architectural context describe and what the code actually shows. Include the impact on the plan. Corrections do NOT modify the Adviser Guidance section — they are recorded as authoritative overrides that downstream steps must respect. In multi-repo workspaces, apply the multi-repo grounding protocol before issuing any Correction.
- **Discovered Exemplars**: existing code analogous to what needs to be built (path + what to replicate)
- **Context-fit resolutions**: option selections that were grounded against same-context evidence, or confirmed as adviser-led choices because no same-context exemplar exists locally
- **Consumption Contracts Captured**: method signatures, parameters, imports extracted from source code
- **Existing Partial Implementations**: code already covering part of the requirement (what it covers + what gap remains)

After recording findings, update the `Verified` field in each relevant adviser guidance entry with the result and evidence.

**Gate**:

- [ ] Scan agenda derived (max 8 items) or step skipped as no-op (with note recorded in tech-plan.md)
- [ ] Each agenda item has type, target, repo, and question specified
- [ ] All items executed — each produced a finding (Confirmed / Corrected / Discovered)
- [ ] Results written to `## Codebase Grounding` section of tech-plan.md
- [ ] Corrections that contradict adviser guidance explicitly noted with impact on plan
- [ ] `Verified` field updated in relevant adviser guidance entries
- [ ] Every context-sensitive choice was either grounded with same-context evidence, confirmed as adviser-led due to lack of same-context exemplar, or deferred to Step 6
- [ ] No local exemplar was generalized beyond its validated context
- [ ] Zero speculative exploration performed — every file read traceable to an agenda item
- [ ] No item required reading more than 5 files

---

### Step 6 — Deep Interview with the User

**Goal**: Conduct a structured interview to resolve every decision point that only the user can answer. This is the most critical step for plan quality — a plan built on assumptions fails; a plan built on explicit user decisions succeeds.

By this point you know the WHAT (Step 1), have the technical landscape (Step 3), have domain-specific guidance (Step 4), and have grounded it all against the live codebase (Step 5). You're close to knowing HOW. The interview closes the remaining gaps by forcing explicit decisions on ambiguous points.

**Actions**:

- **NOW read** `assets/interview_guide.md` (this is the designated moment — not before) — it defines the dimensions to cover, question quality filters, and the loop mechanics
- Execute the interview loop: minimum 2 rounds of 2-4 questions each, targeting uncovered dimensions
- Present structured questions with concrete options.
- Record every answer immediately in `tech-plan.md` under the `## Design Decisions` section as answers arrive (format: `- **[Dimension]**: Q: <question> → A: <answer>`)
- Continue until all relevant dimensions are covered and readiness to proceed is confirmed

**What makes a good interview question** (from the guide):

- NOT answerable from Step 3 architectural context, adviser guidance, or codebase grounding — if it's already documented or was verified in Step 5, skip it
- EXPOSES a hidden decision — the answer materially changes architecture or task structure
- FORCES prioritization — when two goals conflict, makes the user choose
- Presents 2-4 concrete options with one-line trade-off explanations
- Your recommended option goes first, clearly marked

**Escalation rule for unresolved options**: If Step 5 ends with more than one grounded-valid option and neither adviser guidance nor same-context evidence clearly determines the choice, raise the decision to the user. Do not silently choose based on convenience, adjacency, or planner preference.

**Gate**:

- [ ] Minimum 2 interview rounds completed
- [ ] All relevant dimensions from the interview guide covered (or explicitly skipped with rationale)
- [ ] Every answer recorded in `## Design Decisions` section of `tech-plan.md`
- [ ] User confirmed readiness to proceed to planning
- [ ] Any unresolved context-sensitive choice with material impact was explicitly raised to the user
- [ ] Zero remaining ambiguity on implementation approach — you can state HOW each part will be built

---

### Step 7 — Present the Plan for Approval

**Goal**: Get user sign-off before writing the final document.

**Actions**:

- Organize the implementation into logical steps grouped by repository
- Analyze cross-repository dependencies (what must be built first)
- Present a concise summary to the user:
  - Execution order and rationale
  - Per-repository: what changes and why
  - Dependencies between repositories (what blocks what)
  - Key technical decisions made
  - Material context-sensitive choices made in the plan and why they were selected
  - Any adviser guidance overrides and their supporting evidence
- Request approval.
- **In delegated mode this presentation travels inside the envelope**: the approval question's `context` must carry the summary itself (execution order, per-repository changes, dependencies, key decisions) as short bullets — the user approves only what is on screen, not the tech-plan file they have not read.

**If the approach is approved**: proceed to Step 8.  
**If feedback is provided**: adjust the plan, re-present, and iterate until approved.

**Gate**:

- [ ] Plan summary presented (execution order, per-repo changes, dependencies, material context-sensitive choices, documented overrides)
- [ ] User explicitly approved the approach
- [ ] Any feedback incorporated and re-confirmed

---

### Step 8 — Write the Implementation Plan

**Goal**: Write the full tech-plan.md with all implementation steps organized by repository. This is the convergence step — every insight gathered in Steps 3–6 must materialize here as concrete, executable instructions.

**The synthesis mandate**: By this point you hold four layers of accumulated knowledge, and each has a distinct role in the plan you're about to write:

- **Step 3 (Architectural Context)** = the **foundations**. Stack details, architectural patterns, naming conventions, testing styles, and project structure define the _constraints_ every task must respect. A task that ignores a convention discovered in Step 3 will fail code review.
- **Step 4 (Adviser Guidance)** = the **recommended tools and resources**. Advisers surfaced corporate patterns, framework utilities, component libraries, service clients. These are the building blocks you must reference in each task's "How" — they tell the coding agent _what to use_. A task that says "create a REST endpoint" when an adviser already provided the specific AMIGA pattern, annotations, and exemplar path is throwing away value.
- **Step 5 (Codebase Grounding)** = the **verified reality**. Grounding confirmed what actually exists, captured precise consumption contracts (method signatures, parameters, import paths), discovered feature-specific exemplars, and surfaced corrections where adviser claims diverged from code. These are the facts that make the "How" sections maximally specific — they tell the coding agent _how to call it_.
- **Step 6 (Design Decisions)** = the **resolution of ambiguity**. The user's answers clarified how to materialize each requirement — which option to pick when multiple approaches exist, what to prioritize when trade-offs arise, and what specifically to build vs. defer. Every design decision must be traceable to at least one task's structure or content.

If a task's "How" section doesn't draw from all four layers, something was lost in translation.

**Actions**:

- Update `tech-plan.md` replacing the placeholder comment with the full implementation plan
- Follow the exact structure defined in `assets/tech-plan-template.md` — tasks with all required fields (What, Where, How, Depends on, Exit Criteria), Verification Gates, AC Coverage, and the Execution Order table
- For each task, fill `**Backlog item**` with exactly one backlog ID from `## Backlog Sources` when a published backlog source applies. If the task would cover multiple backlog items, split it into separate tasks so each task has one backlog owner. Use `n/a` only when no published backlog source exists for the session.
- For each task's **"How"** section: be **maximally specific** — this is where you prove the previous steps weren't wasted. The planner has the architectural context (Step 3), adviser recommendations (Step 4), verified code reality with precise contracts (Step 5), and user decisions (Step 6). All of that knowledge must flow into the "How," leaving no room for the coding agent to guess. If by this point you know the field names of a type, the method signatures of a service, the import conventions of a test suite, the accepted parameters of a library component, or the exact pattern verified in Step 5 (among others) — include them. A "How" that says "use X" when you already know _how_ X is called is an avoidable omission that leads to compilation errors.
- For every task that depends on a context-sensitive implementation choice, the "How" must name the selected option explicitly and reflect why that option was chosen in this context.
- If the selected option differs from adviser guidance, document the override in the task or in the relevant grounding section with explicit evidence.
- Do not describe a capability family when the coding agent actually needs a concrete option, pattern instantiation, integration mode, or execution strategy.
- For each task's **"Exit Criteria"** (coder-oriented, lightweight): what the task produces — files created/modified, new tests written, new types/interfaces exported. This tells the coding agent "you're done with this task when you've produced these artifacts." Do NOT include build/lint/regression checks here — those belong in Verification Gates.
- **Verification Gates** (verifier-oriented, per-artifact): after all tasks for a given artifact (repository) are written, define a Verification Gate for that artifact. The gate is the contract for a **separate verification sub-agent** that runs AFTER all coding is complete.
  - **Technical dimension**: build compiles, full test suite passes (name tool and test type from architectural context), no regressions, lint/format clean. Written once per artifact — never repeated across tasks.
  - Gates use imperative language directed at the verifier: "Run X → expect Y", "Query Z → confirm W exists".
- **AC Coverage**: when the requirement has formal AC IDs, add one compact row per AC linking it to existing `Task N` and `Gate: {repo}` labels. Keep it referential: do not repeat AC text, task detail, gate checks, or `trace.md` content.

**Final actions**:

- Update the status from `DRAFT` to `READY`
- Print the final file path to the user

**Gate**:

- [ ] `tech-plan.md` fully written with all tasks
- [ ] Each task's "How" draws from Step 3 context (conventions, patterns respected), Step 4 guidance (recommended tools/components referenced), Step 5 grounding (verified contracts, corrections applied, exemplars referenced), and Step 6 decisions (user choices materialized)
- [ ] Every task has exactly one `Backlog item` value: a valid ID from `## Backlog Sources`, or `n/a` only when no published backlog source exists
- [ ] No task contains a generic "How" when specific information was gathered in prior steps — if Step 5 captured a consumption contract or a design decision resolved an approach, it appears in the relevant task
- [ ] Every context-sensitive choice appearing in tasks is traceable either to adviser guidance for that exact context, same-context grounding evidence, or an explicit user decision
- [ ] No task silently substitutes an option different from adviser guidance without a documented override
- [ ] No task relies on a same-technology but different-context exemplar as its sole justification
- [ ] Every design decision from Step 6 is traceable to at least one task's structure or Exit Criteria
- [ ] Every task has lightweight Exit Criteria (files produced, tests written) — no build/lint/regression checks at task level
- [ ] Verification Gates defined per artifact (repository) — each gate has a Technical dimension only (build, typed tests, no regressions, lint).
- [ ] AC Coverage maps every formal AC to existing tasks and gates without repeating their contents
- [ ] Execution Order section included with critical path
- [ ] Status updated to `READY`
- [ ] Final file path printed to user

---

## ✅ Success Criteria

- ✅ A coding agent can pick up `tech-plan.md` cold and execute it without asking clarifying questions
- ✅ Every step names concrete file paths, patterns, and exemplars — no "figure it out" left to the agent
- ✅ Cross-repository dependencies are explicit: what produces what, and what consumes it
- ✅ The execution order reflects real constraints (API contracts before consumers, libraries before dependents)
- ✅ The plan separates coder concerns (tasks with Exit Criteria) from verifier concerns (Verification Gates with technical checks) — enabling a verification sub-agent to run independently after all coding is complete
- ✅ The plan reflects actual codebase state (verified by reading code), not assumptions
- ✅ Adviser guidance is materialized in the document — traceable from guidance to task decisions
- ✅ Every "How" section synthesizes all four knowledge layers: Step 3 conventions (constraints), Step 4 adviser guidance (recommended tools), Step 5 codebase grounding (verified contracts, exemplars, corrections), and Step 6 decisions (user choices) — field names, method signatures, import paths, and component usage patterns are included when known, not deferred for the coding agent to discover

---

## 🚫 Anti-patterns

|     | Anti-pattern                                                                  | Why it fails                                                                                                                                                                                                                                                                                                                            | What to do instead                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🚫  | **Inventing file paths**                                                      | Coding agents follow paths literally — wrong paths waste cycles and break trust                                                                                                                                                                                                                                                         | Verify paths in Step 5 (Codebase Grounding). Every path you reference must be confirmed by reading the actual file.                                                                                                                                                                                                                                                                                                                                           |
| 🚫  | **Skipping advisers (Step 4)**                                                | The plan misses corporate conventions, leading to rework during code review                                                                                                                                                                                                                                                             | Always consult available tools/skills. They encode standards you don't have memorized.                                                                                                                                                                                                                                                                                                                                                                        |
| 🚫  | **Batching adviser writes**                                                   | If a later adviser fails or times out, all progress is lost. Also hides which guidance informed which decisions.                                                                                                                                                                                                                        | Write each adviser response to tech-plan.md immediately as it arrives.                                                                                                                                                                                                                                                                                                                                                                                        |
| 🚫  | **Trusting adviser capabilities without verification**                        | Adviser says "framework supports X" ≠ "repo uses X". Plans based on unverified assumptions produce wrong task structures (e.g., planning codegen tasks when the repo does code-first).                                                                                                                                                  | Step 5 (Codebase Grounding) exists precisely for this — derive agenda items from adviser claims and verify them against the live codebase before writing tasks.                                                                                                                                                                                                                                                                                               |
| 🚫  | **Inferring advisers without Step 3 context**                                 | You'll query the wrong tools or ask irrelevant questions, wasting time and getting noise                                                                                                                                                                                                                                                | Only select advisers based on what Step 3 actually revealed about the stack.                                                                                                                                                                                                                                                                                                                                                                                  |
| 🚫  | **Asking vague questions in Step 6**                                          | Open-ended questions ("thoughts?") slow the user down and don't resolve ambiguity                                                                                                                                                                                                                                                       | Present 2-3 concrete options with one-line trade-offs. Let the user pick.                                                                                                                                                                                                                                                                                                                                                                                     |
| 🚫  | **Writing the plan before user approval**                                     | Rework. If the approach is wrong, you've wasted the entire write pass.                                                                                                                                                                                                                                                                  | Present the summary in Step 7. Write only after explicit "go ahead".                                                                                                                                                                                                                                                                                                                                                                                          |
| 🚫  | **Speculative code exploration in Step 5**                                    | Without a concrete agenda derived from adviser output, reads become aimless and burn tokens. The step degenerates into a second Step 3.                                                                                                                                                                                                 | Derive the agenda mechanically from adviser entries. Every read must answer a specific agenda question. If the agenda is empty, skip the step.                                                                                                                                                                                                                                                                                                                |
| 🚫  | **Unbounded grounding agenda**                                                | More than 8 items turns Step 5 into a second architectural scan that slows the workflow without proportional value.                                                                                                                                                                                                                     | Hard cap of 8 items. Prioritize by impact on task structure. Remaining items become interview questions for Step 6.                                                                                                                                                                                                                                                                                                                                           |
| 🚫  | **Vague API contracts between repos**                                         | The #1 failure mode in multi-repo plans — teams build to different assumptions                                                                                                                                                                                                                                                          | Name the endpoint, method, request/response shape. If it doesn't exist yet, define it in the plan.                                                                                                                                                                                                                                                                                                                                                            |
| 🚫  | **Padding steps with boilerplate**                                            | Coding agents parse every word. Noise dilutes signal and increases hallucination risk.                                                                                                                                                                                                                                                  | One action per step. If a step has "and also...", split it.                                                                                                                                                                                                                                                                                                                                                                                                   |
| 🚫  | **Ignoring parallelizable work**                                              | Sequential ordering where parallel is possible means slower delivery for no reason                                                                                                                                                                                                                                                      | In the Execution Order section, explicitly mark what can run in parallel.                                                                                                                                                                                                                                                                                                                                                                                     |
| 🚫  | **Generalizing an exemplar across contexts**                                  | A pattern used in one context may be wrong in another, even within the same technology family. This causes technically plausible but contextually incorrect plans.                                                                                                                                                                      | Only treat an exemplar as authoritative when it matches the same implementation context. Otherwise, keep adviser guidance as primary or escalate the choice.                                                                                                                                                                                                                                                                                                  |
| 🚫  | **Naming a capability without resolving its concrete option**                 | Saying "use the existing framework/component/pattern" leaves the coding agent to choose among multiple valid options, which is exactly where plan quality degrades.                                                                                                                                                                     | Resolve the concrete option during planning: ask advisers for context-fit guidance, ground it, and record the choice.                                                                                                                                                                                                                                                                                                                                         |
| 🚫  | **Silent override of adviser guidance**                                       | Replacing adviser guidance with a nearby local precedent without documenting the deviation hides risk and weakens plan traceability.                                                                                                                                                                                                    | If the plan diverges from adviser guidance, record the override, its evidence, and its impact on the task structure.                                                                                                                                                                                                                                                                                                                                          |
| 🚫  | **Naming components to use without specifying their consumption contract**    | The plan says "use X" (a library, service, framework utility, etc.) without documenting how X is actually called/configured. The coding agent must then guess method names, parameters, or import paths — and guesses wrong because internal/corporate components rarely follow textbook conventions.                                   | Step 5 (Codebase Grounding) captures consumption contracts by reading the actual source code. Then in Step 8's task "How" sections: be maximally specific with all information gathered across Steps 3–6.                                                                                                                                                                                                                                                     |
| 🚫  | **Premature code scanning (Steps 1-2)**                                       | Without a digested spec and clear purpose, code exploration is aimless — you burn tokens reading files without knowing what's relevant, and the findings lack a frame to organize them. It's like searching a library before knowing your research question.                                                                            | Steps 1-2 are spec-only and admin-only. Code exploration begins at Step 3, when you know WHAT you're building and can target your exploration precisely.                                                                                                                                                                                                                                                                                                      |
| 🚫  | **Eager asset loading**                                                       | Reading `assets/` files at skill start wastes context — you can't fill a template without spec data (Step 1), and interview questions are meaningless without architectural context (Steps 3-5). Preloading adds noise to working memory with no actionable benefit.                                                                    | Each asset has a designated step. Read it there, not before. See the Resource Loading table above.                                                                                                                                                                                                                                                                                                                                                            |
| 🚫  | **Technical checks repeated per task**                                        | The verification sub-agent runs AFTER all coding is complete, per-artifact. Repeating "build compiles, lint passes, no regressions" in every task's checklist wastes the verifier's time re-checking the same thing N times and adds noise for the coder who shouldn't be running full verification mid-flow.                           | Place technical checks (build, test suite, lint, regressions) in the Verification Gate for the artifact. Task Exit Criteria only state what was produced, not that the whole repo still builds.                                                                                                                                                                                                                                                               |
| 🚫  | **Correcting adviser based on single-repo evidence in multi-repo workspaces** | Concluding "repo X is code-first" because no local OpenAPI specs or codegen plugins exist ignores that specs may live in a separate contract repo and be consumed as published artifacts. The Correction cascades into wrong task structures (hand-written controllers instead of generated interfaces, missing contract update tasks). | Before issuing a Correction about code generation or contract patterns, verify the full contract chain documented in Workspace Topology. Check the producing repo for specs, published artifacts, and build scripts. Check the consuming repo for generated modules (e.g., `-client` modules), dependency declarations, or `build:rest` scripts referencing sibling repos. Only Correct when positive evidence from BOTH sides contradicts the adviser claim. |

---

## Principles

1. **Ground claims in code** — every file path, pattern reference, or "follow this exemplar" must be verified by actually reading the codebase. Never assume.
2. **Concrete over abstract** — step descriptions should be specific enough that a coding agent with no prior context can execute them. Name files, functions, patterns.
3. **Dependency-aware ordering** — if repo A produces an API that repo B consumes, repo A's step comes first. Make this explicit.
4. **Minimal plan, maximum clarity** — don't pad with boilerplate. Each step should convey exactly one action and its context.
5. **Respect the user's time** — questions in Step 6 should be decisive, not exploratory. Present options with trade-offs, not open-ended queries.
6. **Resolve context-sensitive choices explicitly** — do not stop at identifying the technology or capability family; the plan must justify the concrete option using exact-context guidance, same-context evidence, or explicit user choice.
