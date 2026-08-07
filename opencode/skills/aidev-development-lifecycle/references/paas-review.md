# Delivery Workflow — Phase 3: PaaS Configuration Review

## Phase 3 — PaaS Configuration Review

**Goal**: Ensure configuration introduced or required by the implementation is correctly placed in the PaaS file hierarchy (`configmap`, `secret`, `platform`, `deployments`, `image`, `pipe`, or local framework configuration).

This phase is **impact-gated**: assess every delivery, but when the implementation introduces no configuration, resolve it as `no changes required` without a deep-dive.

### Steps

1. Load the `paas-config` skill (`SKILL.md`).
2. Identify configuration introduced or required by Phase 2: properties, environment variables, secrets, feature flags, infrastructure services, PIPE topics, and deployment concerns.
3. For each change, run the `paas-config` workflow to determine the correct PaaS file, whether Sentinel Rules inject or rewrite values during `paas-cli prepare`, and whether placement follows PaaS conventions.
4. Apply configuration changes proposed by the skill.
5. If no configuration is needed, document `No PaaS configuration changes required — {justification}`.

### Gate checklist

- [ ] All configuration changes introduced by coding have been reviewed.
- [ ] Each change is correctly placed, confirmed already correct, or explicitly not applicable with justification.
- [ ] Phase 4 starts only after this gate passes.

### Constraints

- Do not skip PaaS review when configuration affects deployability.
- Do not mark Phase 3 `n/a` or `skipped` because it appears downstream, caller-owned, handoff-only, artifact-level, or outside the journal. Execute it or record a truthful blocker.
