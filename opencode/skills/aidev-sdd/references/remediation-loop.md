# SDD Bounded Remediation Loop

This reference is loaded by the orchestrator when a `spec-verification` gate fails and the fix belongs to an earlier phase inside the `technical-plan → test-design → implementation → spec-verification` window. It defines the loop contract and the orchestrator playbook for driving it. Specialist agents never load this reference — the orchestrator is the loop's sole controller.

## Orchestrator playbook

The `technical-plan → implementation → spec-verification` window is a bounded verify→refine loop. You are its controller. `spec-verification` is the evaluator: when its gate fails, you route the fix back to the owning phase, re-run, and re-verify until the ACs pass or the loop budget is spent.

When a `spec-verification` handoff recommends `fail` (or your gate-check fails on real AC failures):

1. **Classify the root cause** from `verification.md`:
   - Code defect (an AC is not satisfied by the implementation) → reroute target is `implementation`.
   - Design/plan defect (the approved plan is wrong) → reroute target is `technical-plan`.
   - Scope defect (an AC itself is wrong or missing) → this is **not** loop remediation; handle it through **Late contract handling** (reopen `functional-spec`). It always involves the user and resets the loop counter.
2. **Record and reroute**: run `sdd-state.py gate {session-dir} spec-verification fail --evidence "..."`, then `sdd-state.py reroute {session-dir} {implementation|technical-plan} --reason "..."`. The CLI counts the iteration and **refuses** the reroute once `orchestration.remediation_loop.max_iterations` is reached.
3. **Prepare focused remediation context**: identify **only the failing ACs and open findings** from `verification.md`. Do not re-derive the whole spec or plan; the owning specialist re-reads its persisted artifact and fixes incrementally. Then re-run `spec-verification` after the orchestrator has completed the correction cycle.
4. **Within budget, loop unattended in both modes.** Do not stop to ask the user between iterations, even in interactive execution — a remediation loop is one unit that runs to convergence or budget exhaustion. Consult `sdd-state.py next {session-dir}`; it reports `iterations/max_iterations` and the mode-aware guidance.
5. **On budget exhaustion (the CLI refuses the reroute)**, stop looping and escalate:
   - `interactive`: present the remaining failing ACs and the options through the native ask mechanism — accept the risk, defer the AC, fix it manually, or raise the budget (`sdd-state.py loop-budget {session-dir} {n}`).
   - `autopilot`: record a blocker in `sdd-state.yml` and report. Never fabricate an `accepted-risk`; accepting incomplete evidence requires the accountable owner.

Do not hand-edit the counter, and do not bypass the refusal with `--force` unless the user explicitly decides to continue. A passing `spec-verification` gate resets the counter automatically.

## Loop contract (technical-plan → implementation → spec-verification)

The `technical-plan → test-design → implementation → spec-verification` window is a **bounded verify→refine loop**. `spec-verification` is the loop's evaluator: when its gate fails, the orchestrator reroutes back to the owning phase, re-runs, and re-verifies until the ACs pass or the loop budget is spent. The loop reuses the existing `reroute` primitive — it adds no new phase, agent, or transition machinery — so it costs no extra orchestration overhead. The loop applies to the `moderate`, `complex`, `exhaustive`, and `smart` tracks; `simple` has no `spec-verification` phase and never enters it.

**Root-cause routing.** On a `spec-verification` failure, classify the failure and reroute to the phase that owns the fix:

- Code defect (implementation does not satisfy an AC) → reroute to `implementation`.
- Design/plan defect (the approved plan is wrong) → reroute to `technical-plan` (the CLI resets `test-design`/`implementation` in between automatically).
- Scope change (an AC itself is wrong or missing) → this is **not** loop remediation. Route it through **Late contract handling** / reopening `functional-spec`; it always requires user involvement regardless of mode and resets the loop counter.

**Budget (CLI-enforced).** `orchestration.remediation_loop.max_iterations` is a single global budget (default `3`, tune with `sdd-state.py loop-budget {session-dir} {n}`). Each verification-driven reroute into the window consumes one iteration; `sdd-state.py reroute` **refuses** once `iterations` reaches `max_iterations`, so the loop can never spin forever. The counter resets to `0` when `spec-verification` passes (convergence) or when the reroute target is an earlier scope phase (`functional-spec`). `status` and `next` report `iterations/max_iterations`. Older sessions without the block behave as before (no budget) until an orchestrator runs `loop-budget` once to opt in.

**Execution-mode behavior.** Within budget the loop runs **unattended in both modes** — the orchestrator reroutes, re-delegates, and re-verifies without stopping to ask the user. This is a deliberate exception to the interactive per-phase stop: a remediation loop is treated as one unit that runs to convergence or budget exhaustion. Only budget exhaustion interrupts:

- `interactive`: stop and present the remaining failing ACs and the options through the native ask mechanism — accept the risk, defer the AC, fix it manually, or raise the budget (`loop-budget`).
- `autopilot`: stop, record a blocker, and report. Autopilot must **never** fabricate an `accepted-risk` decision — accepting incomplete evidence requires an accountable owner.

**Token efficiency.** Keep each loop turn cheap: a remediation re-invocation must pass **only the failing ACs and open findings** from `verification.md` as the need/context (never re-derive the whole spec or plan). `reroute` already resets only the phases inside the window, so specialists re-read their persisted `tech-plan.md`/`code.md` and fix incrementally rather than rebuilding from scratch.
