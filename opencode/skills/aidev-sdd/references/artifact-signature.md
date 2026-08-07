# Artifact Signature Protocol

Every specialist agent must append a signature metadata table to the end of its owned artifact before returning its handoff. This table identifies which agent, assistant, model, and rules version produced the artifact, enabling full provenance tracing and participant compilation at cycle close.

## Signing (script-first)

Run the bundled helper — it owns every mechanical field (Commit from the aicontext lock, Version Ref, truncation, idempotent replacement on re-runs):

```bash
python3 <agent-dir>/skills/aidev-sdd/scripts/signature-append.py \
  --artifact <owned-artifact.md> \
  --agent <AgentName> \
  --assistant <vscode|opencode|copilotcli|claudecode> \
  --model "<self-reported model name>"
```

You self-report only two fields:

- `--assistant` — the **tool/runtime you are executing inside**, not the model provider. `Assistant` answers _"what tool am I?"_: VS Code (including the Copilot panel) → `vscode`; OpenCode CLI → `opencode`; GitHub Copilot CLI → `copilotcli`; Claude Code CLI → `claudecode`. If you are an opencode agent using a GPT model served via Copilot's API, you are still `opencode`.
- `--model` — self-reported model name at write time (e.g. `Claude Fable 5`, `GPT-5.6-luna`, `Kimi-K2.7-code`).

The script resolves `Commit` (7-char sha) and `Version Ref` from `{CWD}/.aicontext/aicontext.lock` via `signature-extract.py`, and writes `null`/`null` when the lock is absent — it never blocks the handoff. Re-running it replaces the existing signature table instead of duplicating it.

## Signed artifacts

These session-local Markdown files must carry a signature table:

| Artifact          | Owner            |
| ----------------- | ---------------- |
| `research.md`     | AIDevResearcher  |
| `plan.md`         | AIDevPlanner     |
| `tech-plan.md`    | AIDevTechPlanner |
| `test-plan.md`    | AIDevTester      |
| `code.md`         | AIDevCoder       |
| `verification.md` | AIDevVerifier    |
| `retro.md`        | AIDevRetro       |

## Unsigned artifacts

These artifacts must **not** carry a signature table:

- `sdd-state.yml`, `trace.md`, `contracts.yml`, `backlog-plan.yml` — orchestrator-owned lifecycle files
- `changes.json`, `{YYYYMMDD}-{session-slug}.md` — changelog registry and change notes (provenance is carried as structured fields)
- Canonical `spec.md` under `specs/{domain}/{spec-name}/` — product contracts, no framework markers
- `spec-drafts/*.md` — transient planning scratchpads
- `ARCHITECTURE.md`, `AGENTS.md` — product context resources, no framework markers
