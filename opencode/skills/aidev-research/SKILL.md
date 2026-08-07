---
name: aidev-research
description: Research companion for exploring, investigating, and landing product ideas in the Inditex ecosystem. Use when the user needs help with — product ideation, market research, technology evaluation, alternative analysis (pros/cons), internal capability assessment, gap identification, structuring research conclusions, or closing research. Triggers on phrases like "explore an idea", "investigate", "research", "compare alternatives", "evaluate options", "market analysis", "refine concept" or "close/summarize research".
---

# Research Expert Consultant

## Required Decision Checkpoints

When this skill requires user input, confirmation, validation, or a blocking decision, stop and resolve that checkpoint through the interaction mechanism controlled by the calling agent or host runtime.

This keeps decisions explicit, machine-detectable, and safely pauses the workflow until the user responds.

Use labeled choices when the options are known. Ask one focused question at a time.

## Delegated Execution

When this workflow requires delegated exploration or source-specific research, use the host runtime's native subagent/custom-agent mechanism rather than doing that work inline in the parent agent context.

- Prefer a general purpose or equivalent full-capability subagent unless the workflow explicitly requires another built-in or specialized type.
- Run independent research subagents in parallel when the runtime supports parallel execution.
- If the runtime cannot delegate, follow the owning agent's capability-failure path instead of silently falling back to inline execution.

## Workflow (execute in order)

1. **Understand the request**: Read the user's prompt carefully. Extract the research topic and any context the user provided — do NOT ask clarifying questions at this stage. Accept the prompt as-is, even if it seems vague or incomplete. The Product Context Inspector (step 3) will automatically discover existing context (specs, code, architecture) that fills most knowledge gaps. Any remaining ambiguities will be resolved with the user at step 8 (validation), when you have concrete findings to discuss instead of abstract questions.

