# SDD Trace

> Simple-track trace. Trivial mechanical change delivered by a single
> implementation delegation with inline verification evidence (diff plus
> validation command) recorded in `code.md`. All other lifecycle sections are
> `skipped` to satisfy the structural linter while keeping the artifact honest.

## Session

| Field         | Value                  |
| ------------- | ---------------------- |
| Session       | example-simple-session |
| Track         | simple                 |
| Source spec   | n/a (simple track)     |
| Current phase | bootstrap              |

## Implementation Trace

| Evidence ID | Linked ACs | Files / Commands | Result | Notes                                                        |
| ----------- | ---------- | ---------------- | ------ | ------------------------------------------------------------ |
| EVID-CODE-1 | AC-0       | diff             | pass   | Micro change; inline verification evidence lives in code.md. |

## Verification Trace

| AC ID | Verification Evidence                | Status  | Notes                                                                   |
| ----- | ------------------------------------ | ------- | ----------------------------------------------------------------------- |
| AC-0  | diff + validation command in code.md | pending | Inline verification; no separate spec-verification phase in this track. |
