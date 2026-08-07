# Workspace Preflight Handoff Contract

This contract is used by `AIDevOrchestrator` when it delegates workspace preflight to `AIDevInit` inside an SDD session flow.

**Routine validation is CLI-owned, not agent-owned.** The orchestrator first runs `sdd-state.py preflight {session-dir}`, injecting the guidance validator (`--validator skills/aidev-explore/scripts/validate-workspace-guidance.py` when `aidev-explore` is installed); the CLI executes it and persists `orchestration.workspace_preflight` directly (with `agent: sdd-state-cli`). `AIDevInit` is delegated **only** when that preflight reports blocked repositories that need initialization, and it receives the blocked repository list in its invocation. After `AIDevInit` returns, the orchestrator re-runs `sdd-state.py preflight` — the CLI re-validation is the source of truth for the final `ready`/`blocked` state, and the agent's handoff summary is recorded with `sdd-state.py decision-add`.

`AIDevInit` remains responsible only for workspace initialization. It must not edit `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{session_slug}/sdd-state.yml`, `trace.md`, `current_phase`, `phases`, or `gates`. The orchestrator owns persistence of the accepted handoff under `orchestration.workspace_preflight`.

## Required handoff

When invoked with this contract, `AIDevInit` must return:

```yaml
workspace_preflight_handoff:
  status: ready | blocked
  workspace_root: "."
  repos_checked:
    - repo-name
  already_initialized_repos:
    - repo-name
  newly_initialized_repos:
    - repo-name
  blocked_repos:
    - repo: repo-name
      reason: blocker summary
  validation_summary: concise summary of the validation and initialization result
```

## Orchestrator persistence

The orchestrator persists the accepted handoff as orchestration metadata:

```yaml
orchestration:
  workspace_preflight:
    status: ready | blocked
    agent: AIDevInit
    completed_at: <orchestrator timestamp>
    workspace_root: "."
    repos_checked: []
    already_initialized_repos: []
    newly_initialized_repos: []
    blocked_repos: []
    validation_summary: ""
```

If `status` is `blocked` or `blocked_repos` is non-empty, the orchestrator stops before specialist phase delegation, reports the blockers, and keeps the current SDD phase unchanged.
