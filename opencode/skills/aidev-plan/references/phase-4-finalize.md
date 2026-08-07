# Phase 4 — Verify & Finalize

> This file contains the complete instructions for Phase 4. This is the final phase. The plan's specs and backlog projection are the deliverable.

1. **Pre-completion checklist** — verify all items in §Success Criteria (in SKILL.md) are met before concluding. In particular, verify:
   - All approved spec drafts listed in the Spec Registry exist under the session
   - `spec-relations.md` exists in the session root (if multi-spec plan with inter-spec contracts)
   - Spec Registry in plan.md is populated and matches spec files on disk
   - `backlog-plan.yml` exists, references every planned spec with a `change_kind` classification, and does not duplicate spec body content
2. Update session file status to `✅ Complete`.
3. Inform the user that the plan is complete and available at the session file path for future reference. Note that the plan package consists of:
   - `plan.md` — the session file (registry, clarifications)
   - `backlog-plan.yml` — change-aware backlog/roadmap projection generated from the specs
   - `sessions/{YYYYMMDD}-{session_slug}/specs/{domain}/{spec-name}/spec.md` — session-local spec drafts (the working spec for each approved spec; promoted to canonical at cycle close)
   - `spec-relations.md` — inter-spec contracts registry in the session root (if applicable)

## Gate

When finalization is complete:

- All §Success Criteria (in SKILL.md) verified
- Status set to `✅ Complete`

Announce completion to user.
