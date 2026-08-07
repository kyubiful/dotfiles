---
name: aidev-explore
description: Architectural exploration of all repositories in a workspace. Detects technology stacks, required tool versions, architecture patterns, project structure, coding conventions, integrations, runtime flows, and gotchas — running repository explorations in parallel via sub-agents. It also supports validation-only checks for existing repository guidance and generates repository-root Taskfiles only when local workflow evidence makes them applicable. Use this skill when the user wants repo-level architecture documentation, workspace architecture onboarding, ARCHITECTURE.md generation, Taskfile generation, or validation of existing repository guidance. Triggers on "explore workspace", "detect stack", "workspace architecture", "aidev-explore", "scan repos", "generate ARCHITECTURE.md", "generate Taskfile", "validate repository guidance", or when the user wants a technical overview of repositories in a workspace.
---

# aidev-explore — Repository Architecture Guidance Skill

Generate or validate repository-local `ARCHITECTURE.md`, `AGENTS.md`, and, when applicable, repository-root Taskfile guidance for repositories discovered in the current workspace.

The cost rule is simple: **scripts discover, detect, and validate; LLM sub-agents produce repository architecture knowledge and applicable Taskfile content**. In generation or refresh runs, the persistent output of this skill is the repository-local architecture guidance. In validation-only runs, the skill writes nothing.

## Output model

For every discovered repository, create or update:

```text
<repo>/ARCHITECTURE.md
<repo>/AGENTS.md
<repo>/Taskfile.yml   # only when Taskfile guidance is applicable
```

If applicable Taskfile guidance is needed and a repository already uses `Taskfile.yaml`, preserve that extension and treat that file as the repository-root Taskfile instead of creating `Taskfile.yml`.

These files are the complete persistent output whitelist for this skill: `ARCHITECTURE.md`, `AGENTS.md`, and optionally exactly one repository-root Taskfile when applicable. `aidev-explore` must not create or modify any other persistent file, regardless of path, name, purpose, or whether it is described as intermediate, support, debug, context, deliverable, backup, cache, or scratch material.

The generated architecture document is a complete repository architecture document, not a partial section. It is primarily an agent-facing architectural context artifact and secondarily a human-readable reference.

When Inditex artifact-typology context is available in the run, pass a compact `workspace_artifact_context` block to each repository exploration sub-agent. Use this context as a non-authoritative exploration aid, not as a complete product map. If no artifact-typology context is available, pass `available: false` and continue without inventing artifact roles or relationships.

It must preserve the required sections:

```markdown
# <repo-name> Architecture

## Overview

## Stack & Environment

## Project Structure

## Architecture & Patterns

## Contracts & Integrations

## Runtime & Data Flow

## Conventions

## Constraints & Gotchas
```

`references/architecture-doc-contract.yml` is the single source of truth for each section's purpose, expected content, empty-state wording, voice, uncertainty style, and constraints for `ARCHITECTURE.md`. Do not duplicate section-level guidance in prompts or workflow prose.

Validation-only mode does not create or update any files; it only checks whether the existing repository guidance satisfies the contracts below.

`AGENTS.md` remains the entry point for any agent operating on the repository. The skill owns one always-required architecture paragraph and one Taskfile paragraph that is required only when a repository-root Taskfile exists. It preserves everything else as written by the user or other tools:

1. `Repository architecture context lives in ARCHITECTURE.md. Always read it to acquire context and/or before making changes.`
2. When a repository-root Taskfile exists: `Local development commands live in the repository-root Taskfile (\`Taskfile.yml\`, or \`Taskfile.yaml\` when already present). Always prefer \`task <phase>\` for standard local workflows (\`install\`, \`build\`, \`lint\`, \`format\`, \`test\`, \`start\`).`

`references/agents-doc-contract.yml` is the single source of truth for required and conditional `AGENTS.md` paragraphs and forbidden stale local-dev block markers.

When present, the repository-root Taskfile owns the concrete local development commands. `references/taskfile-contract.yml` is the single source of truth for:

- canonical phase task names,
- variant naming,
- explicit `dir` requirements,
- evidence policy,
- task omission behavior,
- output constraints.

## Write policy

