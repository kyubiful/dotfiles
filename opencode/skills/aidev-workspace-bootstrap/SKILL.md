---
name: aidev-workspace-bootstrap
description: Bootstrap a local workspace application from Taskfile.yml or Taskfile.yaml files located at the root of repositories under the current workspace's repos/ directory. Use when an assistant needs to infer from the user's prompt which connected runtime repositories are involved in running the requested local app, satisfy repository tooling prerequisites declared in .tool-versions using ASDF, start that whole runtime graph plus required Taskfile dependencies, and use Taskfile tasks whose names follow the start* startup pattern, without leaving the opened workspace root or modifying workspace files.
---

# aidev-workspace-bootstrap

Use the assistant's current working directory as the workspace root. Do not inspect, search, or start repositories outside that root.

Repositories live only under `<workspace_root>/repos/`.

For each repository, consider only `Taskfile.yml` or `Taskfile.yaml` located directly at that repository root. Ignore Taskfiles in nested folders or any other location.

Startup commands are Taskfile tasks whose names follow the `start*` pattern. Do not assume that `start` is the only startup task.

First triage the user's prompt. Determine which app, surface, service, or runtime flow the user wants to start, then select the connected runtime graph required to run that target.

When the user specifies one or more repositories, operate on those repositories and the runtime repositories or startup dependencies that are required for them to run connected to the local workspace.

When the user does not specify repositories, treat the request as intent to start the whole connected runtime for the requested app. Do not stop after starting one repository successfully if other runtime repositories are connected to it. Do not ask whether to start connected runtime neighbors; include them unless the user asks for mocks, standalone mode, or a deliberately partial startup.

Do not start every repository with a Taskfile. Select the connected runtime graph using evidence inside `<workspace_root>/repos/`:

- repository names and obvious runtime roles,
- root Taskfile `start*` tasks and their dependencies,
- `AGENTS.md`, `ARCHITECTURE.md`, README files, or local configuration when present,
- ports, service wiring, contracts, compose files, or dependency references that connect repositories to the requested app.

Exclude repositories that are not needed to run the requested target, even if they have a Taskfile.

Do not start a repository as a top-level runtime just because it provides infrastructure, documentation, generation, or support workflows. Include it only when the prompt or workspace evidence shows that it must run as part of the requested app.

Ask the user only before starting when the prompt could reasonably refer to multiple different disconnected runtime graphs or when runtime relevance cannot be determined from the workspace evidence. Do not ask after a partial startup whether the user wants the remaining connected runtime repositories; starting them is part of the contract unless the user asked for a partial mode.

Select the startup task for each repository with this order:

1. If the user named a concrete startup task, use it.
2. Ignore support-only startup tasks as top-level candidates when they are dependencies of another startup task.
3. Prefer the startup task that is most self-contained for local application bootstrap, according to the Taskfile itself. A task that wires required startup dependencies is a better default than a narrower runtime-only variant.
4. If no self-contained variant is evidenced and `start` exists, use `start` as the conventional default for that repository.
5. Otherwise, if exactly one runnable `start*` task remains, use it.
6. Ask the user only when more than one runnable startup candidate remains after these rules.

Before starting any selected repository, satisfy its declared tooling prerequisites. Look for `.tool-versions` files inside that repository, especially at the repository root and in the selected Taskfile task `dir`. Do not search outside the repository.

For every relevant `.tool-versions` file, run ASDF from the directory that owns that file:

1. Verify `asdf` is available.
2. Install missing declared tool versions with `asdf install`.
3. If ASDF reports a missing plugin, install that plugin with `asdf plugin add <tool>` when ASDF can resolve it, then run `asdf install` again.
4. If ASDF or a required plugin/tool version cannot be installed, block startup for that repository and report the tooling prerequisite failure.

Do not run a repository startup task until its `.tool-versions` prerequisites are satisfied.

Respect Taskfile dependencies and startup ordering. If one selected startup task depends on another startup task, run the dependency first. When running a repository startup task, invoke it from the repository root as `task <startup-task>` and let Taskfile execute its local dependencies.

Report success only when every repository in the selected connected runtime graph has either been started or explicitly blocked. Starting a single repository successfully is not success for a vague app-start request when connected runtime repositories remain unstarted.

Do not create, modify, delete, or persist workspace files. ASDF tool installation outside the workspace is allowed only to satisfy `.tool-versions` prerequisites for repositories selected by this run.
