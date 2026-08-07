# Delivery Workflow — Phase 5: Commit & Push

## Phase 5 — Commit & Push

**Goal**: Stage and commit remaining implementation changes — application source plus required PaaS or configuration files — on every working branch using Conventional Commits, then publish according to `delivery_mode`. In `github-delivery`, the product is a pushed, locally validated **draft PR** per repository. `local-only` may skip only publication, recorded as Phase 5 `done` with justification.

A handoff artifact never makes Phase 5 `n/a`; commit is always required.

### Steps

1. Load the `conventional-commits` skill (`SKILL.md`).
2. For each repo/branch execution mapping from Phase 1:
   - Check out its working branch.
   - **Stage only implementation results** produced by this run within `local_repo_path`, using explicit pathspecs. Never use `git add -A` or `git add .`. Do not stage `code.md`, SDD deliverables, session artifacts, or out-of-scope dirty files.
   - If an intermediate CI Handoff commit exists and no later changes exist, do not create another commit.
   - If later changes exist, including Phase 3 configuration, stage them and create a Conventional Commit. Otherwise create the final Conventional Commit for this run.
3. Publish only when allowed:
   - `github-delivery` — push every branch with unpushed local commits.
   - `local-only` — do not push unless the user or caller explicitly requests it; log `push skipped — local-only`.
4. Leave every PR in **DRAFT**. Do not mark a PR ready, inspect remote checks, or run remote fix loops.

### Gate checklist

- [ ] Every working branch has a Conventional Commit from this run, an intermediate CI Handoff commit, or a Phase 5-reused prior commit with `no implementation changes to commit` recorded.
- [ ] Each commit references its issue when one exists; `local-only` references the tech plan or session slug.
- [ ] Every branch is pushed when `delivery_mode` allows publication.
- [ ] Every `github-delivery` PR remains DRAFT.
- [ ] The final journal is written but no journal or SDD deliverable was committed or pushed.
- [ ] Only implementation changes — application source plus required PaaS or configuration files — staged with explicit pathspecs were committed or pushed.

### Constraints

- Do not mark Phase 5 `n/a` because the invocation requests only a handoff artifact. Commit remains owned; only local-only publication may be skipped with a Phase 5 `done` justification.
- Do not commit or push anything except implementation changes produced by this run: application source plus required PaaS or configuration files. Never stage the journal, SDD deliverables, session artifacts, or the configuration repository's `aicontext` branch.
- Do not force-push or rewrite published history without explicit user confirmation.
- Do not mark PRs ready for review, inspect remote checks, or run remote fix loops. Every PR remains DRAFT.
- Do not batch unrelated changes into one commit; use only Conventional Commit messages.
- Never commit or push it or touch the configuration repository's `aicontext` branch.
