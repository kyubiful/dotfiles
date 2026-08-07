# SDD Specialist Contract (delegated mode)

This is the **complete SDD framework contract for delegated specialists**. When you are invoked as a specialist inside an orchestrated SDD session, load this file instead of `<agent-dir>/skills/aidev-sdd/SKILL.md` — the full skill is the orchestrator's playbook and contains orchestration rules that do not apply to you. Everything you must know as a delegated specialist is here or explicitly pointed to from here.

## Boundaries

- You operate inside `$CWD` only. Never read or write outside the current working directory and its subdirectories.
- You may **read** `sdd-state.yml`, `trace.md`, `contracts.yml`, and any phase artifact listed in your invocation context. You must **never edit** `sdd-state.yml` or `trace.md`; they remain orchestrator-controlled and are written through the state CLI.
- You create or update **only your owned phase artifacts** (plus assets your own skill defines). Reference them through the minimal handoff manifest instead of proposing lifecycle mutations.
- Do not run `sdd-lint.py`. Deterministic validation is orchestrator work.
- Do not ask the user directly and do not auto-confirm user gates. When you need user input, follow `skills/aidev-agent-questions/references/specialist.md` (load that contract before any work). Do not run the SDD state CLI. Batch every open question you have into one envelope round — never drip-feed single questions across rounds.
- If you need sub-work, use the host runtime's native subagent mechanism, preserving parallelism where sub-tasks are independent.

## Session layout (what you read and where you write)

Sessions live at `.aicontext/deliverables/sdd/sessions/{YYYYMMDD}-{slug}/`:

| Artifact                             | Owner phase       | Notes                                                                                           |
| ------------------------------------ | ----------------- | ----------------------------------------------------------------------------------------------- |
| `sdd-state.yml`, `trace.md`          | orchestrator      | read-only for you                                                                               |
| `contracts.yml`, `contracts/`        | orchestrator      | input contract manifest; every listed contract is a hard requirement your artifact must respect |
| `research.md`                        | discovery         |                                                                                                 |
| `plan.md`                            | functional-spec   |                                                                                                 |
| `spec-drafts/`                       | functional-spec   |                                                                                                 |
| `backlog-plan.yml`                   | functional-spec   |                                                                                                 |
| `specs/{domain}/{spec-name}/spec.md` | functional-spec   | session-local spec drafts are planner-owned                                                     |
| `tech-plan.md`                       | technical-plan    |                                                                                                 |
| `test-plan.md`                       | test-design       |                                                                                                 |
| `code.md`                            | implementation    |                                                                                                 |
| `verification.md`                    | spec-verification | review section is appended here                                                                 |
| `retro.md`                           | retro             | retrospective report                                                                            |

Session artifacts use `scope: session`. Workspace-scoped handoff paths are limited to `.aicontext/deliverables/sdd/` in the current workspace; that SDD root may itself be a symlink to external storage, but nested paths may not escape its resolved target. Paths are relative, never absolute, and never contain `..`.

## Context reading discipline (token budget)

Before re-running discovery or detection work (repo stack detection, MCP source discovery, GitHub issue fetches), check `.aicontext/.cache/` for a fresh entry and populate it when you do the work. Cache entries are regenerable working data — never deliverables, never secrets.

## Required handoff

Your generated request provides the exact manifest command. On successful completion:

1. Run the phase-specific `submit-handoff` command embedded in your generated request, adding only its documented repeated flags.
2. Return exactly the one-line `My handoff is in: ...` response printed by the script.

The script-generated manifest contains only references and non-derivable classifications:

- `schema_version: 1`
- the delegated `phase`
- `status: ready | blocked`
- named artifacts with `kind`, `scope`, and `path`
- spec artifact relations, optional `replaces` references, explicit `spec_removals` for dropped drafts, and Retro `spec_deletions` for canonical packages already removed
- contract-to-spec/AC mappings as IDs only when the functional-spec phase must establish non-derivable traceability
- blocker IDs already persisted in a referenced artifact

Do not copy semantic content from an artifact into the manifest. In particular, do not repeat ACs, tasks, tests, evidence descriptions, risks, trace rows, hashes, timestamps, or state-transition instructions. The state CLI derives and validates lifecycle views from the artifacts.

Do not write or edit handoff YAML manually. If the generated command cannot express a required dynamic value, treat that as `contract_failure` rather than inventing a field or bypassing the script.

Keep acceptance criteria in their normal Given-When-Then form. When input contracts are present, express their non-derivable relation through `contract_mappings` in the functional-spec manifest; do not alter AC prose to embed contract metadata.

If you are blocked on user input, follow the delegated envelope contract **instead of** returning the handoff, after persisting the durable recovery checkpoint required by the specialist question contract.

## Artifact signature

Before returning your handoff, sign your owned artifact with one command — the script owns the mechanical fields and is idempotent on re-runs:

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/signature-append.py --artifact <owned-artifact.md> \
  --agent <YourAgentName> --assistant <vscode|opencode|copilotcli|claudecode> --model "<model name>"
```

Load `<agent-dir>/skills/aidev-sdd/references/artifact-signature.md` only if you need guidance on the two self-reported fields.

## Contracts

If your invocation context includes `contracts.yml` entries relevant to your phase, treat each listed contract as a non-negotiable requirement. In delegated mode you never edit `contracts.yml`; surface contract gaps or unmappable contracts as blockers in your handoff. Load `<agent-dir>/skills/aidev-sdd/references/contracts-guide.md` only when you must interpret a contract's lifecycle.

## Completion audit

Before returning `completed`:

- your owned artifact exists on disk, has no `[AIDEV_TODO]`/`[PENDING]` placeholders in sections your phase owns
- the envelope `questions` list is empty and no stop reason applies
- every manifest reference resolves to a concrete file or blocker ID
