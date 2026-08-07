---
name: aidev-code
description: Coding expertise for Inditex technology ecosystem. Provides corporate coding conventions, leverages MCP tools for live framework documentation, and enforces security and testing practices. Adapts to available context — works with a pre-existing implementation plan, a workspace architecture file, or just a developer's prompt. Load this skill before writing code in any Inditex repository. Triggers on "coding conventions", "code guidelines", "aidev-code", "implement", "code this", "develop", or when about to write production code.
---

# aidev-code — Coding Expertise for Inditex

This skill is a knowledge container for writing production code within the Inditex technology ecosystem. It can be invoked from an orchestrating agent (with a full implementation plan) or directly by a developer (with just a task description). It adapts to whatever context is available and can be re-entered iteratively.

## Context Awareness

Before writing code, assess what you already know. This determines how much discovery is needed:

| If this exists...                                                                    | Then...                                                                                                                                                              | Why                                                                                                                                                                    |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/tech-plan.md`        | Trust it as the definitive roadmap. Do not re-validate.                                                                                                              | It was grounded against the codebase and validated with the user. Second-guessing wastes time and creates conflicting signals.                                         |
| Caller-provided `local_repo_path`                                                    | Treat that path as the only execution root for the repository. Do not create worktrees, clones, sibling checkouts, or move the task to another directory.            | SDD/AIContext sessions assign one checkout per affected repo. Moving the work breaks journal resumability and can fork the same feature across multiple working trees. |
| Architectural context for all repositories involved is already loaded in the session | Use it and explore only genuine gaps.                                                                                                                                | Rediscovering known project conclusions burns context tokens with no upside.                                                                                           |
| Neither a plan nor sufficient context                                                | Explore the project to understand the stack, structure, and conventions of the area you'll modify. Use sub-agents for parallel exploration when multiple gaps exist. | You need enough understanding to make sound implementation decisions. But explore only what's missing — the goal is confidence, not exhaustiveness.                    |

## Leveraging Skills/MCP Tools

The skills and/or MCP tools available in your session are your primary advantage over generic coding. They provide live, version-current knowledge about the Inditex ecosystem: frameworks, libraries, patterns, APIs, security configurations, testing setups.

**Before writing any production code**, discover and query the tools relevant to your task. This isn't optional ceremony — without it you'll produce code that looks correct but doesn't align with corporate conventions, causing code review rejections and maintenance burden.

**How to discover:**

1. Review the list of available skills and MCP tools in your session (they're listed in your system context).
2. Identify which ones are relevant to the detected stack and the specific task (documentation tools, framework-specific skills, API references, among others).
3. Query those specifically for the aspects below — targeted queries produce better results than broad "tell me everything" requests.

**What to look for:**

- Naming conventions and project structure patterns
- Error handling and logging approaches
- API and messaging patterns
- Framework components that solve the problem at hand (prefer these over custom or third-party solutions — framework components get maintained, upgraded, and comply with corporate policies automatically)
- Security configurations specific to the stack
- Any other topic relevant to the task that the tools cover.

**Example**: for a Java/Maven project with AMIGA, you'd look for documentation tools that cover AMIGA Java patterns, query them for the specific concern you're implementing (e.g., "data access layer conventions", "REST error response format"), and apply what they return over generic Spring patterns.

If no skills or MCP tools are available, fall back to codebase patterns exclusively. Never block on missing tools.

## Coding Priorities

When making implementation decisions, follow this hierarchy:

1. **Existing codebase patterns** — match the style, structure, and layering of the code around you. Consistency within a project is more valuable than abstract "best practice."
2. **Skills/MCP-sourced conventions** — the stack's canonical way of doing things, as reported by documentation tools.
3. **General best practices** — only when neither of the above provides guidance.

This order exists because code review and maintenance happen in context. A perfectly "correct" implementation that diverges from the surrounding code creates cognitive load for every future reader.

## Inditex Ecosystem First

When a capability exists in the Inditex technology ecosystem — AMIGA frameworks, internal libraries, corporate APIs, shared platform services — use it over any external alternative, regardless of perceived simplicity or popularity of the external option.

This is non-negotiable because internal solutions are purpose-built for Inditex's operational context: its security model, its compliance requirements, its infrastructure, its scale patterns. They are maintained by teams that coordinate upgrades and deprecations across the organization. External alternatives operate outside this controlled environment — they may work today but create compliance gaps, security audit findings, or upgrade conflicts that no corporate team will support.

**Practical implication**: before reaching for any external library or framework feature, query your available skills/MCP tools to check whether the Inditex ecosystem provides a solution. If it does, use it. For example: AMIGA Java's HTTP client over Spring's RestTemplate, AMIGA's caching component over a standalone Redis client, an internal messaging library over a community Kafka wrapper. The internal solution is always the right choice when one exists, because it carries corporate guarantees that no external package can provide.

## Implementation Cycle

Implement coherent repository batches. Write code, review security, and add tests with the behavior they cover. Avoid automatically running technical checks after each unit. [references/testing.md](references/testing.md) is authoritative for the timing and selection of tests, builds, linters, type checks, and formatters.

**Before writing code:**

- If `.tool-versions` exists, ensure correct versions are active. Wrong tool versions cause subtle bugs that waste hours to diagnose.
- If the project uses contract-first design (OpenAPI, GraphQL schemas, messaging contracts), verify generated sources are up to date. Hand-writing types that belong to the generator creates conflicts on the next generation run.

**Testing** — Load [references/testing.md](references/testing.md). Write tests for every new behavior, use the definition of done (from the plan, issue, or task description) to guide coverage, and follow that reference for all technical-check execution. Tests verify behavior, not implementation details.

## Success Criteria

Before signaling completeness, verify that all applicable criteria are met:

| Criterion                         | Evidence                                                                 |
| --------------------------------- | ------------------------------------------------------------------------ |
| ✅ Implementation scope completed | All planned units are implemented or explicitly marked blocked           |
| ✅ Code follows local patterns    | Reused nearby conventions, helpers, naming, and architecture             |
| ✅ Skills/MCP guidance checked    | Consulted available relevant tools, or recorded that none were available |
| ✅ Security reviewed              | Findings recorded, or N/A justified with concrete reason                 |
| ✅ Tests added or updated         | New behavior is covered, or non-applicability is explained               |
| ✅ Inditex ecosystem checked      | No external dependency introduced where a corporate solution exists      |
| ✅ No git operations performed    | Commit/PR remains caller-owned                                           |

## Output Contract

When this skill signals completeness, the following artifacts are expected to exist.

| Deliverable           | State                                                                |
| --------------------- | -------------------------------------------------------------------- |
| Production code       | Compiles, follows local patterns and corporate conventions           |
| Tests                 | Written for new behavior (if required)                               |
| Security              | Evaluated explicitly — findings resolved or N/A justified            |
| Implementation Report | Returned as structured output to the caller (not persisted to disk)  |
| Git state             | Working tree modified, nothing committed — caller owns git lifecycle |

The **Implementation Report** is the structured output this skill returns when signaling completeness. It enables the caller (orchestrator or developer) to aggregate progress across invocations. Contents:

| Section           | What it contains                                                   |
| ----------------- | ------------------------------------------------------------------ |
| Tasks completed   | List of implemented units of work                                  |
| Key decisions     | Non-obvious choices with rationale and alternatives considered     |
| Blockers          | Anything preventing full completion, with remaining work described |
| Security findings | Finding, area, status, and resolution for each evaluated concern   |

If anything prevents full completion (blocker, ambiguity, pre-existing failure), the report's Blockers section documents what remains and why.

## Boundaries

- **No git operations** (commit, push, branch creation, worktree creation, clone creation, checkout relocation). Whether invoked by an orchestrator or by a developer directly, the git lifecycle is not this skill's responsibility. Signal completeness; let the caller decide when to commit. When the caller provides a `local_repo_path`, work only inside that assigned checkout; if another checkout seems necessary, report a blocker instead of creating one.
- **No re-validating the tech-plan**. If one exists, it's the definitive roadmap. Implement it following the execution order.
- **No lifecycle artifact management**. Do not persist progress journals, update trace/state files, or run lifecycle gates. Return the Implementation Report so the caller can handle persistence and orchestration.
- **No custom implementations when a framework component exists**. Use skills and/or query MCP first. Custom code for problems the Inditex ecosystem already solves creates maintenance burden and diverges from upgrade paths.

## Anti-patterns

| Anti-pattern                                                           | Why it's harmful                                                                                                    | Correct behavior                                                                                                                    |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 🚫 Re-exploring what existing artifacts provide                        | Burns context budget rediscovering known conclusions                                                                | Check artifacts first. Explore only genuine gaps.                                                                                   |
| 🚫 Skipping skills/MCP queries when tools are available                | Hardcoded assumptions go stale. The ecosystem evolves; skills/MCP stays current.                                    | Always query available skills/MCP tools. Fall back to codebase patterns only if no tools exist.                                     |
| 🚫 Writing code before prerequisites pass                              | Wrong tool versions or missing generated sources cause subtle breakage                                              | Verify prerequisites before touching production code.                                                                               |
| 🚫 Silently skipping security evaluation                               | Vulnerabilities ship unreviewed                                                                                     | Evaluate explicitly. Record findings or justify N/A.                                                                                |
| 🚫 Writing all tests after all code is done                            | Failures are harder to diagnose when test coverage lags behind implementation                                       | Write tests with the behavior they cover, then follow the technical-check policy in [references/testing.md](references/testing.md). |
| 🚫 Choosing an ad-hoc technical-check cadence                          | Repeated checks waste time and inconsistent check selection misses regressions                                      | Follow the authoritative batch-first policy in [references/testing.md](references/testing.md).                                      |
| 🚫 Bypassing the repository technical-check policy                     | Ad-hoc commands drift from the repository workflow and duplicate or miss quality gates                              | Use the command-resolution rules in [references/testing.md](references/testing.md).                                                 |
| 🚫 Sequential inline exploration when sub-agents would be faster       | Blocks the main agent and fills context with exploration noise                                                      | Spawn targeted sub-agents for parallel exploration of gaps.                                                                         |
| 🚫 Creating another checkout for an assigned repo                      | Splits one feature across multiple working trees and makes the caller's journal path untrustworthy                  | Use the provided `local_repo_path` exactly; report blocked if it cannot be used.                                                    |
| 🚫 Using external libraries when Inditex ecosystem provides equivalent | Creates maintenance orphans outside corporate support, compliance gaps, and diverges from coordinated upgrade paths | Query skills/MCP tools first. If corporate solution exists, use it unconditionally.                                                 |

## Resources

| Reference           | Path                                           | Purpose                                                                  |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------------------------ |
| Testing conventions | [references/testing.md](references/testing.md) | Naming, 3A pattern, coverage, mocking, Object Mother, deterministic time |
