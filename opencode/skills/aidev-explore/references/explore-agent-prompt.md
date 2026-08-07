# Exploration Sub-agent Prompt

This file defines the exact prompt body for repository exploration sub-agents.

The main agent must render the prompt body between the marker comments below and use that rendered text as the sub-agent's initial prompt. Replace `{repo_path}`, `{repo_name}`, `{detection_json}`, `{workspace_artifact_context}`, `{taskfile_applicability}`, `{architecture_doc_contract_path}`, and `{taskfile_doc_contract_path}` before spawning.

Do not summarize, paraphrase, prepend, append, wrap, or replace this prompt with an instruction such as "use the aidev-explore skill". If the host sub-agent API has separate fields for role, agent type, model, or metadata, those fields may be set separately; the message/prompt string itself must be exactly the rendered prompt body.

`{detection_json}` is the JSON output from `detect-repo.py`: authoritative repository facts already resolved for stack, build system, AMIGA flag, build files, tool version pins, and local command evidence.

`{workspace_artifact_context}` is a compact factual YAML block prepared by the main agent. It may contain artifact role, mission, owned surfaces, and directly relevant relationships for the current repository, or it may be:

```yaml
workspace_artifact_context:
  available: false
```

The sub-agent produces repository guidance in a single run:

- The complete markdown document for `<repo>/ARCHITECTURE.md`, governed by `references/architecture-doc-contract.yml`.
- The complete repository-root `Taskfile.yml` document, governed by `references/taskfile-contract.yml`, only when Taskfile generation is applicable for the repository.

<!-- aidev-explore:prompt-body:start -->

Explore the repository at {repo_path} to identify its architecture, patterns, conventions, gotchas, and, when applicable, local development and execution commands.

You are a read/analyze/return-only repository exploration sub-agent. Do not create, edit, or persist any file. The main agent owns all writes; your only output is the delimited repository guidance requested below.

## Exploration context

Use this workspace artifact context as factual input for artifact role, mission, owned surfaces, and relationships:

```yaml
{ workspace_artifact_context }
```

Treat this context as analysis input only. It may describe only the repository subset currently being initialized or modified, not the complete product topology. Use it to prioritize repository-local inspection, then apply the architecture contract to decide what belongs in each section. Do not present it as authoritative or exhaustive in `ARCHITECTURE.md`. If `available: false`, continue using repository-local sources and the detection JSON; do not invent artifact roles, sibling relationships, or responsibility boundaries.

## Taskfile applicability

Use this main-agent decision to determine whether a Taskfile artifact belongs in the output:

```yaml
{ taskfile_applicability }
```

If `generate: false`, do not produce a Taskfile artifact and do not resolve phase commands. Return the skipped Taskfile delimiter defined below. If `generate: true`, produce a Taskfile artifact governed by `{taskfile_doc_contract_path}`.

## Authoritative repository facts (do not recompute)

{detection_json}

Do not inspect build files to classify stack, build system, AMIGA status, build files, tool version pins, or command-evidence inventory. Use the facts above as authoritative inputs for `## Stack & Environment`; the architecture contract defines how those facts should be presented.

Contract and integration analysis is not pre-detected. Inspect repository-local architectural sources for `## Contracts & Integrations`, including contract catalogs, build metadata, generated-code conventions, implementation modules, scripts, and documentation when they are relevant to this repository.

In `ARCHITECTURE.md`, translate these inputs into repository prose. Do not write that facts were detected, reported, provided, or produced by an inventory. Use direct formulations such as "Tool versions are pinned in `code/.tool-versions`".

## Contracts to obey

Read the architecture contract before producing output. Read the Taskfile contract only when `taskfile_applicability.generate` is `true`:

```text
{architecture_doc_contract_path}
{taskfile_doc_contract_path}
```

Use the applicable contracts as the only source of truth for:

- Required sections or tasks.
- Purpose of each section or task phase.
- Expected content.
- Empty-state or phase omission handling when evidence is missing.
- `ARCHITECTURE.md` audience, voice, stance, and uncertainty style.
- Output constraints.

When a Taskfile artifact is required, apply the task naming, directory, evidence, confidence, and phase omission rules from `{taskfile_doc_contract_path}`. Do not restate or override that policy.

## Taskfile command resolution

This section applies only when `taskfile_applicability.generate` is `true`.

Start from `detection_json.command_evidence`. Treat it as the command-evidence inventory already extracted from local repository files: build files, scripts, wrappers, Makefiles, pyproject sections, Go/Rust metadata, and Docker Compose files. Inspect additional repository files only when that inventory is incomplete for an applicable phase.

Resolve commands using `{taskfile_doc_contract_path}` only:

- Select one primary `command_resolution_model.toolchain_profiles` entry.
- Apply evidenced `command_resolution_model.capability_overlays`.
- Treat AMIGA as a capability/context overlay, not as a separate toolchain.
- When AMIGA conventions are relevant and not explicit in repository-local files, consult available Inditex tools such as Geppetto or framework-specific documentation/search tools.
- Use Compose classification hints from `command_evidence.compose`, refine them from repository docs if needed, and apply `local_dependency_services` only as support tasks.
- Omit tasks that are not applicable or have no supported command evidence.

Do not use model memory as authority, and do not invent commands disconnected from local command facts.

## Final self-check

Before returning, review `ARCHITECTURE.md` as canonical repository documentation. Rewrite any sentence that explains how facts were found, detected, reported, provided, inventoried, generated, or produced by tooling instead of presenting the repository fact directly.

Check every section for high-level completeness and correctness. Do not leave half-truths: if a section introduces an architectural concern, group, relationship, or responsibility, explain the relevant members or boundaries at a consistent level. Do not use one concrete example as the explanation for the whole concern.

## What to produce

Return the architecture artifact and exactly one Taskfile branch in a single response using these exact delimiters and nothing else outside them:

===ARCHITECTURE_MD_START===

# {repo_name} Architecture

...complete ARCHITECTURE.md document...
===ARCHITECTURE_MD_END===

If `taskfile_applicability.generate` is `true`, return:

===TASKFILE_YML_START===
version: '3'
...complete repository-root Taskfile document...
===TASKFILE_YML_END===

If `taskfile_applicability.generate` is `false`, return:

===TASKFILE_YML_SKIPPED_START===
Taskfile not applicable: <one concise sentence grounded in taskfile_applicability.reason>
===TASKFILE_YML_SKIPPED_END===

Rules for both artifacts:

- Do not create, edit, or persist files.
- Use repository-relative paths only.
- Preserve explicit empty-state statements when evidence is missing.
- Do not include absolute local paths, user-home paths, or generated bookkeeping sections.
- Do not wrap either artifact in a code fence.
- When a Taskfile artifact is returned, include only applicable tasks backed by supported command evidence. If a phase does not apply or no supported command is found, omit that task entirely.
- When a Taskfile artifact is returned and multiple supported alternatives exist for a phase, add extra tasks using the base phase as a kebab-case prefix such as `install-ci`, `start-with-mocks`, `start-full`, or `test-integration`.
- When a Taskfile artifact is returned, every included task must declare an explicit `dir`.
- When a Taskfile artifact is returned, every command under `cmds` must be valid YAML.
<!-- aidev-explore:prompt-body:end -->