- If `<repo>/ARCHITECTURE.md` is missing, generate it.
- If `<repo>/ARCHITECTURE.md` exists, overwrite it only when the user explicitly asked to generate, update, or refresh architecture documents.
- If `<repo>/ARCHITECTURE.md` exists and the user did not explicitly request generation/update/refresh, report it as already present and skip writing for that repository.
- Generate or update a repository-root Taskfile only when Taskfile guidance is applicable for the repository.
- If Taskfile guidance is applicable and no repository-root Taskfile exists, generate `Taskfile.yml`.
- If Taskfile guidance is applicable and `Taskfile.yaml` already exists, update that file instead of creating `Taskfile.yml`.
- If the repository-root Taskfile exists, overwrite it only when the user explicitly asked to generate, update, or refresh repository guidance.
- If the repository-root Taskfile exists and the user did not explicitly request generation/update/refresh, report it as already present and skip writing for that repository.
- If Taskfile guidance is not applicable and no repository-root Taskfile exists, do not create one and do not add the Taskfile paragraph to `AGENTS.md`.
- If `<repo>/AGENTS.md` is missing after a generated or refreshed `ARCHITECTURE.md` validates, create it with the required architecture paragraph and, only when a repository-root Taskfile exists, the Taskfile paragraph.
- If `<repo>/AGENTS.md` exists, preserve all existing content, remove any stale `aidev-explore` local-dev managed block from older skill versions, append the architecture paragraph when absent, append the Taskfile paragraph only when a repository-root Taskfile exists, and fail validation if a missing Taskfile is still referenced.
- Do not create or modify any persistent file outside the output whitelist. The final chat report is the only place for run notes or execution summaries.
- During generation/refresh, track intended write targets in memory. Before final reporting, verify that the run created or modified only the output-whitelisted files. If any other persistent file was created or modified by this run, remove it before reporting; if it cannot be removed, report the run as blocked instead of ready.

## Deterministic helpers

- `scripts/detect-repo.py <repo_path>` — deterministic stack/build/tool detection plus local command-evidence inventory.
- `scripts/discover-repos.py --workspace <workspace_root>` — deterministic repository discovery.
- `scripts/validate-architecture-doc.py --repo <repo_path>` — validates generated `ARCHITECTURE.md` structure and path safety.
- `scripts/update-agents-architecture-context.py --repo <repo_path>` — creates or appends the `AGENTS.md` paragraph that points agents to `ARCHITECTURE.md` and removes the obsolete `aidev-explore` local-dev managed block when present; it never overwrites unrelated `AGENTS.md` content.
- `scripts/update-agents-taskfile-context.py --repo <repo_path>` — creates or appends the `AGENTS.md` paragraph that points agents to an existing repository-root Taskfile and removes the obsolete `aidev-explore` local-dev managed block when present; call it only after a Taskfile exists. It never overwrites unrelated `AGENTS.md` content.
- `scripts/update-taskfile.py --repo <repo_path> --content-stdin` — writes an applicable repository-root Taskfile idempotently from stdin, preserving an existing `Taskfile.yaml` extension when present and refusing ambiguous dual-file states.
- `scripts/validate-agents-doc.py --repo <repo_path>` — validates that `AGENTS.md` contains the required architecture paragraph, contains the Taskfile paragraph only when a repository-root Taskfile exists, and has no stale local-dev managed block markers.
- `scripts/validate-taskfile.py --repo <repo_path>` — validates that the repository-root Taskfile exists, declares Taskfile version 3, uses valid phase-variant naming, declares explicit `dir` values for included tasks, and contains no unsupported placeholder tasks.
- `scripts/validate-workspace-guidance.py --workspace <workspace_root>` — validation-only mode for already initialized workspaces; discovers repositories under `<workspace_root>/repos/` and validates architecture and agent guidance for each repository, validating Taskfiles only when present, without spawning sub-agents or writing files.
- `references/architecture-doc-contract.yml` — authoritative `ARCHITECTURE.md` contract.
- `references/agents-doc-contract.yml` — authoritative `AGENTS.md` contract for required and conditional discovery paragraphs.
- `references/taskfile-contract.yml` — authoritative repository-root Taskfile contract for local development commands when Taskfile guidance is applicable.
- `references/explore-agent-prompt.md` — repository exploration prompt; produces the `ARCHITECTURE.md` document and, when applicable, the repository-root Taskfile in a single sub-agent run.

