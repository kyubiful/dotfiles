# Delivery Workflow — Phase 2: Coding

## Phase 2 — Coding

**Goal**: Implement the approved work directly, respecting dependencies and preserving one continuous implementation context across repositories.

### Steps

1. Read **Repositories** in `code.md` and re-resolve each `local_repo_path` from `$CWD` as defined by Phase 1. A missing or unverified checkout returns work to Phase 1; never choose or create another checkout.
   - On re-entry, a `pending` journal row is not proof that implementation is absent. Inspect the assigned branch's existing commits and working diff against that task's Exit Criteria. Reuse and verify existing implementation, record it in the journal, and implement only genuine gaps; never restart or duplicate completed work merely because a prior invocation missed its journal update.
2. Load coding skills once before reading or changing application source.
3. Resolve execution:
   - With `tech_plan_path = none`, implement the user objective directly in each target repository. Do not invent an execution order beyond real dependencies discovered from the code.
   - With `## Execution Order`, parse phases, stable task IDs, target repositories, critical path, and parallel groups. Execute phases in order; a parallel group means its tasks have no dependency between them, not that they must be delegated.
   - Without an execution order, group tasks by repository and preserve every ordering or dependency cue in the plan.
4. Implement directly:
   - Work through one execution phase at a time and finish every prerequisite before consuming its result downstream.
   - Complete coherent repository batches before entering Phase 4.
   - Verify every Exit Criterion before marking a task done. Record blockers rather than guessing or silently narrowing scope.
5. After each execution phase or completed repository batch, form the implementation result directly from observed evidence:
   - task ID, title, status (`done`, `partial`, or `blocked`), and whether Exit Criteria are verified;
   - files changed and commands/results supporting the status;
   - batch-preparation or targeted-diagnostic evidence, including its scope, covered change/checks, and any reusable evidence;
   - non-obvious decisions, rationale, and rejected alternatives;
   - blockers and any required CI handoffs.
     A delegated YAML handoff is not required because the lifecycle owner and coding executor are the same agent.
6. Process CI handoffs after every completed execution phase when Exit Criteria depend on CI outputs, ChatBot commands, dispatches, or downstream artifact coordinates:
   - Commit affected completed work using `conventional-commits` only when an intermediate published artifact is genuinely required.
   - Push only when `delivery_mode` permits. If `local-only` blocks necessary publication, mark the affected task blocked.
   - Trigger the required CI action or PR comment using the Phase 1 draft PR when applicable; never fabricate a forbidden artifact.
   - Log action, PR comment, artifact, and `triggered` status in **CI Handoffs**.
   - If downstream work needs the result at build time, notify the user and wait until confirmed or verifiably available.
7. For a Phase 4-triggered fix pass, verify Phase 1 setup again, and directly fix only the failing repository mappings and check scopes supplied by validation. Preserve prior passing evidence unless the changed files invalidate it.

### Gate checklist

- [ ] Execution order and dependencies were followed.
- [ ] Every target task has verified Exit Criteria or a truthful partial/blocked disposition.
- [ ] `EVID-CODE-*` evidence, key decisions, blockers, and CI handoffs are recorded.
- [ ] All completed changes are ready for independent Phase 4 validation.

### Constraints

- Do not read, explore, or write source code before Phase 1 setup is complete, except for a `Small change` or `Validation only` follow-up selected by `aidev-code` after verified reusable state is recorded.
- Always prefer AMIGA framework components over custom or third-party alternatives when an AMIGA stack is detected.
