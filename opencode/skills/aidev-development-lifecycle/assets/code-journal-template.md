# Implementation Journal — {session_slug}

<!-- Replace placeholders: session basename, session-relative plan path, ISO date, and github-delivery or local-only. Status starts in-progress; terminal values are complete, complete-with-follow-ups, blocked, or failed. Edit tables structurally; never use broad string replacement. Use the lifecycle checkpoint for progress/status updates and re-read the journal afterward. -->

> Tech plan: `{tech_plan_path}`
> Delivery mode: {delivery_mode}
> Started: {date}
> Status: {overall_status}

## Repositories

<!-- One row per target repository: name, owner/name, branch, and full issue/PR URLs. In local-only, use n/a for GitHub Repo, Issue, and PR. Status: created, reused, refreshed, local-only, partial, or blocked. Never store a checkout path. -->

| Repo | GitHub Repo | Branch | Issue | PR | Status |
|------|-------------|--------|-------|----|--------|

## Backlog Links

<!-- One row per target repository. Parent Issue is owner/repo#number; Technical Issue is a URL. Link Type: sub-issue, fallback-reference, or n/a. Status: linked, already-linked, fallback-reference, blocked, or n/a. Notes are non-closing; use none when empty. -->

| Backlog ID | Parent Issue | Technical Issue | Repo | Link Type | Status | Notes |
|------------|--------------|-----------------|------|-----------|--------|-------|

## Task Progress

<!-- One row per plan task, retaining its exact ID. Status: pending, partial, blocked, done, failed-validation, deferred, n/a, or accepted-risk. Phase is the plan execution group, not a lifecycle phase. Notes summarize proof and require a concrete reason for deferred, n/a, or accepted-risk. -->

| # | Task | Repo | Status | Phase | Notes |
|---|------|------|--------|-------|-------|

## Implementation Evidence

<!-- Add Phase 2 evidence only. A row may link multiple tasks and ACs; list canonical IDs explicitly, for example "AC-1, AC-2" —no ranges. Use unique, consecutive EVID-CODE-<n> IDs; never use EVID-VAL-* here. Cover every implemented AC with concrete files, commands, and observed results. -->

| Evidence ID | Task IDs | Linked ACs | Repo | Files / Commands | Result |
|-------------|----------|------------|------|------------------|--------|

## Key Decisions

<!-- Record non-obvious choices: selected approach, repository, rationale, and rejected alternatives. Use none only when no alternative was considered. -->

| Decision | Repo | Rationale | Alternatives |
|----------|------|-----------|-------------|

## Continuation Iterations

<!-- Leave empty initially. Before a continuation, add a row: strategy is incremental, targeted-revalidation, full-delivery, or blocked. List phases 1–5, for example `1=reused; 2=rerun; 3=rerun; 4=rerun; 5=rerun`; values are rerun, reused, not-applicable, or blocked. These are iteration metadata, not Phase Status. -->

| Iteration | Requested Change | Strategy | Evidence Baseline | Phase Dispositions | Validation Scope | Escalation / Blocker |
|-----------|------------------|----------|-------------------|--------------------|------------------|----------------------|

## CI Handoffs

<!-- One row per CI trigger. Use a full PR-comment URL or n/a; Artifact is a URL or path. Status: triggered, waiting, or complete. Leave empty when no handoff is required. -->

| Exec Phase | Repo | Action | PR Comment | Artifact | Status |
|------------|------|--------|------------|----------|--------|

## Phase Status

<!-- Keep these five rows. Status: pending, in-progress, done, partial, or blocked; completion requires all done. Notes cover setup, implementation, PaaS assessment, validation/risks, and commit/push/PR respectively. Continuation dispositions belong above, not here. -->

| Phase | Status | Notes |
|-------|--------|-------|
| 1 — Delivery Setup | | |
| 2 — Coding | | |
| 3 — PaaS Config | | |
| 4 — Validation | | |
| 5 — Commit | | |
