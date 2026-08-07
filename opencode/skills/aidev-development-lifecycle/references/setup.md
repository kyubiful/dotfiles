# Delivery Workflow — Phase 1 Setup CLI

Phase 1 is executed exclusively by the deterministic script at [`skills/aidev-development-lifecycle/scripts/setup.py`](../scripts/setup.py). This reference defines how the lifecycle agent invokes the script and how to interpret its result. It does not duplicate the parser or GitHub reconciliation implementation.

## Exclusive setup boundary

- Use the CLI as the sole executor of Phase 1 setup. Do not manually create, adopt, edit, or reconcile technical issues, branches, draft PRs, backlog relationships, or `code.md` as a fallback.
- The agent may resolve invocation inputs and interpret CLI output, but it must not reproduce setup logic with direct `git`, `gh`, filesystem writes, or sub-agents.
- The CLI is only for environment and delivery setup. It must not inspect or modify application source, implement plan tasks, run implementation or validation gates, or perform later lifecycle phases.
- Run `inspect` first, then run `apply --confirm` only when inspection is ready. Exit code `1` or `2` is a hard Phase 1 stop: do not inspect application source or start Phase 2. In delegated mode, persist the required question envelope when user input is needed.

## Purpose

The script establishes one verified execution context per repository assigned by a Markdown tech plan:

- parses tasks, repositories, dependencies, technical gates, and execution order;
- resolves the optional functional parent backlog issue;
- discovers the assigned repository checkout under the active workspace;
- inspects or reconciles one technical issue, working branch, and draft PR per target repository;
- creates or refreshes the Phase 1 journal without persisting local checkout paths; and
- reports blockers instead of guessing when an artifact or relationship is unsafe to change.

The script does not read, scan, or modify application source code. It does not publish functional backlog items, perform coding, run validation gates, or commit implementation changes. Those responsibilities remain outside Phase 1 and must not be added to the CLI.

## Implementation layout

`setup.py` is only the executable and compatibility entry point. The implementation is split under `scripts/_lib/` by responsibility:

- `models.py` and `errors.py` define shared data and actionable failures;
- `text.py`, `tech_plan.py`, and `backlog.py` parse bounded Markdown/YAML-like inputs;
- `repositories.py` and `journal.py` handle workspace grounding and journal persistence;
- `planning.py` builds per-repository reconciliation plans;
- `github.py` owns GitHub, branch, and draft-PR reconciliation;
- `orchestration.py` coordinates inspect/apply workflows; and
- `cli.py` owns argument parsing and the process entry point.

The module boundaries are internal. The invocation contract remains the `setup.py` command documented below.

## Required invocation

Always provide an explicit `delivery_mode`:

- `github-delivery` — reconcile GitHub issues, branches, draft PRs, and the journal.
- `local-only` — verify the local checkout and current branch, record GitHub fields as `n/a`, and update the journal without GitHub mutations.

The script has two commands:

- `inspect` is read-only. It parses the plan, resolves repositories, reads the journal, and inspects recorded GitHub artifacts when GitHub delivery is selected.
- `apply` is mutating. It requires `--confirm` and performs the reconciliations described below.

`--workspace` is the repository trust root and is used only to resolve checkouts at `<workspace>/repos/<repo>`. `--session-path` is an independently explicit framework-session trust root. Host runtimes may mount or symlink that session outside the repository workspace; the CLI resolves and uses the explicit session without requiring physical containment beneath `--workspace`.

A normal GitHub delivery starts with inspection:

```text
python3 skills/aidev-development-lifecycle/scripts/setup.py inspect \
  --tech-plan <session-path>/tech-plan.md \
  --session-path <session-path> \
  --workspace "$PWD" \
  --delivery-mode github-delivery \
  --kind-label <repo-a>=kind/<technical-label> \
  --kind-label <repo-b>=kind/<technical-label> \
  --format text
```

After resolving every reported blocker, apply the same plan explicitly:

```text
python3 skills/aidev-development-lifecycle/scripts/setup.py apply \
  --tech-plan <session-path>/tech-plan.md \
  --session-path <session-path> \
  --workspace "$PWD" \
  --delivery-mode github-delivery \
  --kind-label <repo-a>=kind/<technical-label> \
  --kind-label <repo-b>=kind/<technical-label> \
  --confirm \
  --format text
```

For local-only delivery, omit `--kind-label` and use the explicit local mode:

```text
python3 skills/aidev-development-lifecycle/scripts/setup.py apply \
  --tech-plan <session-path>/tech-plan.md \
  --session-path <session-path> \
  --workspace "$PWD" \
  --delivery-mode local-only \
  --confirm \
  --format text
```

The default output is structured JSON. Use `--format text` for a short human summary. `--timeout` controls each git or GitHub subprocess and defaults to 30 seconds. `--backlog-plan` overrides the default `<session-path>/backlog-plan.yml` location.

## Plan parsing contract

The parser is deliberately line-oriented and fence-aware. A heading or table inside a fenced code block is treated as content, not as plan structure.

It requires:

- a first level-one heading; a leading `Tech Plan:` prefix and an all-caps backlog key such as `US-001:` are removed from the capability title;
- at least one `### Task <stable-id>: <title>` section;
- a `**Repo**` field in every task; and
- unique task IDs.

A task may name one repository or a bounded list such as `` `repo-a` and `repo-b` ``. A cross-repository task is included in each named repository's setup plan while retaining one stable task ID in the journal.

For every task, the script preserves the complete task section for the technical issue body and also extracts:

- repository and optional module;
- backlog item;
- dependencies;
- `Where`, `How`, and exit criteria; and
- source line range for diagnostics.

`### Gate: <repo> ...` sections are grouped by repository. Only checks under `**Technical checks:**` that look like bounded technical checks are copied to `## Definition of Done` in the technical issue body. Functional acceptance, user-journey, E2E, manual, visual, screenshot, VCP, browser, watch, interactive, server, and other long-lived checks are excluded. The script never copies a bare foreground server or watch command into a GitHub issue gate.

`## Execution Order` is parsed when present. Phase, task references, notes, critical path, and parallelizable text are returned in inspection JSON and the phase is recorded in the journal's Task Progress table. An absent execution order is valid; task order remains the order in the plan.

## Parent backlog resolution

The parent is a functional backlog issue, not a technical implementation issue. Resolution uses these sources in order:

1. Concrete GitHub issue URLs in the tech plan's `## Backlog Sources` table.
2. Published entries in `<session-path>/backlog-plan.yml`.

A backlog-plan entry is eligible only when all of the following are true:

```text
publish_decision: approved
github.sync_status: synced
github.issue_url: https://github.com/<owner>/<repo>/issues/<number>
```

For example, an item with `publish_decision: pending`, `issue_url: null`, and `sync_status: not-published` is reported as an unpublished backlog candidate, not as a resolved parent. The script does not publish it or create a parent issue as a side effect.

Resolution outcomes are:

- `resolved` — exactly one parent issue is available;
- `not-applicable` — no published parent issue is available; or
- `ambiguous` — multiple parent issues are available, so technical artifacts may be reconciled but the parent relationship is recorded as blocked.

When one parent is resolved, the script first attempts native GitHub sub-issue linking. If GitHub rejects or does not support the relationship, it creates or updates one managed, non-closing parent comment using:

```text
<!-- aidev-technical-issues:<session-slug> -->
```

It never uses `Closes`, `Fixes`, or `Resolves` for the parent backlog issue. An existing different parent is never replaced automatically.

## Repository discovery and safety

Repository discovery uses exactly the checkout at `<workspace>/repos/<repo>`. A plan using `owner/repo` maps to the corresponding nested path `<workspace>/repos/owner/repo` and also requires the checkout's `origin` to match that remote.

The script does not search other workspace locations, parent directories, `$HOME`, recent workspaces, global git metadata, or external worktrees. It does not clone, create a worktree, relocate a checkout, stash changes, reset files, or discard user work. A missing, path-escaping, detached, or remote-mismatched checkout is a blocker.