## Operating modes

### Validation-only mode

Use this mode when repository guidance already exists and you want a deterministic readiness check without generating or refreshing documentation.

This mode:

- validates only repositories under `$CWD/repos/`,
- reuses `validate-architecture-doc.py`, `validate-agents-doc.py`, and `validate-taskfile.py` when a Taskfile is present,
- returns a per-repository readiness summary plus blocker details,
- does not spawn exploration sub-agents,
- does not run generation helpers,
- does not write files.

Implementation:

```bash
python3 <skill_path>/scripts/validate-workspace-guidance.py --workspace "$CWD"
```

If validation fails, report the failing repositories and the validator output.

## Generation and refresh workflow

### 1. Discover repositories

Workspace root is `$CWD`. Discover repositories with the bundled helper; do not hand-roll Bash for this step.

```bash
python3 <skill_path>/scripts/discover-repos.py --workspace "$CWD"
```

The helper discovers git repositories in `$CWD` itself, immediate children of `$CWD`, and immediate children of `$CWD/repos/`. Treat its output as the repository list for the rest of the run.

**Gate 1**

- [ ] `python3 <skill_path>/scripts/discover-repos.py --workspace "$CWD"` completed successfully.
- [ ] At least one repo was found.

### 2. Detect repository facts

For every discovered repository, run deterministic detection:

```bash
python3 <skill_path>/scripts/detect-repo.py <repo_path>
```

Use the resulting JSON as facts for the `## Stack & Environment` section and as the initial command-evidence inventory for Taskfile applicability and generation. Do not ask LLM sub-agents to re-detect stack, build system, AMIGA status, build files, tool version pins, or parseable command evidence already present in the detection JSON.

Contracts and integrations are not deterministically detected by this script. The repository exploration sub-agent must infer them from repository-local architectural sources such as contract catalogs, build metadata, generated-code conventions, implementation modules, scripts, and documentation, following `references/architecture-doc-contract.yml`.

Tool version detection reports version-pin metadata only: file path plus declared tool/version pairs. It does not decide the tool manager, setup command, or bootstrap procedure.

Command-evidence detection reports local, parseable signals only: build files, wrappers, lockfiles, package scripts, Maven modules/plugins/capabilities, pyproject scripts/tool sections, Makefile targets, Go/Rust runnable hints, and Docker Compose files/services/classification hints. It does not decide final Taskfile commands, consult external tools, or resolve ambiguous conventions.

**Gate 2**

- [ ] Detection ran for every discovered repository.
- [ ] Each detection output was captured and passed to the matching exploration sub-agent.
- [ ] Tool version pins were treated as metadata only; no tool manager, setup command, or bootstrap procedure was decided in this step.
- [ ] Command-evidence inventory was treated as local evidence only; no final Taskfile command was decided in this step.

### 2.5. Prepare workspace artifact context

Before spawning repository exploration sub-agents, build a compact YAML `workspace_artifact_context` block for each repository.

This context is optional and must be derived only from artifact-typology context already available in the current run, repository discovery results, deterministic detection output, or explicit repository-local references. Use repository discovery only for repository names. Use detection output only for deterministic repository facts. Use repository-local references only to confirm direct relationships or contracts, not to infer artifact roles. Do not hardcode artifact types, infer artifact responsibilities from prefixes yourself, or stop the workflow when this context is unavailable.

When artifact-typology context is available, render only the current repository and directly relevant sibling repositories:

```yaml
workspace_artifact_context:
  available: true
  current_repository:
    name: <repo-name>
    artifact_role: <role from available artifact-typology context>
    mission: <mission from available artifact-typology context>
    owned_surfaces:
      - <artifact-owned surface from available context>
  relationships:
    - repository: <related-repo-name>
      relationship: <relationship from available context or explicit local reference>
```

When artifact-typology context is not available for the workspace or repository, render:

```yaml
workspace_artifact_context:
  available: false
```

