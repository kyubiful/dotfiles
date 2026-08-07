# SDD Trace

> Complex-track trace. Complex is spec-driven delivery: functional-spec,
> spec-validation, technical planning, implementation, verification, and
> retro/compound closure run, while discovery and test-design are recorded as
> skipped (test evidence design is folded into spec-verification).

## Session

| Field         | Value                              |
| ------------- | ---------------------------------- |
| Session       | example-complex-session            |
| Track         | complex                            |
| Source spec   | specs/example/example-spec/spec.md |
| Current phase | bootstrap                          |

## Input Contract Trace

| Contract ID | Path         | Affected ACs | Evidence     |
| ----------- | ------------ | ------------ | ------------ |
| CON-1       | [AIDEV_TODO] | [AIDEV_TODO] | [AIDEV_TODO] |

## Acceptance Criteria Trace

> Owned by `functional-spec`. Per-AC implementation and verification evidence lives in the Implementation Trace and Verification Trace sections (linked by AC ID), filled as each downstream phase runs. Do not add future-phase evidence columns here.

| AC ID | Acceptance Criterion | Source Spec  | Notes        |
| ----- | -------------------- | ------------ | ------------ |
| AC-1  | [AIDEV_TODO]         | [AIDEV_TODO] | [AIDEV_TODO] |

## Backlog Trace

| Backlog ID | Source Spec                        | GitHub Issue | Project      | Sync Status   | Notes                                                          |
| ---------- | ---------------------------------- | ------------ | ------------ | ------------- | -------------------------------------------------------------- |
| US-001     | specs/example/example-spec/spec.md | [AIDEV_TODO] | [AIDEV_TODO] | not-published | GitHub issue is a backlog projection, not the source of truth. |

## Technical Plan Trace

| Work Item | Linked ACs | Repository   | Planned Change | Status  |
| --------- | ---------- | ------------ | -------------- | ------- |
| TECH-1    | AC-1       | [AIDEV_TODO] | [AIDEV_TODO]   | pending |

## Implementation Trace

| Evidence ID | Linked ACs | Files / Commands | Result  | Notes        |
| ----------- | ---------- | ---------------- | ------- | ------------ |
| EVID-CODE-1 | AC-1       | [AIDEV_TODO]     | pending | [AIDEV_TODO] |

## Verification Trace

| AC ID | Verification Evidence | Status  | Notes        |
| ----- | --------------------- | ------- | ------------ |
| AC-1  | EVID-TEST-1           | pending | [AIDEV_TODO] |

## PR / Review Trace

| PR           | Linked ACs | Review Status | Blocking Findings | Notes        |
| ------------ | ---------- | ------------- | ----------------- | ------------ |
| [AIDEV_TODO] | AC-1       | pending       | none              | [AIDEV_TODO] |
