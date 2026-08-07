## Review

### Review Summary

Summarize whether the implementation is ready to pass the combined verification/review gate and why.

### Contract Review

| Dimension                | Result | Evidence                      | Notes                                                                                          |
| ------------------------ | ------ | ----------------------------- | ---------------------------------------------------------------------------------------------- |
| Spec alignment           | pass   | verification.md               | Implementation remains within approved scope.                                                  |
| Technical plan alignment | pass   | tech-plan.md, code.md         | Implementation follows the planned approach, or the active track does not require a tech plan. |
| Test evidence            | pass   | test-plan.md, verification.md | Evidence covers acceptance criteria.                                                           |
| Rules and conventions    | pass   | AGENTS.md or repository rules | No blocking convention issues.                                                                 |
| Bugs and edge cases      | pass   | diff review                   | No blocking bugs found.                                                                        |
| Security                 | pass   | security review               | No blocking security findings.                                                                 |
| Traceability             | pass   | verification artifact         | Review outcome can be traced through the verification gate.                                    |

### Findings

| Finding ID | Severity | Status | Linked ACs       | Location | Description         | Required Action     |
| ---------- | -------- | ------ | ---------------- | -------- | ------------------- | ------------------- |
| REVIEW-0   | none     | closed | All verified ACs | N/A      | No review findings. | No action required. |

Use `REVIEW-0` only when there are no findings. Use `REVIEW-N` for real findings, with `blocking` severity for any issue that prevents the combined gate from passing.

### PR Publication

| Field        | Value              |
| ------------ | ------------------ |
| Published    | no                 |
| Review event | not-applicable     |
| Notes        | Local review only. |

### Combined Gate Decision

| Field             | Value                  |
| ----------------- | ---------------------- |
| Gate              | spec-verification      |
| Review decision   | pass                   |
| Blocking findings | 0                      |
| Combined decision | pass                   |
| Next phase        | next non-skipped phase |