The block is analysis input for the sub-agent. It may represent only the subset of repositories currently being initialized or modified, so it must not be treated as the complete product topology. It must be compact and should not include explanatory prose, skill names, absolute local paths, or broad catalogs of unrelated artifact types.

**Gate 2.5**

- [ ] Each repository exploration prompt has a `workspace_artifact_context` block.
- [ ] If artifact-typology context was unavailable, the block says `available: false`.
- [ ] If artifact-typology context was available, the block includes only the current repository and directly relevant sibling repositories.
- [ ] No artifact type, role, or relationship was invented from repository prefixes by `aidev-explore`.
- [ ] No skill name or artifact-typology source name was included in the rendered context.

### 2.6. Decide Taskfile applicability

Before spawning repository exploration sub-agents, decide whether each repository should produce repository-root Taskfile guidance.

Taskfile guidance is applicable when at least one of these is true:

- A repository-root `Taskfile.yml` or `Taskfile.yaml` already exists.
- The user explicitly requested Taskfile generation.
- Repository-local command evidence shows meaningful local workflows that are relevant to the repository mission, owned surfaces, or implementation responsibilities.

If none of the applicability conditions above is met, set `generate: false`. Do not infer applicability solely from repository name, prefix, artifact type, or product assumptions.

Render a compact YAML block for each repository:

```yaml
taskfile_applicability:
  generate: <true|false>
  reason: <one concise repository-local reason>
```

This decision controls output shape only. It must not override `ARCHITECTURE.md`, must not rewrite the artifact mission, and must not be presented as product topology.

**Gate 2.6**

- [ ] Each repository exploration prompt has a `taskfile_applicability` block.
- [ ] Existing repository-root Taskfiles were treated as applicable guidance.
- [ ] New Taskfiles were requested only when repository-local evidence or the user's explicit request made them useful.
- [ ] No Taskfile applicability decision was based solely on artifact type, repository prefix, or assumed product role.

### 3. Explore repositories

Spawn one repository exploration sub-agent per repository, all in the same turn where possible. This step is delegated even for single-repo workspaces to keep detailed repository reads out of the main context window and to preserve parallelism.

Use a general purpose or default sub-agent type for repository exploration. Do not use host runtimes' `explore` or `explorer` agent type for this step, because those lightweight exploration agents may lack MCP/tool access needed when Taskfile command-resolution rules apply.

The initial prompt for every repository exploration sub-agent is not free-form. It must be the exact prompt body from `references/explore-agent-prompt.md`, rendered only by replacing its placeholders. The main agent must copy the rendered body into the sub-agent invocation's message/prompt field with no additional text before or after it.

For each repository:

1. Read `references/explore-agent-prompt.md`.
2. Copy the prompt body between `<!-- aidev-explore:prompt-body:start -->` and `<!-- aidev-explore:prompt-body:end -->`.
3. Replace exactly these placeholders:
   - `{repo_path}` with the repository path.
   - `{repo_name}` with the repository name.
   - `{detection_json}` with the Step 2 detection JSON for that repository.
   - `{workspace_artifact_context}` with the Step 2.5 YAML context block for that repository.
   - `{taskfile_applicability}` with the Step 2.6 YAML context block for that repository.
   - `{architecture_doc_contract_path}` with the absolute path to `references/architecture-doc-contract.yml`.
   - `{taskfile_doc_contract_path}` with the absolute path to `references/taskfile-contract.yml`.
4. Spawn a general purpose or default repository exploration sub-agent with that rendered prompt body as the complete initial prompt. Do not summarize it, paraphrase it, prepend coordination text, append reminders, wrap it in another prompt, pass only the template path, or replace it with "use the aidev-explore skill".
5. If the sub-agent API has separate fields for agent type, role, model, tools, or metadata, set those separately. The message/prompt field must still be exactly the rendered prompt body.

Each rendered prompt includes:

- Repository path.
- Repository name.
- Detection JSON from Step 2.
- Workspace artifact context from Step 2.5.
- Taskfile applicability from Step 2.6.
- Absolute path to `references/architecture-doc-contract.yml`.
- Absolute path to `references/taskfile-contract.yml`.
- The required output delimiters from `references/explore-agent-prompt.md`.

