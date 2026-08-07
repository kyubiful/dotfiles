---
name: aidev-review
description: Standard review contribution workflow. Use when reviewing an implementation diff or PR against the approved spec, tech-plan, test-plan, verification evidence, project rules, bugs, and security, and producing a review contribution with a gate recommendation.
---

# aidev-review - Review Contribution

This skill reviews an implementation diff or PR against the approved requirements or criteria, technical plan, test plan, verification evidence, project rules, bugs, and security concerns.

It does not produce a standalone phase artifact. It produces a review contribution block that the caller incorporates into the active review artifact.

## Inputs

- Framework session state
- Framework defined requirements or criteria
- Tech-plan.md when present for the active track
- Test-plan.md when present for the active track
- Code.md when present for the active track
- Verification draft or report.
- Trace.md when present for the active track
- PR diff, local diff, or changed-file list
- Optional `AGENTS.md` from the target repository

## Output

Return a review block.

The contribution must include a Markdown section the caller can place as the final top-level `## Review` section:

The section must follow `assets/review-template.md`. Every blocking finding must be linked to evidence, a file, an AC, or an explicit review dimension.

## Review dimensions

| Dimension                | What to verify                                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| Spec alignment           | Implementation satisfies the approved scope and does not introduce unapproved behavior                |
| Technical plan alignment | Code follows the planned architecture, affected repos, and sequencing unless deviations are justified |
| Test evidence            | Test design and verification evidence are consistent with changed behavior                            |
| Rules and conventions    | Changes follow repository instructions such as `AGENTS.md` when available                             |
| Bugs and edge cases      | Diff does not introduce likely runtime, data, or logic defects                                        |
| Security                 | Diff does not introduce exploitable vulnerabilities or unsafe patterns                                |

## Workflow

### Step 1 - Resolve topic and review target

1. Read artifacts the state to find requirements, read them, as well as tech-plan when present, test-plan when present, code journal, verification draft/report, and trace artifacts.
2. Resolve the review target:
   - If a PR is provided, use the PR diff.
   - If no PR exists, use the local diff in the target repository.
   - If neither exists, return a blocking finding asking for a PR or changed files.

Gate:

- [ ] Topic state exists.
- [ ] Required track artifacts are available or missing artifacts are explicitly documented.
- [ ] Verification statuses are available for every AC that belongs to the active track.
- [ ] A PR diff, local diff, or explicit no-diff rationale is available.

### Step 2 - Run review checks

Review the diff against each dimension:

1. Compare changed behavior to the approved spec and ACs.
2. Compare implementation shape to the tech-plan when the active track includes one.
3. Verify tests and verification evidence match the changed behavior.
4. If `AGENTS.md` exists, check repository rules and conventions.
5. Review for bugs and edge cases.
6. Review security-relevant diff sections.

Gate:

- [ ] Every review dimension is covered or explicitly marked not applicable.
- [ ] Security review was run or skipped with a reason.
- [ ] Every finding has severity, status, and owner/next action.

### Step 3 - Build the review section

1. Read `assets/review-template.md`.
2. Fill the review section with concrete findings and decisions.
3. Do not leave placeholders such as `[AIDEV_TODO]`.
4. Use `REVIEW-N` IDs for concrete findings. Use a single `REVIEW-0` row only when no findings exist.
5. Persist the review decision, finding summary, and evidence in the review contribution for the caller; lifecycle trace rows are derived from the completed verification artifact.

Gate:

- [ ] The contribution starts with `## Review`.
- [ ] The contribution includes review summary, contract review, findings, and combined gate decision subsections.
- [ ] Blocking findings make the combined verification gate fail.

### Step 4 - Return review contribution

If an indication of structure returned response is given, return your findings in that exact structure.

If the review fails, recommend that current phase fails the combined gate.

Gate:

- [ ] The contribution includes review status and blocking findings.
- [ ] The contribution proposes verification artifact updates, gate status, and next phase or blockers.

## Constraints

- Do not modify production code.
- Do not rewrite specs or acceptance criteria.
- Keep the output in English, even if the conversation is in another language.

## Completion response

When invoked directly, report:

1. The review contribution result.
2. Blocking findings count.
3. Gate decision.
4. PR publication status.