This repository boundary does not apply to the explicitly supplied framework `--session-path`. Repository checkouts remain physically bounded to `--workspace`; session artifacts are read and written only beneath the resolved explicit session.

A dirty working tree is reported but is not automatically cleaned. The assigned checkout remains the only execution checkout for that repository.

## GitHub reconciliation

`github-delivery` requires `gh` authentication and an explicit technical label mapping. The label must be one `kind/*` label other than `kind/story`; the script does not guess the corporate taxonomy. A single global label can be provided with `--kind-label kind/<technical-label>`, or mappings can be provided per repository.

For each target repository, `apply`:

1. creates or reuses a coder-created technical issue with the repository's task sections and technical checks only;
2. updates an open technical issue in place when its body is stale;
3. preserves an existing non-story `kind/*` label selected by a human and records the divergence, or adds the supplied label when no technical label exists;
4. refuses to reopen a closed issue and never adopts a `kind/story` backlog projection;
5. links the technical issue to the one resolved parent, when applicable;
6. reuses a journaled branch when it still exists, otherwise invokes `gh sherpa create-pr --issue <number> --yes` to create the working branch and draft PR;
7. reuses or creates the draft PR without changing a PR that is already ready for review; and
8. verifies that the PR body contains `Closes #<technical-issue-number>` for the same-repository technical issue.

Every GitHub mutation is followed by a read-after-write verification. A failure is returned in the repository result and does not silently create a replacement artifact.

The script uses the existing `gh-sherpa` extension. If it is not installed, `apply` installs `InditexTech/gh-sherpa` before creating a branch or PR. The operation remains explicit because `apply` requires `--confirm`.

## Local-only reconciliation

In `local-only`, the script does not call GitHub, create labels, create issues, create branches, or create PRs. It verifies the resolved checkout and its currently checked-out branch. On re-entry, a journaled branch that differs from the current branch is a blocker rather than an automatic branch switch.

The journal records `Issue = n/a` and `PR = n/a` for every local-only repository.

## Journal output and Phase 1 gate

`apply` writes `<session-path>/code.md` atomically. It creates or refreshes:

- **Repositories** — GitHub repository, branch, issue, PR, and setup status;
- **Backlog Links** — parent and technical issue relationship status;
- **Task Progress** — stable task IDs, repository, execution phase, and preserved previous task statuses; and
- **Phase Status** — Phase 1 plus the pending later phases.

The journal never stores `local_repo_path`; that value is resolved again from `$PWD`/`--workspace` on every invocation. Existing implementation evidence, key decisions, continuation iterations, and CI handoffs are preserved when the journal is refreshed. If `sdd-state.yml` exists, the output records the proposed `artifacts.code_journal: code.md` update, but the script does not edit `sdd-state.yml`.

Phase 1 is `done` only when every current target repository has a verified mode-appropriate setup and backlog-link status. Missing repositories, GitHub failures, unsafe branch/PR states, ambiguous parents, and unreconciled artifacts keep Phase 1 blocked or partial. The lifecycle must stop before Phase 2 when Phase 1 is not done.

## Exit codes and re-entry

- `0` — parsing and requested operation completed without blockers;
- `1` — inspection or apply completed with one or more actionable blockers; and
- `2` — invalid invocation, unreadable input, malformed plan, or unsafe command configuration.

The command is idempotent when the same session path and tech plan are used again. Re-entry uses `code.md` as reconciliation input, refreshes stale issue content, reuses verified branches and draft PRs, and never creates duplicates just because a previous invocation was interrupted.

On re-entry, journal placeholders such as `n/a`, `none`, and blank cells are treated as missing artifact references, never as issue, branch, or PR identifiers. A successful setup refresh updates Phase 1 and repository mappings while preserving existing Task Progress, implementation/validation evidence, decisions, continuation iterations, CI handoffs, downstream phase statuses, and the overall terminal status. Setup must not reset completed implementation work to `pending`.
