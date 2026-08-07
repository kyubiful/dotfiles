# SDD Semantic Review Checklist

Use this checklist when deterministic validation passes but a phase gate still needs semantic judgement. The linter proves structure and trace shape; this checklist asks whether the evidence is meaningful.

## Functional Spec

- Every AC is observable by a user, caller, operator, or measurable system signal.
- No AC describes internal implementation as the success condition.
- Scope and out-of-scope boundaries are specific enough to prevent accidental expansion.
- Risks and assumptions name concrete uncertainty, not generic delivery risk.

## Technical Plan

- Every task maps to at least one AC or explicitly supports cross-cutting delivery.
- Every `How` section names concrete files, contracts, commands, or verified patterns when those facts are known.
- Verification gates describe executable proof, not a restatement of the AC.
- Cross-repository dependencies identify producer, consumer, order, and compatibility expectations.

## Test Design

- Each AC has the smallest sufficient automated evidence path, with manual checks justified only when automation is not viable.
- Expected evidence includes command, test name, assertion, screenshot, log, metric, or other concrete proof.
- Risky behavior has more than one evidence path when a single test level is weak.
- Accepted gaps name owner, reason, and impact.

## Implementation Evidence

- `code.md` records actual commands, files, tests, and commits.
- `trace.md` includes `EVID-CODE-*` entries linked to each implemented or preserved AC.
- `sdd-state.yml` records the implementation gate result and does not advance on weak or missing evidence.

## Verification And Review

- Verification statuses are supported by evidence produced after the implementation, not by plan text alone.
- A passing AC has command output, test evidence, diff evidence, release smoke evidence, or accepted owner evidence.
- Review findings are tied to ACs, files, security dimensions, or explicit non-functional concerns.
- Accepted risk and deferred scope include owner and rationale.

## Release And Observation

- Smoke checks prove released behavior, not only deployment success.
- Observation signals cover the AC impact or clearly record signal unavailability.
- Follow-ups are recorded as backlog or retro actions instead of hidden in prose.