Each sub-agent must read the architecture contract before writing and must read the Taskfile contract only when Taskfile guidance is applicable. It must return repository guidance in a single response, wrapped between the delimiters defined in `references/explore-agent-prompt.md`:

- The complete markdown document for `<repo>/ARCHITECTURE.md`.
- Either the complete repository-root Taskfile document headed by `version: '3'`, or the explicit Taskfile skipped delimiter when Taskfile guidance is not applicable.

The main agent owns parsing returned artifacts and writing files. If a sub-agent response is not delimited exactly as required, rerun that repository exploration with the exact rendered prompt instead of salvaging an ambiguous response.

**Gate 3**

- [ ] One general purpose or default repository exploration sub-agent ran per repository that needs generation or refresh.
- [ ] No repository exploration sub-agent used a lightweight `explore` or `explorer` agent type.
- [ ] Each sub-agent initial prompt was exactly the rendered `references/explore-agent-prompt.md` prompt body, with placeholders replaced and no added or removed prompt text.
- [ ] Each sub-agent reused Step 2 detection JSON; no LLM re-detected deterministic stack facts.
- [ ] Each sub-agent received the Step 2.5 `workspace_artifact_context` block for its repository.
- [ ] Each sub-agent received the Step 2.6 `taskfile_applicability` block for its repository.
- [ ] Each sub-agent read `references/architecture-doc-contract.yml`; Taskfile-applicable sub-agents also read `references/taskfile-contract.yml`.
- [ ] Taskfile-applicable sub-agents started from Step 2 `command_evidence` and inspected additional repository files only when required command evidence was incomplete.
- [ ] Taskfile-applicable sub-agents selected one primary toolchain profile and applied relevant capability overlays from `references/taskfile-contract.yml`.
- [ ] For Taskfile-applicable AMIGA framework repositories, each sub-agent treated AMIGA as a capability/context overlay and consulted relevant available Inditex ecosystem tools before accepting or rejecting framework-specific conventions.
- [ ] If Docker Compose files were present in Taskfile-applicable repositories, each sub-agent classified them as runtime dependency, integration-test dependency, or auxiliary compose evidence before adding dependency tasks.
- [ ] Docker Compose support tasks, when generated, were modeled as `start-deps`, `stop-deps`, `reset-deps`, or qualified variants and only wired into `start`/test variants when repository evidence supported that relationship.
- [ ] Each sub-agent returned a complete architecture document headed by `# <repo-name> Architecture`.
- [ ] Each returned architecture document presents repository facts directly and does not narrate discovery, detection, inventory, reporting, sub-agent behavior, model behavior, or output provenance. If it does, rerun or correct that repository exploration before writing the file.
- [ ] Each returned architecture document is complete, correct, and high-quality at a high architectural level: it does not leave introduced architectural aspects incomplete and does not use one concrete example as the explanation for the whole concern.
- [ ] Each Taskfile-applicable sub-agent returned a complete repository-root Taskfile with only applicable tasks backed by supported command evidence.
- [ ] Each non-Taskfile-applicable sub-agent returned the exact Taskfile skipped delimiter and no Taskfile content.
- [ ] Every returned Taskfile task declares an explicit `dir`.
- [ ] Any returned Taskfile phase variants follow the `<phase>-<qualifier>` naming rule.
- [ ] When a phase is not applicable or has no supported command evidence, the returned Taskfile omits that task instead of creating a failing placeholder.
- [ ] Every returned Taskfile artifact is parseable YAML.
- [ ] No returned artifact includes absolute local paths, user-home paths, or Markdown code fences.
- [ ] No returned artifact, raw sub-agent response, parsed Taskfile, parsed architecture markdown, note, or context snapshot was persisted as an additional file.

### 4. Write and validate ARCHITECTURE.md, then update AGENTS.md architecture context

For each repository that needs generation or refresh, write the returned architecture markdown to:

```text
<repo>/ARCHITECTURE.md
```

Then validate it:

```bash
python3 <skill_path>/scripts/validate-architecture-doc.py --repo <repo_path>
```

If validation fails, fix the markdown before proceeding. Do not silently accept invalid architecture docs.

Only after validation succeeds, update `AGENTS.md` with the architecture-context paragraph:

```bash
python3 <skill_path>/scripts/update-agents-architecture-context.py --repo <repo_path>
```

