# aidev-verify-wsc - WSC/Backend Verification Adapter (aidev-verify reference)

> Progressive-disclosure reference for `aidev-verify`. Load this file only when the active verification session involves a backend, WSC, web service client, REST/HTTP API, service logic, repository, queue, database integration, or backend test outputs. The parent `aidev-verify` skill stays loaded; this reference adds the WSC/backend-specific contract on demand.

This reference is a technology adapter for `aidev-verify`. It captures backend and WSC test execution as verification artifacts and returns instructions for adding verification-ready evidence to `verification.md`. It does not own the lifecycle gate and does not edit framework state, traceability artifacts, or `verification.md`.

## Core rules

- Use the fixed `verification_artifacts/` directory for backend/WSC evidence.
- Store backend/WSC logs under `verification_artifacts/logs/`.
- Prefer commands explicitly planned in the test design. Infer commands only when no planned command exists.
- Capture stdout, stderr, exit code, duration, command, and working directory for every executed command.
- Do not run deploys, migrations, release tasks, publication tasks, destructive database operations, or tests against shared environments unless the test plan explicitly marks them safe.
- Do not write a separate WSC/backend report or edit `verification.md`. Return a `wsc_verification_contribution` block that tells the parent verifier what to add.
- Keep generated lifecycle artifacts and contribution text in English.

## Inputs

When invoked from `aidev-verify`, the caller supplies active framework/session inputs:

- Requirement file(s) from the active framework contract.
- Test design artifact when available.
- Implementation evidence artifact when available.
- Optional backend repository root when it differs from the lifecycle session root.
- Optional prior command output, CI URL, PR URL, local diff, or test report paths.

The AC list is not required as input. Infer AC coverage from requirements, test-plan mappings, command rows, and existing evidence IDs.

## Artifact layout

Use this fixed artifact layout:

```text
verification_artifacts/
`-- logs/
```

Each command log filename must include the evidence ID and a command slug, for example:

```text
verification_artifacts/logs/EVID-WSC-1-mvn-test.log
```

## Command discovery

Discover commands in this order:

1. Test design execution evidence rows.
2. Implementation evidence command results.
3. Caller-provided command list.
4. Look for the task file (defined at repo root) that exposes a collection of commands. You can invoke them with `task <task-name>`.

Integration, contract, smoke, mutation, coverage, or container-backed commands are inferred only when the test plan names that level or the repo exposes an obviously safe local test task. Otherwise, record them as not run.

## Safety filter

Never run commands containing deployment or destructive intent unless the test plan explicitly marks the target local, disposable, mocked, or seeded:

- `deploy`, `release`, `publish`
- `terraform apply`, `kubectl apply`, `helm upgrade`
- `migrate`, `db:reset`, `truncate`, `drop`, `delete`
- commands targeting production, staging, shared, remote, or real customer data

When safety cannot be proven, return `blocked` or a failed evidence gap for affected ACs instead of running the command.

## Workflow

### Step 1 - Resolve inputs

1. Create `verification_artifacts/logs/`.
2. Read supplied requirement file(s), test design, and implementation evidence when available.
3. Resolve backend repository root from caller input, active framework/session input, or current working directory.

Gate:

- [ ] Fixed artifact directories are available.
- [ ] Backend root is resolved.
- [ ] Test plan or fallback command inference is available.

### Step 2 - Build command plan

1. Extract planned `TEST-N` to command mappings from the test plan.
2. Preserve the command exactly when it is explicit and safe.
3. Link each command to known `TEST-N` and inferred `AC-N` IDs.
4. Assign sequential `EVID-WSC-N` IDs to command evidence rows.
5. Mark unsafe, missing, or ambiguous commands as skipped with reason.

Gate:

- [ ] Every command has evidence ID, working directory, safety status, and linked tests/ACs when known.

### Step 3 - Execute safe commands

For every safe command:

1. Run it from the resolved backend root.
2. Capture stdout and stderr to a log under `verification_artifacts/logs/`.
3. Record command, cwd, start time, end time, duration, exit code, and result.
4. Treat non-zero exit code as `fail` unless the test plan says the command is expected to fail for negative testing.

Gate:

- [ ] Every safe command has a log file and exit status.
- [ ] Every skipped command has a safety or availability reason.

### Step 4 - Analyze results

1. Map passing command logs to covered tests and ACs.
2. Map failing command logs to failing tests and affected ACs.
3. If a command could not run because dependencies or services were unavailable, mark affected ACs as `fail` or `blocked` unless an accountable owner accepts the risk.
4. Prefer explicit test-plan links over inferred AC links.

Gate:

- [ ] Every evidence row has result, source log, linked tests, and linked ACs when known.

### Step 5 - Return verification.md contribution

Do not write a separate WSC/backend report or edit `verification.md`. Return one structured contribution block that tells the parent verifier how to update it:

```yaml
wsc_verification_contribution:
  adapter: aidev-verify-wsc
  result: pass | fail | blocked
  add_to_evidence_reviewed:
    - evidence_id: EVID-WSC-1
      type: backend-test
      source: <command>
      result: pass | fail | blocked
      linked_tests: [TEST-1]
      linked_acs: [AC-1]
      log_path: <relative artifact path>
      notes: <short explanation>
  add_to_wsc_verification_evidence:
    - evidence_id: EVID-WSC-1
      command: <command>
      cwd: <path>
      log_path: <relative artifact path>
      exit_code: <integer or null>
      duration_seconds: <number or null>
      result: pass | fail | blocked
  add_to_command_results:
    - evidence_id: EVID-WSC-1
      command: <command>
      result: pass | fail | blocked
      log: <relative artifact path>
      notes: <short explanation>
  ac_status_suggestions:
    - ac_id: AC-1
      suggested_status: pass | fail | accepted-risk | deferred
      evidence_ids: [EVID-WSC-1]
      rationale: <short reason>
  skipped_commands:
    - command: <command>
      reason: <safety or availability reason>
      affected_tests: [TEST-2]
      affected_acs: [AC-2]
  notes: <optional free text>
```

The block must be complete enough for `aidev-verify` to update these `verification.md` sections without understanding backend-specific test tooling:

- `## Artifact Index`
- `## Evidence Reviewed`
- `## WSC Verification Evidence`
- `## Command Results`
- `## Acceptance Criteria Verification`
- `## Adapter Results`

When the parent verifier maps artifact paths into these sections, it renders them as filename-only links and registers each one in `## Artifact Index`.

## Constraints

- Do not edit source, tests, requirements, framework state, traceability, or `verification.md`.
- Do not install dependencies unless the caller explicitly approves.
- Do not start shared infrastructure or mutate shared data.
- Do not treat a command as passing without an exit status or trusted external result.
- Do not hide skipped integration tests; record them as evidence gaps.
