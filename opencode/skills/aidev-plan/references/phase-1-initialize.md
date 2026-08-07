# Phase 1 — Initialize & Understand

> This file contains the complete instructions for Phase 1. Read it when starting this phase. Do not read other phase instruction files until this phase's gate is met.

## Steps

> **`<workspace_root>`** = the root directory of the **project the user is working on**. This is the user's project directory — NOT the agent's session state directory. Resolve it from the IDE workspace path or the current working directory. If the user invoked the skill from within a specific directory, that directory is the workspace root. When in doubt, ask the user.

> **Execution model.** Steps 1–2 are sequential setup (session file, target repo, MCP tool selection). Step 3 delegates an existing-spec overlap check to an `explore` sub-agent (blocking checkpoint if an existing spec already covers the request). Step 4 acquires product context via a `general-purpose` sub-agent — only after the overlap check clears, to avoid spending resources when the work may already exist. Step 5 summarizes understanding and transitions to Phase 2.

1. **Check for prior research (optional)** — Only consume research if the user explicitly provides a path to a research session file. **Do not search for research files automatically.** If the user provides a path, read it and consume its main sections — `## Research Objective`, `## Research Conclusions` (Key Findings, Scope, Recommendations, Risks, Open Questions), `## Internal Capabilities`, `## External Analysis`, and `## Sources`. Treat scope, recommendations, and risks as **binding context**. If no research path is provided, skip this step entirely.

2. **Create the session file & determine target repository** ← _requires step 1 complete if research was provided_

   **2.1. Create session file** — living document updated throughout planning:
   - Template: Load [template-plan-session.md](../assets/template-plan-session.md) — do not omit any section.
   - Path: `<workspace_root>/.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/plan.md` — where `{session_slug}` is a short, kebab-case summary of the planning topic.
   - Create directories if they don't exist. Also create the `spec-drafts/` subdirectory: `<workspace_root>/.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/spec-drafts/`
   - If previous research exists in the context, populate the `## Research Context` section with a summary of the binding context (objective, key findings, recommendations, risks, open questions).
   - Populate `## Overview` — what is being planned, why, and for whom. If coming from a previous research, summarize the research objective and recommended direction. If from an idea or direct requirement, capture the problem statement and desired outcome.
   - Set status to `🔄 Understanding`.

   **2.2. Determine target repository** — If the user already specified a target repository (`owner/repo`) in their planning prompt, use it directly — no auto-detection or confirmation needed. Otherwise, try to infer it automatically:
   1. Check if `<workspace_root>/repos` exists.
   2. Inside it, look for directories matching the pattern `app-*`.
   3. **If exactly one application (`app-*`) directory is found** — treat it as the target repository. Resolve its `owner/repo` identifier from its git remote origin (`git -C <path> remote get-url origin`, then extract `owner/repo` from the URL). Inform the user which repository was auto-detected: _"Detected target repository: owner/repo"_.
   4. **Otherwise** — the `repos` folder does not exist, contains no `app-*` directories, or contains more than one — hold the question for the combined setup prompt in §2.4.

   Write the resolved `owner/repo` to the session file's `## Metadata` → `**Target repository**` field immediately. This value is reused in Phase 4 (materialization) to avoid re-resolving the same repository.

   **2.3. Discover product-level MCP tools** — If the user already specified which MCP tool(s) to use in their planning prompt, record the selection and skip discovery. Otherwise, **discover** the available tools in your **MCP tool list** that can provide functional context about the product (what it is, what it does, scope, etc). If tools are found, hold the question for the combined setup prompt in §2.4.

   If no product-context tools are discovered, inform the user and move on — the product-context sub-agent will rely on specs and direct code exploration only.

   **2.4. Combined setup prompt** — If §2.2 and/or §2.3 have pending questions (target repo not resolved, MCP tool not selected), present them together in a **single interactive question tool call**. This avoids multiple back-and-forth exchanges:
   - **Spec issues repository** (if unresolved): freeform input. Header `"Spec issues repository"`. Prompt `"Which repository should I create the issues projected from these specs in? (owner/repo format)"`. Include a short hint clarifying that these are high-level functional specification issues (for example, user stories) derived from the specs, so this is typically the product's main application repository. Never surface the bare word "target" or assume the user already knows what repository is meant. If multiple `app-*` directories were found in §2.2, list them as selectable options.
   - **Product context tool** (if tools were discovered): list the discovered tools as selectable options with a `"Skip — use specs/code only"` option. Header `"Product context tool"`, prompt `"Which tool should I use to understand the product?"`.

   If both questions are already resolved (user provided repo + tool, or repo auto-detected + user provided tool, etc.), skip this step entirely.