This helper is idempotent. It creates `AGENTS.md` when missing, appends to an existing `AGENTS.md` without replacing it, and skips appending when the exact paragraph already exists.

**Gate 4**

- [ ] Each discovered repository has a root `ARCHITECTURE.md` or was explicitly reported as already present and skipped.
- [ ] Every generated or refreshed document satisfies `references/architecture-doc-contract.yml`.
- [ ] Every generated or refreshed document uses repository-relative paths only.
- [ ] No generated or refreshed document includes generated bookkeeping sections.
- [ ] Every generated or refreshed repository has an `AGENTS.md` that references `ARCHITECTURE.md` as required agent context.
- [ ] No existing `AGENTS.md` content was replaced or rewritten.

### 5. Write and validate applicable repository-root Taskfiles, then update AGENTS.md Taskfile context

For each repository that needs generation or refresh and has `taskfile_applicability.generate: true`, stream the Taskfile artifact returned by the sub-agent directly into the dedicated helper. Do not write a copy of the Taskfile artifact to any other persistent file.

```bash
python3 <skill_path>/scripts/update-taskfile.py --repo <repo_path> --content-stdin
```

Pass the exact Taskfile artifact on stdin. Do not leave any Taskfile content file behind after this step.

This helper is idempotent for the repository-root Taskfile location: it writes `Taskfile.yml` when the repository has no Taskfile yet, preserves an existing `Taskfile.yaml` extension when present, and refuses ambiguous dual-file states.

If the helper rejects the Taskfile because it is not parseable YAML or does not satisfy the Taskfile contract, rerun or correct the repository exploration output before writing. Do not write malformed YAML and do not repair it by hand outside the Taskfile contract.

Then validate the resulting Taskfile:

```bash
python3 <skill_path>/scripts/validate-taskfile.py --repo <repo_path>
```

If validation fails, fix the Taskfile content before proceeding. Do not silently accept an invalid Taskfile.

Only after validation succeeds, update `AGENTS.md` with the Taskfile discovery paragraph and validate the final `AGENTS.md`:

```bash
python3 <skill_path>/scripts/update-agents-taskfile-context.py --repo <repo_path>
python3 <skill_path>/scripts/validate-agents-doc.py --repo <repo_path>
```

For each repository with `taskfile_applicability.generate: false`, do not call `update-taskfile.py` or `update-agents-taskfile-context.py`. Validate `AGENTS.md`; it must contain the architecture paragraph and must not reference a missing repository-root Taskfile.

**Gate 5**

- [ ] Every Taskfile-applicable generated or refreshed repository has exactly one repository-root Taskfile (`Taskfile.yml` or `Taskfile.yaml`).
- [ ] Every generated or refreshed repository Taskfile declares version 3 and a top-level `tasks` key.
- [ ] Every generated or refreshed repository Taskfile contains only applicable tasks backed by supported command evidence.
- [ ] Every generated or refreshed repository Taskfile phase variant follows the `<phase>-<qualifier>` naming rule.
- [ ] Every generated or refreshed repository Taskfile task declares an explicit `dir`.
- [ ] Every generated or refreshed repository Taskfile parses successfully as YAML.
- [ ] Each generated or refreshed Taskfile satisfies the evidence policy and task omission handling in `references/taskfile-contract.yml`.
- [ ] Each generated or refreshed Taskfile uses repository-relative paths only and contains no absolute local, user-home, or fenced Markdown content.
- [ ] Every Taskfile-applicable generated or refreshed repository has an `AGENTS.md` that references both `ARCHITECTURE.md` and the repository-root Taskfile.
- [ ] Every non-Taskfile-applicable generated or refreshed repository has no repository-root Taskfile created by this run and no `AGENTS.md` paragraph that references a missing Taskfile.
- [ ] No generated or refreshed repository leaves the obsolete `aidev-explore` local-dev managed block in `AGENTS.md`.
- [ ] `validate-taskfile.py` passed for every generated or refreshed Taskfile, and `validate-agents-doc.py` passed for every updated repository.
- [ ] No additional persistent file was created or modified by this step.

### 6. Final side-effect guard

Before reporting success, confirm the persistent output boundary:

