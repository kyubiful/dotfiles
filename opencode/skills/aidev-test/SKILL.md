---
name: aidev-test
description: Standard SDD test design workflow. Use when deriving a test strategy from an approved spec and technical plan, creating AC-driven test matrices, planning unit/integration/e2e/contract/smoke coverage, or preparing test evidence before implementation in the Spec-Driven Development lifecycle.
---

# aidev-test - SDD Test Design

This skill turns an approved functional spec and technical plan into an executable test design. It does not implement production code or test code. It defines what must be tested, at which level, and what evidence is expected so implementation and verification can prove the spec contract was met.

## Inputs

- `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/sdd-state.yml`
- `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/spec.md` or `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/specs/spec-*.md`
- `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/tech-plan.md`
- `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/trace.md`
- Optional repository architectural context from the workspace

## Output

Create or update:

```text
.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/test-plan.md
```

The file must follow `assets/test-plan-template.md` and every acceptance criterion must map to at least one planned test or explicitly documented accepted gap.

## Workflow

### Step 1 - Resolve topic and read contract

1. Read `sdd-state.yml` first.
2. Verify `current_phase` is `test-design` or that the orchestrator explicitly invoked this skill for test design.
3. Read `sdd-state.yml.specs[].path` to find specs, then read each listed spec file. If no spec list exists, discover `spec.md` / `specs/spec-*.md` in the session directory.
4. Read `tech-plan.md`.
5. Read `trace.md`.

Gate:

- [ ] Topic state exists.
- [ ] At least one spec is available.
- [ ] `tech-plan.md` is available.
- [ ] `trace.md` is available.

### Step 2 - Extract acceptance criteria

Extract every acceptance criterion from the spec source. Normalize each one to a stable ID:

- Preserve existing IDs such as `AC-1`, `AC-2`.
- If the spec has no IDs, assign `AC-{N}` in source order.
- Do not rewrite the functional meaning of the criterion.

Gate:

- [ ] Every acceptance criterion has an ID.
- [ ] No acceptance criterion is skipped.

### Step 3 - Design coverage

For each AC, choose the smallest sufficient set of test levels:

| Test level  | Use when                                                                           |
| ----------- | ---------------------------------------------------------------------------------- |
| Unit        | Pure business rules, validation, mapping, formatting, branching logic              |
| Integration | Multiple components, persistence, messaging, framework wiring, external adapters   |
| Contract    | Producer/consumer compatibility, API schema, event payload, backward compatibility |
| E2E         | User-visible workflow crossing UI/API/service boundaries                           |
| Smoke       | Critical path check after deploy or release                                        |
| Manual      | Only when automation is not viable; justify why                                    |

Prefer automated tests. Manual checks require a clear reason and expected evidence.

Gate:

- [ ] Each AC has at least one planned test level or a justified accepted gap.
- [ ] Risky behavior has more than one evidence path when appropriate.

### Step 4 - Author test plan

1. Read `assets/test-plan-template.md`.
2. Create `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/test-plan.md`.
3. Assign every test a sequential integer ID in the form `TEST-<N>` (`TEST-1`, `TEST-2`, `TEST-3`, …) in matrix order. Do not use semantic or level-prefixed IDs such as `TEST-CONTRACT-01` or `TEST-BE-INT-02`; the test level or area belongs in the `Level` column, not in the ID. This keeps IDs consistent with `trace.md`, `verification.md`, and the deterministic linter, which expects `TEST-<N>`.
4. Maintain the AC↔test relation in both directions. `## Acceptance Criteria Coverage` lists, per AC, the covering `TEST-<N>` IDs (`Covering Tests` column); `## Test Matrix` lists, per test, the `Linked ACs`. They are the same links seen from both sides — when you add, remove, or re-link a test, update both tables in the same edit so they never drift.
5. Pair each `TEST-<N>` with an `EVID-TEST-<N>` row in `## Execution Evidence Plan` that names the command/tool and expected output.
6. Fill every remaining section with concrete content.
7. Do not leave placeholders such as `[AIDEV_TODO]`, and do not keep the template example rows.

Gate:

- [ ] `test-plan.md` exists.
- [ ] Every test ID matches `TEST-<N>` with sequential integers and no semantic suffix.
- [ ] Every AC appears in `## Acceptance Criteria Coverage` with at least one covering `TEST-<N>` or a justified accepted gap.
- [ ] Each AC↔test link appears in both tables: every `TEST-<N>` under an AC's `Covering Tests` lists that AC in its `Linked ACs`, and vice versa.
- [ ] Every planned test has a matching `EVID-TEST-<N>` row in `## Execution Evidence Plan`.
- [ ] `test-plan.md` contains enough evidence for semantic review; the handoff manifest references it without repeating that evidence.

### Step 5 - Return orchestrator handoff

1. Do not edit `trace.md` or `sdd-state.yml` directly.
2. If an orchestrator provided a response contract, follow that contract exactly. Otherwise, return a concise completion report for the caller.
3. Persist planned tests, accepted gaps, risks, and blocker IDs in `test-plan.md`, then run the generated handoff command and return its printed response.

Gate:

- [ ] `test-plan.md` includes test design evidence for every AC and the manifest remains reference-only.
- [ ] The handoff manifest references `test-plan.md` without duplicating its test or gap content.

## Constraints

- Do not write production code.
- Do not write test code unless the user explicitly asks for test implementation.
- Do not invent acceptance criteria.
- Do not skip low-level tests just because an E2E test is planned.
- Do not plan only manual testing unless automation is genuinely not viable.
- Use sequential integer test IDs (`TEST-<N>`); never semantic or level-prefixed IDs such as `TEST-CONTRACT-01`.
- Keep `## Acceptance Criteria Coverage` and `## Test Matrix` mutually consistent; every AC↔test link must appear in both tables.
- Keep the output in English, even if the conversation is in another language.

## Completion response

Report:

1. Test plan path.
2. Number of acceptance criteria covered.
3. Planned test levels.
4. Any accepted gaps or risks.
5. Gate recommendation and next phase: implementation when accepted by the orchestrator.