3. **Check for existing spec overlap** ← _requires step 2 complete: session file exists, target repo resolved, and MCP tool selection recorded_ — Before spending any resources on product-context acquisition, verify the request is not already covered by an existing spec. In an SDD framework, specs are the canonical record of what has already been planned, so an exploration sub-agent can match the planning topic against them directly — no separate term-extraction step is needed.

   Spawn a single `explore` sub-agent (read-only local inspection — no GitHub, no MCP) that receives the user's planning topic and the workspace root. The sub-agent must:
   1. Check whether a **stable specs** directory exists as per defined by the framework. Specs inside session folders are not stable and must be ignored, as they may provide stale or incomplete context.
   2. If it exists, inspect the specs artifacts (<frameworkpath>/spec.md) whose domain, name, or title relates to the planning topic — read enough of each candidate `spec.md` to judge whether it already covers the request.
   3. Return a compact summary — one line per relevant spec: `title | path | scope (one-line) | overlap assessment (covers / related / unrelated)`. If no specs directory exists or none relate: `No prior specs found.`

   **Blocking checkpoint** — Do not proceed to step 4 until this is fully resolved:
   - **If an existing spec already covers what the user wants to plan** — meaning the scope, intent, and outcome substantially overlap — **pause the workflow and present the findings**. Explain clearly what was found and why it appears to overlap, then ask which way to go: _"I found an existing spec that appears to cover this request: [spec title](path). The scope overlaps because [brief explanation]. How should I proceed — create a new plan anyway, or stop and end the process here?"_ Wait for the user's explicit answer. Do NOT continue while waiting. If the user chooses to stop, end the workflow. If the user chooses to create a new plan anyway, continue with the existing spec noted as context in `## Planning Notes` (prefixed `[Phase 1]`).
   - **If related but not overlapping specs are found** — specs that touch the same area but address a different concern or scope — record them as context in `## Planning Notes` with a `[Phase 1]` prefix and proceed to step 4.
   - **If no specs found** — proceed directly to step 4.

   The distinction between "already covered" and "related but different" matters. A spec titled "Add retry logic to payment service" covers a request to "plan retry handling for payments" — that is a blocking overlap, pause and ask. But it does not cover "plan circuit-breaker for payment service" — that is related context, not a duplicate. When in doubt, err on the side of pausing — a false pause is cheap (the user says "proceed"), but a duplicate plan wastes significant effort.

4. **Acquire product context** ← _requires step 3 complete: the overlap checkpoint cleared (no overlap found, or the user chose to create a new plan anyway)_ — Spawn a single `general-purpose` sub-agent that acquires product context. The sub-agent receives: the user's planning topic, the list of artifact repositories involved, the user's MCP tool selection from §2.3 (if any), and instruction to return a synthesized functional summary.

   > **Note**: this sub-agent must be `general-purpose`, not `explore` — `explore`-type sub-agents do NOT have MCP access, and product context may require the product-level MCP tool.

   The sub-agent uses the following sources **in priority order, stopping as soon as it has enough functional context** — do not consult a lower-priority source if the higher-priority ones already explain what the product does:
   - **SDD specs** (canonical source of truth — consulted first): Check for a stable specs directory at the defined directory from the framework. If it exists, read the spec packages related to the planning topic — they define, in product language, what the product already does and what has been contracted. Treat these as the authoritative product context; all other sources are supplementary and must not override what an approved spec states.

   - **Product-level MCP tool** (only if the user selected one in §2.3): Use the specified tool to understand the product's value proposition and capabilities. If the user skipped tool selection, skip this source.

   - **Direct code exploration** (only if specs and the MCP tool did not provide enough functional context): Explore the code under the artifact repositories (e.g., `<workspace_root>/repos/`) to understand what the product does. Take advantage of any resource available in your context that optimizes code exploration to the fullest. Translate every code-level insight into functional terms before reporting it (apply the Functional-Language Rule from SKILL.md).

   The sub-agent must return:
   - A functional summary of what the product does, who it serves, what capabilities each artifact contributes — all in **domain/product language** (applying the Functional-Language Rule from SKILL.md). Architecture and tech stack details are relevant only when they represent product-level constraints (e.g., "the product operates as two separate applications — an operations SPA and a backend service" is relevant; "uses Spring Boot with WebFlux and a PostgreSQL database" is not).
   - A list of sources consulted with brief notes on what each revealed
   - Any significant discoveries or surprises relevant to the planning topic

   Populate the session file from the sub-agent's output:
   - Populate the `## Product Context` section with the functional summary — what the product does, who it serves, what capabilities each artifact contributes, and how they relate. When SDD specs were consulted, treat them as the authoritative basis for this section; other sources only supplement them.
   - Add to `## Planning Notes` — record any significant discoveries, surprises, or connections from the sub-agent's output. Keep notes brief (1-3 sentences each) and prefix with `[Phase 1]`.

5. **Summarize understanding** ← _requires step 4 complete: product context populated (the overlap checkpoint was already resolved in step 3)_ — Summarize understanding and report it as a **preamble before the first interview round** — include the product name (derived from product context, specs, or the user's input, never from directory or workspace paths), the key artifacts involved (referencing them by name but describing what each one does for the user or the product, not its internal architecture), and any initial observations framed in product terms. The user is a product stakeholder — they care about what the product does and what it could do better, not about how the code is structured internally. Then immediately proceed to Phase 2. The user will have the opportunity to correct any misunderstanding through their interview answers.

## Gate

When all steps above are complete:

- Session file exists with Overview, Product Context, and Sources consulted populated
- Context extracted from specs has been made from stable specs directory (if it exists)

Announce: **"Phase 1 complete — moving to Phase 2: Deep Interview."** Then read `phase-2-interview.md` and present the understanding summary alongside the first interview round.