- Allowed generated or refreshed files are only `<repo>/ARCHITECTURE.md`, `<repo>/AGENTS.md`, and, for Taskfile-applicable repositories, exactly one repository-root Taskfile (`Taskfile.yml` or existing `Taskfile.yaml`).
- For repositories where Taskfile guidance is not applicable, the whitelist is limited to `<repo>/ARCHITECTURE.md` and `<repo>/AGENTS.md`.
- No raw sub-agent response, parsed artifact, Taskfile copy, scratch file, context snapshot, execution note, backup file, deliverable, or any other non-whitelisted file created by this run remains anywhere.

If any non-whitelisted persistent file was created or modified by this run, delete or restore it before the final report. If that cannot be done, report the workspace as blocked and name the path. Do not report success while non-whitelisted run artifacts remain.

## Success Criteria

- Every discovered repository has a root `ARCHITECTURE.md`.
- Every generated or refreshed repository has an `AGENTS.md` paragraph that tells agents to read `ARCHITECTURE.md` as context.
- Every Taskfile-applicable generated or refreshed repository has an `AGENTS.md` paragraph that tells agents to use the repository-root Taskfile for standard local workflows.
- Every non-Taskfile-applicable generated or refreshed repository has no new Taskfile and no `AGENTS.md` paragraph that references a missing Taskfile.
- Every Taskfile-applicable generated or refreshed repository has exactly one repository-root Taskfile (`Taskfile.yml` or `Taskfile.yaml`).
- Each `ARCHITECTURE.md` contains all required sections from `references/architecture-doc-contract.yml`.
- Each generated or refreshed repository-root Taskfile satisfies `references/taskfile-contract.yml`, including the base task names `install`, `build`, `lint`, `format`, `test`, and `start`.
- `## Stack & Environment` is grounded in deterministic `detect-repo.py` output.
- Interpretive sections explain project structure, architecture patterns, integrations, runtime flows, conventions, and gotchas.
- No generated document contains absolute local paths, user-home paths, or generated bookkeeping sections.
- The skill no longer depends on persistent repository architecture artifacts outside the repository root.
- No persistent files are created or modified except the output-whitelisted repository-local files: `ARCHITECTURE.md`, `AGENTS.md`, and, when applicable, one repository-root Taskfile.

## Key Rules

- The root `ARCHITECTURE.md` is the repository-level architecture artifact.
- When present, the repository-root Taskfile is the only place where local development and execution commands live; do not duplicate them in `AGENTS.md` or `ARCHITECTURE.md`.
- `AGENTS.md` is the discovery entry point that points agents to `ARCHITECTURE.md` and, only when present, the repository-root Taskfile.
- When generated or refreshed, the repository-root Taskfile must omit tasks for phases that are not applicable or have no supported command evidence.
- When a Taskfile is generated or refreshed and multiple supported alternatives exist for a phase, name each variant with the base phase as a kebab-case prefix, such as `start-with-mocks`, `start-full`, or `test-integration`.
- Every generated or refreshed Taskfile task must declare an explicit `dir`.
- Every generated or refreshed Taskfile must parse as YAML.
- Remove the obsolete `aidev-explore` local-dev managed block from `AGENTS.md` during refresh; that block is no longer part of the valid output model.
- Do not create repository architecture artifacts outside the repository root.
- Do not create or modify any persistent file outside the output whitelist.
- Do not create persistent intermediate files, raw output files, Taskfile copies, context files, notes, execution-support files, backups, manifests, or snapshots anywhere.
- Do not generate freshness, audit, or bookkeeping sections.
- Do not include absolute local paths or user-home paths.
- Do not overwrite an existing architecture document unless the user explicitly asked to generate, update, or refresh it.
- Do not create a repository-root Taskfile unless Taskfile guidance is applicable for that repository.
- Do not overwrite an existing repository-root Taskfile unless the user explicitly asked to generate, update, or refresh it.
- Do not overwrite or rewrite an existing `AGENTS.md`; only append the required discovery paragraphs when applicable and absent.
- Command evidence and uncertainty handling for generated or refreshed repository-root Taskfiles are governed by `references/taskfile-contract.yml`; do not duplicate that policy in workflow prose.
