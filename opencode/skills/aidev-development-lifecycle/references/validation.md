# Delivery Workflow — Phase 4: Validation

## Phase 4 — Validation

**Goal**: Independently validate every implemented repository mapping using technical checks from the tech plan, repository tooling, and the code journal.

Phase 4 is mandatory whenever application code changes. It uses independent, read-only validator sub-agents and runs the complete applicable repo-local technical suite once per relevant repository state. With no tech plan, derive checks from repository tooling and `code.md`.

The first Phase 4 pass for a materially implemented repository is **complete validation**. Later passes after focused improvements are **partial validation** and rerun only failed or invalidated checks. Promote a partial pass back to complete validation when accumulated fixes materially broaden behavior or invalidate the repository-wide baseline.

## Parallelism and evidence reuse

- Use exactly one validator per repo/branch mapping in a validation pass. Launch all repository validators concurrently in one fan-out batch; do not wait for one repository before starting another.
- A repository validator owns that repository's complete deduplicated check set. Do not launch separate validators for lint, build, typecheck, formatting, or overlapping test suites in the same checkout because they duplicate startup and may contend for files or caches.
- Before dispatch, normalize checks by effective command and scope. When an aggregate task already includes narrower checks, run the aggregate once unless the narrower command is needed to localize a known failure. Do not run both `task test` and its identical `task test-unit`/`task test-integration` children merely to collect duplicate evidence.
- Treat a passing Phase 4 validator report as reusable evidence keyed by repository, branch, HEAD, dirty-diff fingerprint, command, and relevant configuration fingerprint. Do not rerun an unchanged passing check later in the same delivery. Phase 2 implementation evidence does not replace the first independent Phase 4 run.
- After a fix, invalidate only checks whose inputs intersect the changed files, plus their aggregate or dependency gates. Keep unrelated repositories and unaffected passing checks cached.
- Parallelize independent checks inside a repository only when the project or Taskfile provides an explicit safe aggregate/parallel command, or when commands are read-only, self-terminating, use isolated outputs, and cannot compete for generated files, formatter writes, coverage directories, build directories, ports, or package-manager locks. Otherwise run that repository's deduplicated checks sequentially inside its single validator.

### Steps

1. Build a validation matrix from Phase 1 mappings and the journal. Each repository row contains its deduplicated required checks, reusable passing evidence and fingerprints, checks invalidated by files changed since that evidence, and checks still required in this pass.
2. Spawn exactly one validation-only/read-only auditor sub-agent for each repository with required checks, launching all such validators concurrently. Do not spawn a validator for a repository whose complete required matrix remains covered by valid passing evidence.
3. Give every validator `target_repo`, `local_repo_path`, `issue_reference` (`n/a` in `local-only`), `working_branch`, `tech_plan_path`, `checks_required`, and `checks_reused`. Instruct it to read the local tech plan and journal; run only `checks_required`; accept `checks_reused` without rerunning; deduplicate overlapping commands; prefer one project aggregate over duplicate child commands; and never create multiple validators against the same checkout. Within a repository it may parallelize checks only under **Parallelism and evidence reuse**. It must continue after failures to inventory the failure set, bound every command by a timeout, and keep implementation rationale out of its prompt. A startup/liveness check uses a bounded background probe and termination, never a blocking server, watcher, or REPL.
4. Enforce this validator contract:
   - **Allowed**: read tech plan, journal, source/configuration, and git status/diff; run required technical checks; query corporate documentation only to understand how to run checks.
   - **Forbidden**: edit files, apply patches, write-mode formatters, snapshot updates, generated migrations, long-lived/interactive gates, commit/branch/push/PR actions, fixing failures, functional tests, AC decisions, or `verification.md` changes.
   - **Workspace guard**: capture a pre- and post-validation git-state fingerprint. If the workspace changed, report `workspace_mutations_detected`; never clean it up or fix it.
5. Require this structured report from each validator:

   ```yaml
   issue: "<issue reference or n/a>"
   repo: "<target repo>"
   branch: "<working branch>"
   status: "passed | failed"
   validation_scope: "complete | partial"
   scope_rationale: "<substantial implementation, focused improvement, or promotion reason>"
   validation_fingerprint:
     head: "<commit SHA>"
     dirty_diff: "<stable diff fingerprint>"
     config: "<Taskfile/toolchain/config fingerprint>"
   checks_reused:
     - name: "<check name>"
       evidence_ref: "<prior journal evidence ID>"
   checks_run:
     - name: "<check name>"
       result: "passed | failed"
       evidence: "<short command/result summary>"
   failed_checks:
     - "<failed check name>"
   non_compliance_reasons:
     - "<why the implementation does not satisfy the tech plan / DoD>"
   recommended_fix_focus:
     - "<specific coding area for the next Phase 2 fix pass>"
   readonly_guard:
     pre_validation_state: "<git status / diff fingerprint before checks>"
     post_validation_state: "<git status / diff fingerprint after checks>"
     workspace_mutations_detected:
       - "<file changed or generated during validation>"
     mutation_assessment: "none | generated-artifact | unexpected-source-change"
   ```

6. Aggregate all reports once after the concurrent fan-out completes. Reject duplicate reports for the same repo/branch mapping, persist new passing fingerprints, and retain reusable evidence from earlier passes.

## Coding↔Validation loop

1. If every report is `passed`, continue to Phase 5.
2. For failures, group reports by repo/branch mapping, return to Phase 2 fix-pass mode, and pass only `failed_checks`, `non_compliance_reasons`, and `recommended_fix_focus`. Keep the current execution mapping.
3. After each fix pass, compute the changed-file delta. Revalidate concurrently only the failed checks, checks transitively affected by that delta, and required aggregate gates. Do not rerun successful repositories or unaffected passing checks.
4. Repeat until all mappings pass or a mapping reaches three fix passes. At the limit, halt, set journal status to `failed`, report unresolved mappings, and never signal completion.

### Gate checklist

- [ ] Each repo/branch mapping has either one current validator report or a matrix entry proving its entire required check set is covered by reusable passing evidence.
- [ ] All repository validators with required work were launched concurrently, with no duplicate validator for one checkout.
- [ ] Each repository's check matrix was deduplicated; aggregate and child checks were not repeated without a localization reason.
- [ ] Validators used the local tech plan and journal, with no GitHub issue-body read.
- [ ] Validators ran independently in read-only auditor mode and did not intentionally mutate source, snapshots, migrations, or fixes.
- [ ] Workspace mutations are reported and classified before progressing.
- [ ] Every applicable technical gate was checked; functional validation and `verification.md` were not performed.
- [ ] Every report passed, every prior failure had a focused Phase 2 fix pass and re-validation, and no mapping exceeded the fix-pass limit.
- [ ] Successful validations are not re-run during later fix passes.
- [ ] Reused checks have matching HEAD, dirty-diff, command, and configuration fingerprints; every invalidated check was rerun.

### Constraints

- Do not read GitHub issue bodies during validation. Validators use the local tech plan, the code journal, and repository tooling as sources of truth.
- Do not allow validators to modify source files or fix failures. All fixes return through Phase 2 and `aidev-code`.
- Do not rerun a check merely because another check failed, another repository changed, a new validation pass started, or the orchestrator resumed. Rerun only when prior evidence is absent, failed, stale, or invalidated by relevant changes.
- Do not mark Phase 4 `n/a` or `skipped` because it appears downstream, caller-owned, handoff-only, artifact-level, or outside the journal. Execute it or record a truthful blocker.
- Do not proceed to Phase 5 until validation passes for every repo/branch mapping. Reaching the fix-pass limit is a terminal `failed` outcome, never completion.
