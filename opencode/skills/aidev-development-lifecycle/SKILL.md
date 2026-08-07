---
name: aidev-development-lifecycle
description: 'Use when starting or resuming an Inditex software delivery: resolve a tech plan, GitHub issue, or free-text objective; honor delivery_mode; run deterministic Phase 1 setup; reconcile workspace repositories, GitHub issues, branches, draft PRs, and the centralized code journal; and coordinate coding, PaaS review, validation, and commit phases. Trigger on "aidev-development-lifecycle", "delivery lifecycle", "tech plan", "phase handoff", "re-entry", "implement", "develop", or before writing production code in an Inditex repository.'
---

# Delivery Lifecycle

Before starting or resuming a delivery, load `skills/aidev-development-lifecycle/references/lifecycle.md`. It is the authoritative procedure for the centralized `<framework-session-path>/code.md` journal, re-entry reconciliation, status vocabulary, persistence, and final report.

## Phase procedure progression

After completing the current phase procedure and before starting the next phase, batch, or sub-agent, run the journal checkpoint defined in `references/lifecycle.md`. Do not advance while completed work is still recorded as `pending` or the phase being left is not truthfully recorded. If the checkpoint cannot be applied and verified, stop as blocked.

Always follow:

```
<phase-1> -> journal checkpoint -> <phase-2> -> journal checkpoint -> <phase-3> -> journal checkpoint -> <phase-4> ...
```

```
Phase 1: Delivery Setup & Branch Grounding     → GitHub setup by default, local-only grounding when explicitly requested
Phase 2: Coding                                → skill: aidev-code
Phase 3: PaaS Config Review                    → skill: paas-config
Phase 4: Validation                            → per-repo technical validator
Phase 5: Commit                                → skill: conventional-commits
```

# Input Resolution

Handle the input based on what you receive:

| Input type                 | What to do                                                                                                                                          | Why                                                                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Free text**              | Proceed to implement the stated objective.                                                                                                          | Direct execution without ceremony. The caller (developer or orchestrator) owns any progress tracking.                                  |
| **GitHub issue reference** | Fetch the issue body once, save it to a local temporary `tech-plan.md` (or a caller-provided destination), and treat it as the implementation plan. | The issue body IS the technical plan. Downloading once avoids repeated API calls and context loss if connectivity fails on re-entries. |
| **Path to a .md file**     | Use that file directly. Do NOT transcribe or relocate it.                                                                                           | The file is already prepared with full context and roadmap. Duplicating it wastes tokens and creates drift risk.                       |

Once input is resolved, the local fetched plan file or referenced markdown file becomes the definitive roadmap — trust it completely as described in Context Awareness above.

## Deliver mode

Before doing any work, resolve `delivery_mode`. delivery_mode is a session-policy context variable that determines how the implementation orchestrator sets up the delivery. It can be one of:

- `github-delivery` (default) — create or verify one issue, working branch, and draft PR per current target repository.
- `local-only` — when the caller's session-policy context forbids/rejects GitHub artifacts such as issues, branches, or PRs. Verify the local repository path and working branch instead, and record `Issue = n/a` and `PR = n/a`.

Honor a `delivery_mode` provided in the invocation's session-policy context exactly. Never infer `local-only` from the absence of an explicit commit/push request, generic host guidance about committing, caution about creating GitHub artifacts.

## Reference Files

| Reference       | Path                                                   | Purpose                                                                                                                          |
| --------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| Lifecycle       | [references/lifecycle.md](references/lifecycle.md)     | Phase index, journal lifecycle, continuation rules, status vocabulary, and final reporting                                       |
| Delivery setup  | [references/setup.md](references/setup.md)             | Setup CLI invocation, repository discovery, branch grounding, issue/PR reconciliation, journal refresh, and the pre-Phase-2 gate |
| Coding          | [references/coding.md](references/coding.md)           | Direct repository-scoped implementation, CI handoffs.                                                                            |
| PaaS review     | [references/paas-review.md](references/paas-review.md) | Configuration impact assessment and placement in the PaaS hierarchy                                                              |
| Validation      | [references/validation.md](references/validation.md)   | Parallel per-repository read-only validation, evidence reuse, failure aggregation, and targeted fix-pass rules                   |
| Commit and push | [references/commit.md](references/commit.md)           | Conventional commits, publication rules, draft PR handling, and terminal journal status                                          |

## Scripts

| Script             | Path                                                           | Purpose                                                                             |
| ------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Phase 1 CLI        | [scripts/setup.py](scripts/setup.py)                           | Read-only inspection and explicit apply reconciliation for tech-plan delivery setup |
| Journal checkpoint | [scripts/journal_checkpoint.py](scripts/journal_checkpoint.py) | Atomic Task Progress and Phase Status update with post-write verification           |
