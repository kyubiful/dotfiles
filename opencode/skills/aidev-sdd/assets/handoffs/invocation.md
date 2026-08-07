# SDD Specialist Delegation

You are invoked as the {agent} specialist inside the `{phase}` phase of an orchestrated Spec-Driven Development session.

## Required outcome

{need}

## Operating contract

- `interaction_mode: delegated`.
- Load `<agent-dir>/skills/aidev-sdd/references/specialist-contract.md` and `<agent-dir>/skills/aidev-agent-questions/references/specialist.md` before any work.
- Execute your agent and owning skill completely. This request supplies routing context, not a replacement workflow.
- Do not edit `sdd-state.yml` or `trace.md`, and do not run SDD lifecycle validation commands.
- When blocked on user input, follow the delegated question-envelope contract and stop.
- Before a successful handoff, sign every owned Markdown artifact that requires a signature with `signature-append.py`.
- Use shell execution only for commands required by your owning workflow and these generated SDD helpers; do not run lifecycle mutation or validation commands.

## Context

- Session path: `{session}`
- Read-only inputs:
  {context}
- Session policy:
  {policy}

## Successful handoff

When the mission is complete, replace any `<placeholder>` values in the command below, then run it exactly once after adding only the repeated flags allowed for this phase. The phase instructions below identify the artifacts already included and the permitted flags; do not redeclare an included artifact. The command writes and validates the manifest. Return exactly the one-line response printed by it. The command defaults to `--status ready`; for a durable non-question blocker, replace that value with `blocked` and add the required `--blocker` flags.

```bash
{manifest_command}
```

{manifest_options}

Do not write the handoff YAML manually and do not add a narrative report to the final response.
