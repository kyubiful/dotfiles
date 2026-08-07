# SDD Trace

> Moderate-track trace. Mechanical change with no functional acceptance
> criteria. Most sections are recorded as `skipped` to satisfy the structural
> linter while keeping the artifact honest. Technical planning, verification,
> and retro/compound closure still run in this track.

## Session

| Field         | Value                    |
| ------------- | ------------------------ |
| Session       | example-moderate-session |
| Track         | moderate                 |
| Source spec   | n/a (moderate track)     |
| Current phase | bootstrap                |

## Input Contract Trace

| Contract ID | Path         | Affected ACs | Evidence     |
| ----------- | ------------ | ------------ | ------------ |
| CON-1       | [AIDEV_TODO] | [AIDEV_TODO] | [AIDEV_TODO] |

## Technical Plan Trace

| Work Item | Linked ACs | Repository  | Planned Change                                        | Status  |
| --------- | ---------- | ----------- | ----------------------------------------------------- | ------- |
| TECH-1    | AC-0       | diff target | Lightweight technical plan for the mechanical change. | pending |

## Implementation Trace

| Evidence ID | Linked ACs | Files / Commands | Result | Notes                                    |
| ----------- | ---------- | ---------------- | ------ | ---------------------------------------- |
| EVID-CODE-1 | AC-0       | diff             | pass   | Mechanical change; see code.md and diff. |

## Verification Trace

| AC ID | Verification Evidence | Status  | Notes                                                       |
| ----- | --------------------- | ------- | ----------------------------------------------------------- |
| AC-0  | diff                  | pending | Moderate-track verification uses diff evidence plus review. |

## PR / Review Trace

| PR           | Linked ACs | Review Status | Blocking Findings | Notes                                           |
| ------------ | ---------- | ------------- | ----------------- | ----------------------------------------------- |
| [AIDEV_TODO] | AC-0       | pending       | none              | Embedded review is appended to verification.md. |