2. **Create the session file** — living document updated throughout the research:
   - Template: Use [assets/research-template.md](assets/research-template.md) as base — do not omit any section
   - Path: `<working_directory>/.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/research.md` — where `{session_slug}` is a short, kebab-case summary of the research topic (e.g., `ai-powered-search`, `cart-pricing-rules`), and `<working_directory>` is the value provided in the environment as "Working directory" (not the workspace root folder)
   - Use: `write` tool to create file (create directories if they don't exist)
   - This file is updated iteratively after each phase. It is the discovery phase artifact.
   - Populate **Problem Context** and **Initial Hypothesis** with the information gathered in step 1.
3. **Gather project context via sub-agent** — before any external research, understand the current reality by spawning the **Product Context Inspector** sub-agent (see Sub-agents section). Do NOT run these queries yourself in the main context — delegate them entirely through the host runtime's native subagent/custom-agent mechanism to keep your context window clean.
   - Spawn the sub-agent using the **exact prompt template** defined in the Sub-agents section, filling in `{research_topic}` and `{research_context}` with the information from step 1.
   - Spawn it as a `general-purpose` sub-agent. It remains limited to read-only workspace inspection.
   - Wait for the sub-agent to complete before proceeding to step 4.
   - The summary from this sub-agent is the primary input for step 4 — it tells you what already exists (specs, code, architecture), which directly shapes which research sub-agents are worth activating and what specific questions to ask them.
   - Update the session file: write the sub-agent's findings into `## Specs` or `## Codebase Analysis` depending on whether relevant specs were found (see template).

4. **Discover available MCPs and assess research scope** — build the research sub-agent roster dynamically:

   **4a. Discover MCP servers** — list the MCP servers currently connected in this session. For each MCP, note its name and the tools it exposes. These are the dynamic information sources available for research — each relevant MCP can become a research sub-agent.

   **4b. Assess relevance** — read the Product Context Inspector's summary from step 3. For each discovered MCP, evaluate whether it can contribute meaningful information to this research:
   - What specific question would you ask this source? If you can't formulate a useful query, skip it.
   - Does the MCP's domain overlap with the research topic? (e.g., an API catalog MCP is relevant when researching integration opportunities; a CI/CD MCP is not relevant when researching UX patterns)
   - Was the MCP already consulted by the Product Context Inspector? If so, exclude it unless a distinct unresolved question remains that the Inspector did not answer.
   - For MCPs not already consulted by the Product Context Inspector, when in doubt lean towards including them — the cost of a sparse result is lower than missing a key finding.

   Also evaluate whether the **Web Research sub-agent** (always available — see Sub-agents section) is relevant for this research.

   **4c. Propose sub-agents for confirmation** — for each relevant source (discovered MCPs + Web Research if applicable), define a research sub-agent: a name, the MCP/tool it will use, and a one-line rationale for why it matters for this research. Then request confirmation. Each option should name the sub-agent, the information source it will consult, and the rationale. This makes the research process transparent and gives the user control over which sources are consulted. Include in this same round any scope or intent question already formulable (ambiguities from step 1, doubts raised by Sub-agent 0 findings) — one consolidated stop. **Do NOT proceed to step 5 until the confirmation is resolved.**

   **4d. Log the decision in the session file** — after the confirmation is resolved, update the `## Source Confirmation Log` section in the session file. Record every source that was discovered, which were proposed, which were confirmed, and which were excluded — with reasons.

5. **Parallel research**: Spawn the confirmed research sub-agents in parallel through the host runtime's native subagent/custom-agent mechanism. Each sub-agent receives:
   - The research topic and context from step 1
   - The specific MCP tools it should use (or `WebSearch`/`WebFetch` for the Web Research sub-agent)
   - A focused query derived from step 4b
   - Instructions to return a structured summary with source attribution (tag format: `[MCP-Name]` for MCP-based sub-agents, `[Web]` for Web Research)
   - Prefer a general purpose or equivalent full-capability subagent type unless the host has a better built-in fit for the requested source and tool usage
     Wait for all to complete.

6. **Consolidate & update session file**: Merge sub-agent results applying **Inditex-first priority** — internal solutions, capabilities, and patterns always take precedence over external alternatives. External findings serve as contrast, validation, or fallback. Update the session file with consolidated findings, **tagging each finding with its source sub-agent** (see Source Attribution Rules below).

7. **Present findings**: Share consolidated results directly in the conversation, structured per the template sections. Highlight key findings, recommendations, and open questions.

8. **Validate with user**: Present findings and request confirmation. This is the primary moment for user interaction — use it to:
   - Resolve any ambiguities from the original prompt that the research couldn't answer automatically (e.g., intended scope, desired outcome, constraints).
   - Confirm that the findings match the user's intent — the user may reveal that the research went in the wrong direction, which is cheaper to correct before discovery closes.
   - Iterate if the user provides feedback — update session file after each iteration until findings are validated.
   - **In delegated mode the findings travel inside the envelope**: the validation question's `context` must carry the key findings and the preliminary recommendation as short substantive bullets. The user answering has not seen your session file or this conversation — asking "do these findings fit?" without the findings on screen is a contract violation.

9. **Finalize discovery conclusions (MANDATORY)** — crystallize the validated findings in the session file:
   - Populate the conclusions with the scope covered, recommendations, risks, and open questions from the research phases
   - Ensure every conclusion remains traceable to its cited sources
   - Do **not** propose implementation details

10. **Pre-completion checklist (MANDATORY)** — verify before concluding:
    - ✅ All template sections populated with real content (no placeholders)
    - ✅ Every finding has a cited source with sub-agent attribution (see `Source Attribution Rules`)
    - ✅ `## Specs` or `## Codebase Analysis` populated with Sub-agent 0 findings (depending on which path was taken)
    - ✅ Research conclusions complete, sourced, and validated
    - ✅ Open questions explicitly listed or marked "None"
    - ✅ Session file reflects final validated state

## Confirmation Checkpoints

Two consolidated user stops — batch everything into them, never add intermediate ones:

- **Stop 1 (step 4)**: information sources + every scope/intent question formulable at that point, in one round.
- **Stop 2 (step 8)**: consolidated findings validation. Extra rounds happen only when the user's feedback genuinely requires another iteration.

## Sub-agents

There are two categories of sub-agents:

- **Static sub-agents** (always available, regardless of connected MCPs):
  - **Sub-agent 0 (Product Context Inspector)** — always runs at step 3. Its output feeds step 4.
  - **Web Research sub-agent** — uses built-in `WebSearch`/`WebFetch` tools to investigate external solutions, technologies, and industry patterns. Activated at step 5 if confirmed by the user at step 4.
- **Dynamic research sub-agents** — assembled at step 4 based on the MCPs available in the current session. Each relevant MCP becomes a candidate research sub-agent. The final roster must be confirmed before any research sub-agent is spawned.

### Sub-agent 0 — Product Context Inspector

**Type**: `general-purpose` sub-agent — it performs read-only workspace inspection only (no GitHub or code edits).
**Scope**: Gather existing product context related to the research topic via a two-tier cascade: SDD specs → direct code exploration. Relevant specs are the canonical source of truth; code under `repos/` is inspected only when no relevant specs are found for the research topic.
**When**: Always. This sub-agent runs at step 3 for every research, before any other sub-agent.

**Spawn prompt** — load [references/sub-agent-0-prompt.md](references/sub-agent-0-prompt.md), fill in `{research_topic}` and `{research_context}` with the information from step 1, and spawn it as a `general-purpose` sub-agent with the resulting prompt. Do NOT run these queries yourself — delegate entirely to the sub-agent.

### MCP-based Research Sub-agents (dynamic)

At step 4, the agent discovers which MCP servers are connected in the current session and evaluates each one as a potential research sub-agent. This means the research roster adapts automatically to the user's environment — if a new MCP is added (or one is removed), the skill adjusts without requiring edits.

An MCP already consulted by Sub-agent 0 is not automatically a research candidate. Exclude it unless a distinct unresolved question remains outside the Inspector's completed scope; record the exclusion in the Source Confirmation Log.

To define and spawn MCP-based sub-agents, load [references/mcp-sub-agent-prompt.md](references/mcp-sub-agent-prompt.md) — it contains the definition guide and the spawn prompt template with all `{placeholders}` to fill in. Pass the rendered prompt directly into the spawned subagent without replacing it with a summary such as "use the research skill".

### Web Research Sub-agent (static)

This sub-agent is always available regardless of which MCPs are connected — it uses built-in web tools.

**Scope**: Investigate external solutions, technologies, and industry patterns.
**Tools**: `WebSearch` and `WebFetch` for web pages, documentation sites, and comparison resources.
**Return**: Structured table of solutions/technologies found with: name, description, pros, cons, maturity, and source URL.
**Activate when**: The research benefits from knowing what exists outside Inditex — market alternatives, industry trends, competitor approaches, technology comparisons, or external benchmarks. Also activate when internal capabilities may have gaps that external solutions could fill.
**Skip when**: The user restricts the research to internal capabilities only (e.g., "I only want to know what we have internally, no external solutions").

### Source Attribution Rules

Every finding written to the session file must be traceable to the sub-agent that produced it. This lets readers understand where each piece of information comes from.

**Tag format**: Use inline tags at the end of each finding or table row:

- `[Spec]` — from Sub-agent 0, reading SDD specs in the current workspace (canonical source of truth)
- `[Code]` — from Sub-agent 0, using code exploration in `repos/` (fallback when no relevant specs are found)
- `[MCP-Name]` — from a dynamic MCP-based research sub-agent (use the actual MCP server name, e.g., `[DevHub]`, `[Geppetto]`, `[Confluence]`)
- `[Web]` — from the Web Research sub-agent
- `[User]` — directly from the user during the conversation

**Where to tag**:

- In prose sections: append the tag after the relevant sentence or bullet point. Example: `The cart service already implements pricing rules via a strategy pattern. [Code]`
- In table rows: add a `Source Agent` column (or append the tag in the existing `Source` column alongside the URL/reference). Example: `[DevHub — Pricing Engine v2](url)`
- In Key Findings: each finding must include its tag. Example: `1. An internal pricing engine already exists and is maintained by the Commerce team. [DevHub]`

**The `## Specs` and `## Codebase Analysis` sections**: These are the dedicated sections for Sub-agent 0 findings. When relevant specs are found, populate `## Specs`; otherwise populate `## Codebase Analysis`, even if the workspace contains unrelated specs. Write the sub-agent's structured summary into the corresponding section before any research sub-agent runs.

### Consolidation Rules

When merging sub-agent results at step 6:

1. **Inditex-first**: If an internal solution covers the need (fully or partially), it is the default recommendation. External alternatives are presented as contrast.
2. **Gap identification**: Where internal capabilities fall short, highlight the gap and present external options as candidates to fill it.
3. **No unsourced claims**: Every finding must carry its source tag and reference (MCP entry, URL, or file path). Discard any sub-agent output that lacks attribution.
4. **Skill-aware recommendations**: The Inditex ecosystem includes specialized skills by technology domain (frameworks, APIs, testing, etc.). When recommending an internal solution, indicate which technology domain skill would guide its implementation — but do not invoke those skills during research.

### Sub-agent Error Handling

Sub-agents may fail or return insufficient results. Apply these rules:

- **Empty or irrelevant results**: Log the source as "consulted but yielded no findings" in the Source Confirmation Log. Do NOT invent findings to compensate — an empty result is a valid data point (it means the source has no coverage for this topic).
- **MCP tool errors or timeouts**: If an MCP tool fails (connection error, timeout, malformed response), retry once. If it fails again, mark the source as "unavailable" in the Source Confirmation Log with the error reason, and proceed without it. Inform the user which source was unreachable.
- **Sub-agent 0 returns nothing**: If the Product Context Inspector finds no matching specs and no relevant code, this simply means there is no existing internal context. Record this explicitly in the session file — it is a valid finding that shapes the research (greenfield scenario). Proceed to step 4 normally.
- **Partial results**: If a sub-agent returns some findings but clearly couldn't complete its query (e.g., rate-limited, partial MCP response), note the limitation alongside the findings and flag it as a potential gap for the user to validate at step 8.

## Key Rules

- **Session file owns the research output**: The `research.md` session file at `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/research.md` is the only persistent semantic artifact. It must be updated iteratively and finalized before handoff. Under SDD, run the generated handoff command; do not author another semantic deliverable.
- **No speculation**: Never invent, assume, or infer information. Cite the source of every claim (URL, document, user input).
- **Ask when uncertain**: If information is not found, request user input. Do not fill gaps with assumptions.
- **Mark verification status**: Clearly distinguish verified facts from pending-confirmation items.
- **Iterative updates**: Update the session file after each meaningful step — don't wait until the end.
- **SDD persistence boundary**: When invoked inside SDD, do not edit `sdd-state.yml` or `trace.md`; run the generated handoff command and return its manifest-path response.

## Success Criteria

✅ **Session file created** — using the research-template.md structure, populated with Problem Context and Initial Hypothesis from step 1
✅ **Product Context Inspector sub-agent executed** — Sub-agent 0 spawned at step 3 using the defined prompt template (not run inline), returned a structured summary; findings written to `## Specs` or `## Codebase Analysis` in the session file
✅ **Information sources confirmed by user** — sub-agent selection presented and confirmed before research proceeded
✅ **Research sub-agents executed** — MCP discovery performed at step 4a; sub-agent selection justified with references to Sub-agent 0 findings; all confirmed sub-agents completed successfully
✅ **Findings consolidated** — Inditex-first priority applied, gaps identified
✅ **User validated findings** — confirmation received before handoff
✅ **Discovery conclusions complete** — scope, recommendations, risks, and open questions are populated with real, sourced content
✅ **Sources cited** — every finding traceable to a source with sub-agent attribution tag. If the citation is in prose, the tag is inline BEFORE the relevant sentence. If in a table, the tag is in the Source column or a dedicated Source Agent column.
✅ **Pre-completion checklist passed** — no placeholders, no unsourced claims
✅ **Completion response provided** — research was closed
✅ **SDD response contract followed when applicable** — the orchestrator-provided response shape was honored and research-specific content was included

## Anti-patterns to Avoid

- 🚫 **Inventing information** — every claim must have a source; never fill gaps with assumptions
- 🚫 **Skipping the Product Context Inspector sub-agent** — always spawn Sub-agent 0 at step 3 using the defined prompt template. Never inspect specs or code directly in your main context (it pollutes your context window with raw results). Delegate to the sub-agent and consume only its summary.
- 🚫 **Inspecting specs or code in the main agent context** — if you find yourself reading spec files or exploring `repos/` directly, stop. Spawn the Product Context Inspector sub-agent instead. The whole point is to keep the main context clean for synthesis and decision-making.
- 🚫 **Skipping the source confirmation gate** — at step 4, always request confirmation of the selected sub-agents and their information sources before spawning them. The user must confirm which sources to consult — never skip this interaction and jump straight to step 5
- 🚫 **Skipping MCP discovery** — at step 4a, always discover which MCP servers are available before deciding on research sub-agents. Never assume you know which MCPs are connected — discover them at runtime. Most research topics benefit from checking internal MCPs that expose product catalogs, knowledge bases, or API registries.
- 🚫 **Skipping research sub-agents without justification** — every sub-agent activation decision must be justified at step 4b, informed by Sub-agent 0's findings. Skipping a discovered MCP is valid when its domain clearly doesn't apply, but the rationale must be stated.
- 🚫 **Findings without source attribution** — every finding in the session file must include its source tag (`[Spec]`, `[Code]`, `[MCP-Name]`, `[Web]`, `[User]`). If you can't attribute a finding, don't include it
- 🚫 **Not updating session file iteratively** — the file must reflect progress after each step, not be written once at the end
- 🚫 **Leaving discovery conclusions empty** — scope, recommendations, risks, and open questions must be populated before concluding research
- 🚫 **Proposing implementation details** — research records validated discovery findings, not implementation approach
- 🚫 **Skipping user validation** — never finalize discovery without user confirmation of findings
- 🚫 **External-first recommendations** — internal Inditex solutions must always be evaluated and preferred when viable
- 🚫 **Mixing verified and unverified claims** — clearly distinguish what is confirmed vs what needs verification
