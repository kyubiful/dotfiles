# research.md Template

Use this template when creating or updating the session file at `.aicontext/deliverables/sdd/{feature_name}/research.md`. Copy the structure below and fill in each section as the research progresses. Remove placeholder rows and replace with actual content.

---

```markdown
# Research: <Idea/Feature Title>

## Metadata

- **Start date**: YYYY-MM-DD
- **Author**: @username
- **Status**: In research | In refinement | Ready for design | Discarded

## Problem Context

What problem needs solving? For whom?

## Initial Hypothesis

What is the initial idea or proposal?

## Market Research

### Existing Solutions

| Product/Solution | Description | Pros | Cons | Source   | Agent   |
| ---------------- | ----------- | ---- | ---- | -------- | ------- |
| ...              | ...         | ...  | ...  | [link]() | `[Web]` |

### Relevant Technologies

| Technology | Potential Use | Maturity | Fit with Inditex | Source   | Agent   |
| ---------- | ------------- | -------- | ---------------- | -------- | ------- |
| ...        | ...           | ...      | ...              | [link]() | `[Web]` |

## Specs

> Populated from the Product Context Inspector sub-agent (step 3) when a specs directory exists in the current workspace and relevant specs are found. Specs are the canonical source of truth. If no relevant specs are found, this section is left empty and `## Codebase Analysis` is populated instead.

### Spec inventory

| Spec | Path | Status |
| ---- | ---- | ------ |
| ...  | ...  | ...    |

### Synthesized findings

- **Current state of the topic**: [What is specified, in scope, contracted, or explicitly out of scope — and why. `[Spec]`]
- **Key decisions and context**: [Important constraints, trade-offs, or decisions captured in the specs. `[Spec]`]
- **Covered vs pending**: [Which aspects are already specified vs still open. `[Spec]`]

### Implications for research

[What should the research sub-agents investigate next, based on what the specs reveal?]

## Codebase Analysis

> Populated from the Product Context Inspector sub-agent (step 3) as fallback when no relevant specs are found, including when the workspace contains unrelated specs. Code-derived conclusions are verified against source.

### Exploration methods

[Code-intelligence capabilities used and what they clarified, or direct file search/read only. Include source paths used to verify conclusions.]

### Relevant code found

[Services, integrations, patterns, dependencies, configs found — with file paths. Tag each: `[Code]`]

### Architecture context

[How the relevant parts are structured and connected. Tag each: `[Code]`]

### Gaps or absence

[What was searched for but NOT found. Tag each: `[Code]`]

### Implications for research

[What should the research sub-agents investigate next?]

## Ecosystem Analysis

### Discovered Capabilities

What already exists that can be reused? Tag each finding with the MCP source: `[MCP-Name]`

### Identified Gaps

What is missing? What would need to be built?

## Evaluated Alternatives

### Option A: <name>

- Description:
- Pros:
- Cons:
- Estimated effort:
- Risks:

### Option B: <name>

...

## Recommendation

Which option is recommended and why?

## Research Conclusions

### Key Findings

1. [Finding — include source tag: `[Spec]`, `[Code]`, `[MCP-Name]`, `[Web]`, or `[User]`]
2. ...
3. ...

### Scope

- **Covered in this research**:
  - ...
- **Pending investigation**:
  - ...

### Resolved Questions

| Question | Answer | Source   |
| -------- | ------ | -------- |
| ...      | ...    | [link]() |

### Open Questions

| Question | Context | Suggested Action |
| -------- | ------- | ---------------- |
| ...      | ...     | ...              |

### Risks

| Risk | Impact          | Notes |
| ---- | --------------- | ----- |
| ...  | High/Medium/Low | ...   |

## Research Status

- [ ] Problem context documented
- [ ] Alternatives identified and analyzed
- [ ] Pros/cons documented with sources
- [ ] Recommendation proposed
- [ ] Conclusions validated with user
- [ ] Discovery conclusions finalized

## Sources

- [Source 1](url)
- [Source 2](url)

## Source Confirmation Log

> Populated at workflow step 4. Records which information sources were discovered (MCPs + Web Research), which were proposed as relevant, which the user confirmed, and which were excluded. An MCP already consulted by the Product Context Inspector is excluded unless a distinct unresolved research question remains. Rows are dynamic — one per discovered MCP server plus the static Web Research source.

| Source                         | Type   | Discovered | Proposed | Confirmed | Reason                     |
| ------------------------------ | ------ | ---------- | -------- | --------- | -------------------------- |
| Product Context Inspector      | Static | ✅         | ✅       | ✅        | Always runs (step 3)       |
| [MCP name]                     | MCP    | ✅         | ✅/—     | ✅/—      | [Why proposed or excluded] |
| Web Research (External Market) | Static | ✅         | ✅/—     | ✅/—      | [Why proposed or excluded] |

## Decision History

| Date       | Decision | Reasoning |
| ---------- | -------- | --------- |
| YYYY-MM-DD | ...      | ...       |

---
```
