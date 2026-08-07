# Tech Plan: {Capability Title}

**Status**: DRAFT
**Date**: {YYYY-MM-DD}

<!-- CONDITIONAL: Include only when input is a GH issue -->

**Requirement Source**: {GH issue URL}
**Source type**: GitHub issue
**Source cache**: `.aicontext/.cache/gh-issues/{owner}/{repo}/{issue_number}.md` (local only; not a deliverable)

<!-- CONDITIONAL: Include only when input is a markdown file or plain prompt -->

**Requirement Source**: {source markdown path OR research.md OR prompt summary OR <framework-spec-path>/{spec-name}/spec.md}
**Source type**: Markdown file | Research artifact | Plain prompt | Stable SDD spec | Mechanical change prompt

## Purpose

{What is being built and why}

## Scope

**In scope**: {bulleted list of what the plan covers}  
**Out of scope**: {bulleted list of explicit exclusions}

<!-- END CONDITIONAL -->

<!-- OPTIONAL: Include when backlog-plan.yml contains published backlog items approved for this session. -->

## Backlog Sources

| Backlog ID | Type         | GitHub Issue                            | Source Spec                 |
| ---------- | ------------ | --------------------------------------- | --------------------------- |
| {US-001}   | {user-story} | {<https://github.com/org/app/issues/123}> | {specs/domain/spec/spec.md} |

---

## Adviser Guidance

<!-- Each adviser's response is appended here as it arrives. One subsection per adviser. -->

### {Adviser Domain}

**Prompt**: {prompt sent to adviser}  
**Guidance**: {concrete, actionable response received}  
**Verified**: {filled in Step 5 — yes/no + evidence — e.g., "Yes: codegen plugin in pom.xml, specs at src/main/resources/api/" or "No: framework supports it but repo does code-first"}  
**Applies to**: {which parts of the requirement this informs}

---

## Codebase Grounding

<!-- Populated during Step 5. Targeted code scan guided by adviser output. Each finding validates, corrects, or enriches the knowledge base for plan writing. If Step 5 was skipped (no-op), record the reason here. -->

### Validated

| Component                               | Repo        | Adviser Ref                          | Evidence                                            |
| --------------------------------------- | ----------- | ------------------------------------ | --------------------------------------------------- |
| {component name + method if applicable} | {repo name} | {which adviser domain referenced it} | {file path:line confirming existence and API shape} |

### Corrections

<!-- Corrections are authoritative overrides — downstream steps must respect these over adviser guidance when there is a conflict. -->

| What was claimed                                     | Actual state                                        | Impact on plan                          |
| ---------------------------------------------------- | --------------------------------------------------- | --------------------------------------- |
| {claim from adviser or Step 3 architectural context} | {what the code actually shows, with file path:line} | {how this changes what must be planned} |

### Discovered Exemplars

| Pattern needed        | Exemplar found                 | Path        | What to replicate                  |
| --------------------- | ------------------------------ | ----------- | ---------------------------------- |
| {what the spec needs} | {existing implementation name} | {file path} | {specific pattern worth following} |

### Consumption Contracts Captured

| Component                             | Signature / Usage                                               | Source           |
| ------------------------------------- | --------------------------------------------------------------- | ---------------- |
| {component.method or component usage} | {verbatim signature, parameters, return type, or usage pattern} | {file path:line} |

### Existing Partial Implementations

| Spec requirement        | Existing code             | Coverage                 | Gap                            |
| ----------------------- | ------------------------- | ------------------------ | ------------------------------ |
| {requirement from spec} | {existing implementation} | {what it already covers} | {what is missing for the spec} |

---

## Design Decisions

<!-- Populated during the deep interview (Step 6). Each entry records a decision point and the user's answer. -->

- **[Dimension]**: Q: {question asked} → A: {user's answer and chosen option}

---

## Implementation Plan

### Task {N}: {Task Title}

- **What**: {concrete action to perform}
- **Repo**: {repo name}
- **Backlog item**: {Backlog ID from Backlog Sources, e.g. US-001; use n/a only when no published backlog source exists}
- **Where**: {repo(s) and file paths — existing files to modify or new files to create, use relative paths starting from the repo root}
- **How**: {implementation mechanism - the following are guides to orient you how to fill this out, but not all may apply to every task. Include as much relevant detail as possible to ensure the task is actionable and clear to a coding agent.}
  - **Pattern/Exemplar**: {existing code to follow as reference — file path + what to replicate from it}
  - **Components to use**: {framework utilities, libraries, service clients from adviser guidance — include method signatures, accepted parameters, import paths}
  - **Conventions to respect**: {naming, structure, testing patterns from architectural context that constrain this task}
  - **Design decision applied**: {which user decision from Step 6 shapes this task, and how}
- **Depends on**: {task references, e.g. "Task 1", "Task 3" — omit if no dependencies}
- **Exit Criteria** (coder-oriented — "I'm done with this task when I've produced these artifacts"):
  - [ ] {files created/modified as specified in Where}
  - [ ] {new tests written covering the new code — name what is tested, not that it passes}
  - [ ] {new types/interfaces/exports that downstream tasks will consume, if applicable}

---

## Verification Gates

<!-- One gate per artifact (repository). Each gate is the contract for a verifications
     that run AFTER all tasks for this artifact are implemented. The verifier reads this section to know
     exactly what to check. Gates contain technical checks (build, tests, lint, no regressions).Write in imperative voice directed at the verifier. -->

### Gate: {artifact/repo name} (after Tasks {X, Y, Z})

**Technical checks:**

- [ ] Run `{build command from architectural context}` → exits 0, no compilation errors
- [ ] Run `{test command from architectural context}` → all tests pass, 0 failures ({test type}: {tool})
- [ ] Run `{lint command from architectural context}` → exits 0, no violations
- [ ] Confirm no regressions: test count ≥ previous count, no previously-passing test now fails

### Gate: {second artifact/repo name} (after Tasks {A, B, C})

**Technical checks:**

- [ ] {same pattern — build, test, lint, no regressions}

---

## AC Coverage

<!-- Navigation only: the source spec owns AC text, tasks own implementation detail, gates own concrete checks, and trace.md owns cross-phase traceability. -->

| AC     | Tasks              | Gates                      |
| ------ | ------------------ | -------------------------- |
| AC-{N} | Task {N}, Task {N} | Gate: {artifact/repo name} |

---

## Execution Order

| Phase | Tasks          | Notes                                    |
| ----- | -------------- | ---------------------------------------- |
| 1     | {task numbers} | {why this goes first / what it unblocks} |
| 2     | {task numbers} | {dependencies satisfied by Phase 1}      |

**Critical path**: {task sequence that determines minimum delivery time}  
**Parallelizable**: {tasks/phases that can run concurrently}
