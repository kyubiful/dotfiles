# Sub-agent 0 — Product Context Inspector: Spawn Prompt

Use this exact template when spawning the Product Context Inspector **general-purpose** sub-agent at step 3. Fill in `{research_topic}` and `{research_context}` with the information gathered in step 1.

```
Gather product context for: {research_topic}

Context: {research_context}

You inspect the CURRENT workspace only and perform no edits. Follow this two-tier cascade IN ORDER. Tier 2 is reached ONLY when Tier 1 finds no relevant specs.

---

## TIER 1 — SDD Specs (canonical source of truth)

Specs are the canonical source of truth in an SDD workspace, so they always take priority over code.

1. Check whether a specs directory exists in the current workspace at the framework defined path.
2. If it exists, inspect the specs that match `{research_topic}`:
   - Browse the framework defined spec directories and read the `spec` files whose domain or name relates to the topic.
   - Digest what is already specified, in scope, contracted, or decided.
   - Tag every finding: `[Spec]`.
3. If a specs directory exists and one or more relevant specs are found, this tier is sufficient — do NOT proceed to Tier 2.
4. Proceed to Tier 2 if no specs directory exists or no specs in it relate to `{research_topic}`.

---

## TIER 2 — Direct code exploration (only when no relevant specs exist)

You reach this tier ONLY if no relevant specs were found for `{research_topic}`, whether or not a specs directory exists.

1. Explore the code under the `repos/` directory of the current workspace — each subdirectory there is a cloned repository involved in this research.
2. State that no relevant specs were found before reporting code-derived findings.
3. Use available code-intelligence capabilities when the task requires repository orientation, feature-area mapping, symbol ownership, dependency or wiring analysis, or relationship reconstruction. Use direct file search and reads for exact text or known small files. Verify all code-derived conclusions against source.
4. Tag every finding: `[Code]`.

---

Return ONLY this structured summary — no raw spec text, no raw code, no tool output:

## Specs
(Only if Tier 1 found one or more relevant specs. Omit this section if no relevant specs were found.)

### Spec inventory
A compact reference table — just enough to identify and locate each spec:

| Spec | Path | Status |
|------|------|--------|
| ... | ... | ... |

### Synthesized findings
This is the core output. Based on reading the relevant specs above, provide:
- **Current state of the topic**: what is specified, in scope, contracted, or explicitly out of scope — and why. `[Spec]`
- **Key decisions and context**: important constraints, trade-offs, or decisions captured in the specs. `[Spec]`
- **Covered vs pending**: which aspects are already specified and which remain open. This distinction is critical for scoping the research. `[Spec]`

### Implications for research
What should the research sub-agents investigate next, based on what the specs reveal?

## Codebase Analysis
(Only if Tier 2 was used — no relevant specs were found. Omit if Tier 1 found relevant specs.)

### Exploration methods
State which available code-intelligence capabilities were used and what they clarified, or state that direct file search and reads were used only.

### Relevant code found
What exists related to the topic: services, integrations, patterns, dependencies, configs. Include file paths and source tag `[Code]`.

### Architecture context
How the relevant parts are structured and connected. Base each conclusion on verified source.

### Gaps or absence
What was searched for but NOT found — this is equally informative.

### Implications for research
What should the research sub-agents investigate next, based on what the code reveals?
```
