# Retro spec-consolidation handoff

The canonical Retro manifest is built by the generated `sdd-state.py submit-handoff` command. Retro persists all semantic closure, compounding, consolidation, version and publication details in `retro.md`; repeated flags add references only.

For each created or updated spec, reference:

- the workspace-scoped canonical `spec.md`
- the workspace-scoped `changes/changes.json`
- the workspace-scoped per-session change note
- the session-scoped spec registry entry replaced by the canonical spec

For each retired spec, first record the identity and reason in `retro.md`, remove the complete workspace package, then declare `spec_deletions[].registered` and `spec_deletions[].package`. Do not reference deleted files as artifacts.

`accept-handoff --file` verifies created/updated files, verifies deleted packages are absent, and applies the spec registry changes together with state/trace. Keep semantic summaries in `retro.md`; do not copy them into the manifest.
